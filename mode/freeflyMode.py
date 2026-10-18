from typing import ClassVar
from mode.workMode import workMode
from prompt.aseembler import build_static_system_prompt
from prompt.dynamicPrompt.modelPrompt.freeFly import FreeFly_pro


class freeflyMode(workMode):
        mode:ClassVar[str] = "free_fly"

        @staticmethod
        def get_tools():
                return workMode.get_tools()

        @staticmethod
        def get_prompt_template() -> str:
            return freeflyMode._build_static_free_fly_system_prompt()




        @staticmethod
        def _build_static_free_fly_system_prompt() -> str:
            static_prompt = build_static_system_prompt()
            return f"{static_prompt}\n\n{FreeFly_pro}"