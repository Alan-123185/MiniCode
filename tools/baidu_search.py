import requests
import json

from langchain_core.tools import tool
from config.data import settings
from core.toolResult import toolResult


@tool
def baidu_search(question : str) -> toolResult:
    """
    这个工具可以返回实时联网搜索结果，当涉及时效性问题或者自己无法确定的结论时务必调用获取最新信息

    :param question: 要搜索的关键词或者问题描述，字符串类型
    :return:  返回一个工具调用结果类
    """

    url=settings.baidu_search_url
    #json请求体
    payload = json.dumps(
{
    "messages": [
            {
                "role": "user",
                "content": question
            }
                ],    #消息是字典列表
    "edition": "standard",   #普通搜索模式
    "search_source": "baidu_search_v2",   #模型版本
    "search_recency_filter": "week",  #时间过滤
    "resource_type_filter":[
        {
            "type":"web",
            "top_k": settings.baidu_search_default_return_number
        }
    ]
    },
    ensure_ascii=False  #编码方式
    )
    #请求头
    headers = {
        'Content-Type': 'application/json',   #内容类型
        'Authorization': 'Bearer '+settings.baidu_search_api_key   #身份认证
    }
    try:
        response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))
    except Exception as e:
        return toolResult(
            success=False,
            content=f"请求失败: {str(e)}",
            tool_name="baidu_search"
        )

    response.encoding = "utf-8"

    references = json.loads(response.text)["references"]

    result=[]

    for reference in references:
        ref={}
        ref["url"]=reference["url"]
        ref["title"]=reference["title"]
        ref["date"]=reference["date"]
        ref["content"]=reference["snippet"]
        if ref["content"] not in result:
            result.append(ref)
    return toolResult(
        success=True,
        message=f"{question}的搜索结果",
        content=str(result),
        tool_name="baidu_search"
    )


if __name__ == '__main__':
    res = baidu_search.invoke({"question":"长沙今天天气如何"})
    for i in res.content:
       print(i.content)

