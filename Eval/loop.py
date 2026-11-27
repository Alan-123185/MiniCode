"""
这个函数用来作为Eval调用agent的入口
传入路径，agent临时设置为默认用自由飞行模式
"""
import json
import os
import asyncio
import httpx
from datasets import load_dataset
from loguru import logger

from Eval.Prompt import PROMPT
from Eval.callRequest import CallRequest, problemInfo, resultInfo
from requestcommon.chatRequest import ChatRequest
from requestcommon.workplaceRequest import WorksplaceRequest


USER_ID:str = "user_local"
MODEL_NAME:str = "MiniCode"


def repo_path(instance_id: str) -> str:
    """每个 instance 一个固定目录（不用时间戳），保证 ready_repo 与 main 拿到同一个路径"""
    return f"D:/testMiniCode/{instance_id}"

async def call_agent(payload:CallRequest):
    base_url="http://127.0.0.1:8000/MiniCode/chat"
    #调用这个接口实现给agent发配任务
    base_prompt=PROMPT
    try:
        async with httpx.AsyncClient(
                base_url=base_url, timeout=httpx.Timeout(120, connect=5), trust_env=False
        ) as client:
            await client.post("http://127.0.0.1:8000/MiniCode/workplace", json=WorksplaceRequest(workplace=payload.path,user_id=USER_ID,session_id=payload.session_id).model_dump())
            await client.post(f"http://127.0.0.1:8000/MiniCode/chat", json=ChatRequest(message=base_prompt+payload.message,user_id=USER_ID,session_id=payload.session_id).model_dump())
    except Exception as e:
        logger.error(f"产生错误{e}")
        raise

"""
拿到题集
"""
async def get_problem_list() -> list[problemInfo]:
    dataset = load_dataset(
        "SWE-bench/SWE-bench_Verified",
        split="test"
    )
    tasks = dataset.select(range(10))   # 这里为了测试方便，只取前10个任务，后续可以改成全部
    ret:list[problemInfo] = []
    for data in tasks:
        ret.append(problemInfo(instance_id=data["instance_id"],
                               repo=data["repo"],
                               base_commit=data["base_commit"],
                               problem_statement=data["problem_statement"]
                               ))
    return ret


"""
把工作区恢复到 base_commit：丢弃 agent 改过的文件，并删掉 agent 新增的未跟踪文件/目录
"""
async def reset_repo(repo_path: str, commit: str) -> None:
    for args in (("reset", "--hard", commit), ("clean", "-fd")):
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="replace"))


"""
这个函数用来整理agent的最终结果，主要是得到git diff
"""
async def manage_output(repo_path: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git",
        "add",
        "-N",
        "--",
        ".",
        ":(exclude).MiniCode",
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode("utf-8", errors="replace"))

    proc = await asyncio.create_subprocess_exec(
        "git",
        "diff",
        "HEAD",
        "--no-color",
        "--",
        ".",
        ":(exclude).MiniCode",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=repo_path,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode("utf-8", errors="replace"))

    return stdout.decode("utf-8")


async def main() -> list[resultInfo]:
    pro_list=await get_problem_list()
    ret_list:list[resultInfo] = []
    for pro in pro_list:
        path=repo_path(pro.instance_id)
        try:
            # 每轮开始前先复位，防止上一题的改动残留在工作区
            await reset_repo(repo_path=path, commit=pro.base_commit)
            await call_agent(payload=CallRequest(session_id=pro.instance_id,message=pro.problem_statement,path=path))
            diff_text=await manage_output(repo_path=path)
            ret_list.append(resultInfo(instance_id=pro.instance_id,model_patch=diff_text,model_name_or_path=MODEL_NAME))
        except Exception as e:
            logger.error(f"{pro.instance_id} 处理失败: {e}")
            diff_text = await manage_output(repo_path=path)
            ret_list.append(resultInfo(instance_id=pro.instance_id,model_patch=diff_text,model_name_or_path=MODEL_NAME))
    return ret_list


async def ready_repo(pro_list:list[problemInfo]):
    async def _add_repo(instance_id: str, repo: str, commit: str):
        path = repo_path(instance_id)

        # 如果还没有 Git 仓库，就执行克隆
        if not os.path.exists(os.path.join(path, ".git")):
            os.makedirs(os.path.dirname(path), exist_ok=True)

            proc = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                f"https://github.com/{repo}.git",
                path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(stderr.decode("utf-8", errors="replace"))

        # 克隆完成，或者仓库原本就存在，现在切换 commit
        proc = await asyncio.create_subprocess_exec(
            "git",
            "checkout",
            commit,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="replace"))


    #按照instance_id顺序依次clone repo并checkout到指定commit，保证ready_repo与main拿到同一个路径
    for pro in pro_list:
        await _add_repo(pro.instance_id, pro.repo, pro.base_commit)


# #先利用ready_repo函数把所有的repo都clone下来并checkout到指定commit
pro_list=asyncio.run(get_problem_list())
asyncio.run(ready_repo(pro_list))


json_list=asyncio.run(main())
output_path = os.path.join(
    os.path.dirname(__file__),
    "predictions.jsonl"
)
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    for result in json_list:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

