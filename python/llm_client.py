from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from config import settings

def create_llm() -> ChatOpenAI:
    """创建并返回一个ChatOpenAI实例"""
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
        max_tokens=4096
    )

if __name__ == "__main__":
    llm = create_llm()
    chat_messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="What is the capital of France?"),
        ]
    response = llm.invoke(chat_messages)
    print(response.content)
