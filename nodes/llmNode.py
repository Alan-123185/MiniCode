import uuid
from langchain_core.runnables import RunnableConfig
from loguru import logger
from config.modelConfig import model_config
from context.pipline import pre_call_func
from exceptions import BizException
from states.OverallState import OverAllState
from tools.toolManage import tools


async def llm_node(state: OverAllState,config:RunnableConfig) -> OverAllState:
    input_message = pre_call_func(state,config)
    logger.info(input_message)
    # 型是运行时选择的,必须调用时取最新,不能在模块级绑定
    model = model_config["value"]
    if model is None:
        raise BizException(message="ERROR 请先选择模型")
    #提示词得改一下
    response = None
    try:
        async for chunk in model.bind_tools(tools).astream(input_message):
            response = chunk if response is None else response + chunk
    except Exception as e:
        raise BizException(message=f"ERROR 生成失败")
    # 1. 生成 message_id
    message_id =str(uuid.uuid4()).replace("-", "")
    # 2. 把 message_id 塞进 additional_kwargs
    # if response.additional_kwargs is None:
    #     response.additional_kwargs = {}
    response.additional_kwargs["memory_id"] = message_id
    usage = response.usage_metadata
    logger.info("respnse:"+str(response))
    return {
        "output": response.content,
        "messages": [response],
        "total_tokens": usage["total_tokens"] if usage else 0,
        "steps": ["thinking......"]
    }



