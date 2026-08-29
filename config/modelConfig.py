
#阿里云百炼模型
# default_model=ChatTongyi(
#     model=settings.model_name,
#     streaming=settings.DEFAULT_STREAMING,
#     model_kwargs={
#         "enable_thinking": settings.default_think_model # 关闭思考模式
#     }
# )

#OpenAi兼容模式   2026.8.15 use OpenAi api to void bug ,the user can choose the model

model_config = {"value": None}   # 运行时由用户更新
# model_config["value"] is the true model



