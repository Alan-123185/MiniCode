import json
import re
from pathlib import Path

from tree_sitter_analyzer.core._analysis_engine_errors import UnsupportedLanguageError
from tree_sitter_analyzer.core.analysis_engine import UnifiedAnalysisEngine
from tree_sitter_analyzer.core.request import AnalysisRequest
from config.sessionManager import sessionmanager
from core.toolResult import toolResult
from service.summaryService import summaryService
from utils.commandSafe import truncate_output

"""
使用AST结构化文件读取结果，方便降级工具调用结果（仅针对于全文读取）
"""


summary_service=summaryService()
async def _compress_read_result(tool_result:toolResult,tool_call_id: str) -> str :
    config=tool_result.data.get("config")
    file_path = tool_result.data.get("file_path")
    if tool_result.success:
        #当返回了完整代码时，尝试使用AST解析器提取函数、类、常量等骨架信息
        if not tool_result.data.get("start_line") and not tool_result.data.get("end_line") and not "仅返回折叠后的源码骨架" in tool_result.message:
            try:
                abs_path = sessionmanager.get_session(config.get("configurable", {}).get("thread_id")).workplace  # 确保在工作区根目录下运行
                engine = UnifiedAnalysisEngine(project_root=abs_path)
                abs_file_path = str(Path(abs_path) / file_path)
                request = AnalysisRequest(
                    file_path=abs_file_path,
                    include_details=False,  # 摘要不需要详细属性
                    include_complexity=False,
                )
                result = await engine.analyze(request)
            except UnsupportedLanguageError as e:
                return tool_result.content
            except Exception as e:
                return tool_result.content
            if not tool_result.success:
                return tool_result.content

            lines = [f"[{file_path} 共 {result.line_count} 行]"]
            elements = sorted(result.elements, key=lambda e: (e.start_line, e.end_line))
            for elem in elements:
                lines.append(f"signature: {elem.raw_text.split('\n')[0]}")
                if elem.element_type == "function":
                    # 提取函数名、行号范围，可进一步从 raw_text 提取签名
                    lines.append(f"  def {elem.name} L{elem.start_line}-L{elem.end_line}")
                elif elem.element_type == "class":
                    lines.append(f"class {elem.name} L{elem.start_line}-L{elem.end_line}")
                elif elem.element_type == "variable" and elem.is_constant:
                    lines.append(f"  const {elem.name} L{elem.start_line}-L{elem.end_line}")
                elif elem.element_type == "import":
                    lines.append(f"  import {elem.name} L{elem.start_line}-L{elem.end_line}")
            return "\n".join(lines)+f"\n[system Info]文件读取结果已降级为骨架，如需查看完整结果，请调用get_original_content_by_tool_call_id"
        else:
            return tool_result.content
    else:
        return (tool_result.error if tool_result.error else "")



"""
降级代码搜索结果，保留文件路径和行号
"""
def _compress_search_code_result(tool_result:toolResult,tool_call_id:str) -> str:
    if tool_result.success:
        result=tool_result.content
        PATTERN = re.compile(r'^(?P<file_path>.+?):\s+.+\(in (?P<line>\d+)\)$')

        def extract(s: str) -> tuple[str, int] | None:
            m = PATTERN.match(s)
            if not m:
                return None
            return m.group("file_path"), int(m.group("line"))

        first_info = "\n[system Info]代码搜索结果已进行压缩处理，如需查看完整结果，请调用get_original_content_by_tool_call_id"
        lines = result.split("\n")

        extracted = []
        for line in lines:
            info = extract(line)
            if info is not None:
                file_path, line_num = info
                extracted.append(f"{file_path}:{line_num}")

        return "\n".join(extracted) + first_info

    else:
        return (tool_result.error if tool_result.error else "")+f"\n[system Info]代码搜索失败，tool_call_id:{tool_call_id}，"



def _compress_run_bash_result(tool_result:toolResult,tool_call_id:str) -> str:
    if tool_result.success:
        content=json.loads(tool_result.content)
        stdout=content["stdout"]
        stderr=content["stderr"]
        out=truncate_output(stdout)
        err=truncate_output(stderr)
        final_content = ""
        if stdout:
            final_content += f"--- 标准输出 (STDOUT) ---\n{out}\n"
        if stderr:
            final_content += f"--- 错误输出 (STDERR) ---\n{err}\n"
        if not final_content:
            final_content = "命令执行完毕，无标准输出和错误输出。"
        return f"exit code:{int(tool_result.message.split(":")[-1].strip())}\n{final_content.strip()}"
    else:
            #如果失败了就不压缩，直接返回原始内容
            return tool_result.content





def forced_compress_tool_result(tool_call_id:str) -> str|None:
    """
    二次强制压缩工具结果，适用于工具返回内容过长的情况
    """
    if summary_service.get_content_by_tool_call_id(tool_call_id):
        return f"[system Info]工具调用成功，结果已被强制压缩，调用get_original_content_by_tool_call_id可查看"
    else:
        return None
