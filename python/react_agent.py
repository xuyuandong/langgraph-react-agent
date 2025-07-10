# 导入必要的模块
from enum import Enum
from typing import Dict, Any, Union, Optional, Tuple

# LangGraph 相关导入
from langgraph.prebuilt import create_react_agent  # 预构建的React Agent
from langgraph.checkpoint.memory import MemorySaver  # 内存保存器，用于状态持久化
from langchain_core.runnables import RunnableConfig  # 运行时配置
from langchain_core.messages import ToolMessage, HumanMessage  # 消息类型
from langgraph.types import Command  # 控制命令

# 本地模块导入
from llm_client import create_llm  # LLM客户端创建函数
from internal_tools import TOOLS_LIST, AUTO_APPROVE_TOOLS  # 工具列表和自动批准工具


class State(Enum):
    """
    定义Agent的状态枚举
    这些状态用于控制Agent的行为流程
    """
    INVALID_CONFIRMATION = "INVALID_CONFIRMATION"  # 无效确认状态
    RESUME = "RESUME"  # 恢复执行状态
    NORMAL = "NORMAL"  # 正常处理状态
    REJECT = "REJECT"  # 拒绝执行状态


class ReactAgent:
    """
    React Agent 包装类
    
    这个类封装了LangGraph的预构建React Agent，提供了：
    1. 工具调用的用户确认机制
    2. 自动批准某些工具的功能
    3. 状态管理和持久化
    4. 灵活的配置选项
    """
    
    def __init__(self, name: str, llm=None, prompt=None):
        """
        初始化React Agent
        
        Args:
            name: Agent的名称
            llm: 语言模型实例
            prompt: 提示模板
        """
        self.name = name
        self.llm = llm
        self.tools = TOOLS_LIST  # 获取工具列表
        
        # 创建LangGraph React Agent
        # interrupt_before=['tools'] 表示在工具调用前暂停，等待确认
        self.agent_executor = create_react_agent(
            model=self.llm,                    # 语言模型
            tools=self.tools,                  # 工具列表
            checkpointer=MemorySaver(),        # 内存检查点，用于状态持久化
            prompt=prompt,                     # 提示模板
            interrupt_before=['tools']         # 在工具调用前暂停
        )
        
        # 设置自动批准的工具列表
        self.auto_approve_tools = [tool.name for tool in AUTO_APPROVE_TOOLS]


    async def invoke(self, input: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Union[str, Dict[str, Any]]:
        """
        调用Agent执行任务
        
        这是Agent的主要入口点，负责：
        1. 初始化检查和配置设置
        2. 预处理输入，确定当前状态
        3. 根据状态选择不同的处理流程
        4. 后处理响应
        
        Args:
            input: 输入数据，通常包含用户消息
            config: 运行时配置，包含线程ID等
            
        Returns:
            处理后的响应或包含响应和日志的字典
        """
        # 检查Agent是否已正确初始化
        if not self.agent_executor:
            raise RuntimeError("Agent not initialized. Make sure to use 'await LLMAgent.create()' to create the agent.")

        # 确保配置对象存在，用于状态管理
        if config is None:
            config = RunnableConfig(configurable={"thread_id": "default"})

        # 保存当前的线程/请求标识符，用于日志消息推送
        if config and "configurable" in config and "thread_id" in config["configurable"]:
            self.current_thread_id = config["configurable"]["thread_id"]

        # 清除之前的日志消息
        if hasattr(self, "log_messages"):
            self.log_messages = []

        # 预处理：分析当前状态，确定处理流程
        previous_state = self._pre_process(input, config)

        response = None
        # 根据不同状态执行不同的处理逻辑
        if (previous_state == State.INVALID_CONFIRMATION):
            # 用户确认无效，返回提示信息
            return "Not a valid confirmation. Please reply would you like to proceed(yes/no or accept/reject)?"
        elif (previous_state == State.RESUME):
            # 用户确认继续，恢复Agent执行
            response = await self._handle_message(Command(resume=True), config)
        elif (previous_state == State.REJECT):
            # 用户拒绝工具调用，添加拒绝消息并重新开始
            state = self.agent_executor.get_state(config=config)
            messages = state.values["messages"]
            tool_call = messages[-1].tool_calls[0]
            # 添加工具拒绝消息
            messages.append(
                ToolMessage(
                    content="Tool call rejected",
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                ))
            # 添加新的用户消息
            messages.append(HumanMessage(content=input["messages"]))
            # 更新状态(新加了用户拒绝的消息，和用户可能新输入的消息)
            self.agent_executor.update_state(config, {"messages": messages})
            # goto="agent"：跳转到 Agent 节点重新开始推理, 不是 resume：这不是恢复之前的工具调用，而是从头开始新的推理循环
            response = await self._handle_message(Command(goto="agent"), config=config)
        elif previous_state == State.NORMAL:
            # 正常处理流程
            response = await self._handle_message(input, config)

        # 后处理响应
        processed_response = self._post_process(response, config)

        # 如果有日志消息，返回包含响应和日志的字典
        if hasattr(self, "log_messages") and self.log_messages:
            return {
                "response": processed_response,
                "logs": self.log_messages
            }
        else:
            return processed_response

    def _pre_process(self, input: Dict[str, Any], config: Optional[RunnableConfig] = None) -> State:
        """
        预处理：分析当前状态，确定下一步处理流程
        
        这个方法检查Agent的当前状态，特别是是否正在等待工具调用确认，
        并根据用户输入决定应该执行什么操作。
        
        Args:
            input: 用户输入
            config: 运行时配置
            
        Returns:
            State: 当前状态枚举值
        """
        if config is None:
            config = {"configurable": {"thread_id": "default"}}
        
        # 获取当前Agent状态
        state = self.agent_executor.get_state(config=config)
        
        # 检查是否正在等待工具调用确认
        if (len(state.next) > 0 and state.next[0] == "tools"):
            # 处理用户确认
            is_confirmed = self._handle_confirm(input["messages"])
            if is_confirmed == True:
                return State.RESUME  # 用户确认，继续执行
            elif is_confirmed == False:
                return State.REJECT  # 用户拒绝，拒绝执行
            else:
                return State.INVALID_CONFIRMATION  # 无效确认
        
        return State.NORMAL  # 正常状态

    def _post_process(self, response: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """
        后处理：处理Agent响应，检查是否需要用户确认
        
        这个方法检查Agent是否准备调用工具，如果是，则格式化确认消息；
        否则直接返回响应。
        
        Args:
            response: Agent的原始响应
            config: 运行时配置
            
        Returns:
            处理后的响应
        """
        if config is None:
            config = RunnableConfig(configurable={"thread_id": "default"})
        
        # 获取当前状态
        state = self.agent_executor.get_state(config=config)
        
        # 检查是否正在等待工具调用确认
        if (len(state.next) > 0 and state.next[0] == "tools"):
            # 格式化工具调用确认消息
            last_message = state.values["messages"][-1]
            tool_call = last_message.tool_calls[0]
            return f"{last_message.content}\n\n" \
                "The Agent wants to make a tool call with the parameter:\n" \
                "{\n" \
                f"\t\"name\": \"{tool_call['name']}\"\n" \
                f"\t\"args\": \"{tool_call['args']}\"\n" \
                "}\n" \
                "Would you like to proceed?"
        else:
            return response

    def _handle_confirm(self, input: str) -> bool:
        """
        处理用户确认输入
        
        Args:
            input: 用户输入字符串
            
        Returns:
            bool: True表示确认，False表示拒绝，None表示无效输入
        """
        if input is not None:
            lower_input = input.lower()
            if lower_input.startswith('accept') or lower_input.startswith('yes'):
                return True
            elif lower_input.startswith('reject') or lower_input.startswith('no'):
                return False
        return None

    async def _handle_message(self, message: Union[dict[str, Any], Any], config: Optional[RunnableConfig] = None) -> str:
        """
        处理消息并调用Agent执行器
        
        这个方法负责实际调用LangGraph Agent执行器，并处理自动批准逻辑。
        
        Args:
            message: 要处理的消息或命令
            config: 运行时配置
            
        Returns:
            Agent的响应
        """
        if config is None:
            config = RunnableConfig(configurable={"thread_id": "default"})
        
        # 调用Agent执行器
        response = await self.agent_executor.ainvoke(message, config)
        
        # 打印所有消息（用于调试）
        for message in response["messages"]:
            message.pretty_print()
        
        # 检查是否需要自动批准工具调用
        state = self.agent_executor.get_state(config=config)
        if (len(state.next) > 0 and state.next[0] == "tools"):
            tool_call = state.values["messages"][-1].tool_calls[0]
            # 如果工具在自动批准列表中，自动继续执行
            if tool_call["name"] in self.auto_approve_tools:
                response = await self._handle_message(Command(resume=True), config)

        return response

# 使用示例
if __name__ == "__main__":
    import asyncio
    
    async def main():
        """
        使用示例：展示如何创建和使用ReactAgent
        """
        llm = create_llm()
        from prompt import REACT_AGENT_PROMPT
        agent = ReactAgent("chatbot", llm=llm, prompt=REACT_AGENT_PROMPT)
        #response = await agent.invoke({"messages": "北京的天气怎么样？"})
        response = await agent.invoke({"messages": "我妈妈叫什么名字？"})
        print(response)
    
    # 运行异步函数
    asyncio.run(main())