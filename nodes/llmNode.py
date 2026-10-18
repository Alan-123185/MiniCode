import uuid
from loguru import logger
from config.modelConfig import model_config
from exceptions import BizException
from mode.modeRegistry import get_mode
from states.degradeState import degradeState


async def llm_node(degrade_state: degradeState) -> dict:
    input_message = degrade_state.degraded_messages
    # 型是运行时选择的,必须调用时取最新,不能在模块级绑定
    model = model_config["value"]
    if model is None:
        raise BizException(message="ERROR 请先选择模型")
    # 提示词得改一下
    response = None
    mode=get_mode(degrade_state.mode)
    tools=mode.get_tools()
    try:
        async for chunk in model.bind_tools(tools).astream(input_message):
            response = chunk if response is None else response + chunk
    except Exception as e:
        logger.exception(f"ERROR 生成失败: {e}")
        raise BizException(message=f"ERROR 生成失败")

    # 1. 生成 message_id
    message_id = str(uuid.uuid4()).replace("-", "")
    # 2. 把 message_id 塞进 additional_kwargs
    # if response.additional_kwargs is None:
    #     response.additional_kwargs = {}
    response.additional_kwargs["memory_id"] = message_id
    usage = response.usage_metadata
    logger.info("respnse:" + str(response))
    return {
        "output": response.content,
        "messages": [response],
        "total_tokens": usage["total_tokens"] if usage else 0,
        "steps": ["thinking......"],
    }
