from mode.freeflyMode import freeflyMode
from mode.planMode import planMode
from mode.workMode import workMode

_MODE_REGISTRY :dict[str, type]={
    "work": workMode,
    "plan": planMode,
    "free_fly": freeflyMode
}

def get_mode(mode_name: str) -> type:
    """
    根据模式名称获取对应的模式类。
    """
    if mode_name in _MODE_REGISTRY:
        return _MODE_REGISTRY[mode_name]
    else:
        raise ValueError(f"未找到模式: {mode_name}")