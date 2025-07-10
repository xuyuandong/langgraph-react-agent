import random
from typing import Dict, Any, List
from langchain.tools import tool

# 原始函数定义（不带装饰器）
def _get_weather(location: str) -> Dict[str, Any]:
    """
    查询指定地点的天气信息 (Mock)
    
    Args:
        location: 地点名称
        
    Returns:
        包含天气信息的字典
    """
    # Mock天气数据
    weather_conditions = ["晴天", "多云", "阴天", "小雨", "中雨", "大雨", "雪天"]
    temperatures = list(range(-10, 40))  # 温度范围 -10°C 到 40°C
    humidity = list(range(30, 100))      # 湿度范围 30% 到 100%
    wind_speed = list(range(0, 20))      # 风速范围 0 到 20 km/h
    
    return {
        "location": location,
        "weather": random.choice(weather_conditions),
        "temperature": random.choice(temperatures),
        "humidity": random.choice(humidity),
        "wind_speed": random.choice(wind_speed),
        "unit": "°C",
        "humidity_unit": "%",
        "wind_unit": "km/h"
    }

def _get_family_names() -> List[Dict[str, str]]:
    """
    查询家人姓名信息 (Mock)
    
    Returns:
        包含家人信息的列表
    """
    # Mock家人数据
    family_members = [
        {"relationship": "父亲", "name": "王建国", "age": "52"},
        {"relationship": "母亲", "name": "李美华", "age": "48"},
        {"relationship": "哥哥", "name": "王小明", "age": "28"},
        {"relationship": "妹妹", "name": "王小红", "age": "22"},
        {"relationship": "爷爷", "name": "王老爷", "age": "75"},
        {"relationship": "奶奶", "name": "张老太", "age": "72"}
    ]
    
    return family_members

def _get_family_member_by_relationship(relationship: str) -> Dict[str, str]:
    """
    根据关系查询特定家人信息 (Mock)
    
    Args:
        relationship: 家人关系 (如：父亲、母亲、哥哥、妹妹等)
        
    Returns:
        包含家人信息的字典，如果未找到则返回空字典
    """
    family_members = _get_family_names()
    
    for member in family_members:
        if member["relationship"] == relationship:
            return member
    
    return {"error": f"未找到关系为'{relationship}'的家人"}

# 使用装饰器创建 LangChain 工具
@tool
def get_weather(location: str) -> Dict[str, Any]:
    """
    查询指定地点的天气信息 (Mock)
    
    Args:
        location: 地点名称
        
    Returns:
        包含天气信息的字典
    """
    return _get_weather(location)

@tool
def get_family_names() -> List[Dict[str, str]]:
    """
    查询家人姓名信息 (Mock)
    
    Returns:
        包含家人信息的列表
    """
    return _get_family_names()

@tool
def get_family_member_by_relationship(relationship: str) -> Dict[str, str]:
    """
    根据关系查询特定家人信息 (Mock)
    
    Args:
        relationship: 家人关系 (如：父亲、母亲、哥哥、妹妹等)
        
    Returns:
        包含家人信息的字典，如果未找到则返回空字典
    """
    return _get_family_member_by_relationship(relationship)


# 工具列表，用于 LangChain create_react_agent
TOOLS_LIST = [
    get_weather,
    get_family_names,
    get_family_member_by_relationship
]


AUTO_APPROVE_TOOLS = [
    #get_weather,
    get_family_names,
    get_family_member_by_relationship
]


# 工具注册字典，方便调用
TOOLS = {
    "get_weather": {
        "function": _get_weather,
        "description": "查询指定地点的天气信息",
        "parameters": {
            "location": "地点名称 (字符串)"
        }
    },
    "get_family_names": {
        "function": _get_family_names,
        "description": "查询所有家人姓名信息",
        "parameters": {}
    },
    "get_family_member_by_relationship": {
        "function": _get_family_member_by_relationship,
        "description": "根据关系查询特定家人信息",
        "parameters": {
            "relationship": "家人关系 (字符串)"
        }
    }
}

def call_tool(tool_name: str, **kwargs) -> Any:
    """
    调用指定的工具函数
    
    Args:
        tool_name: 工具名称
        **kwargs: 工具函数的参数
        
    Returns:
        工具函数的返回值
    """
    if tool_name not in TOOLS:
        return {"error": f"工具 '{tool_name}' 不存在"}
    
    try:
        return TOOLS[tool_name]["function"](**kwargs)
    except Exception as e:
        return {"error": f"调用工具 '{tool_name}' 时发生错误: {str(e)}"}

# 示例使用
if __name__ == "__main__":
    # 测试天气查询
    print("=== 天气查询测试 ===")
    weather_info = call_tool("get_weather", location="北京")
    print(f"北京天气: {weather_info}")
    
    # 测试家人姓名查询
    print("\n=== 家人姓名查询测试 ===")
    family_info = call_tool("get_family_names")
    print("家人信息:")
    for member in family_info:
        print(f"  {member['relationship']}: {member['name']} (年龄: {member['age']})")
    
    # 测试根据关系查询家人
    print("\n=== 根据关系查询家人测试 ===")
    father_info = call_tool("get_family_member_by_relationship", relationship="父亲")
    print(f"父亲信息: {father_info}")
    
    # 测试自动批准功能
    print("\n=== 自动批准功能测试 ===")
    print("自动批准的工具:")
    for tool_name in get_auto_approve_tool_names():
        print(f"  - {tool_name}")
    
    print(f"\nget_weather 是否自动批准: {is_tool_auto_approved('get_weather')}")
    print(f"get_family_names 是否自动批准: {is_tool_auto_approved('get_family_names')}")
    
    # 测试修改自动批准设置
    print("\n=== 修改自动批准设置测试 ===")
    set_tool_auto_approve("get_weather", False)
    print(f"修改后 get_weather 是否自动批准: {is_tool_auto_approved('get_weather')}")
    print(f"get_weather 工具对象的 auto_approve 属性: {getattr(get_weather, 'auto_approve', 'Not set')}")
    
    # 演示如何在 LangChain 中使用
    print("\n=== LangChain 工具使用示例 ===")
    print("在 LangChain 中使用这些工具:")
    print("from langchain.agents import create_react_agent")
    print("from internal_tools import TOOLS_LIST, get_auto_approve_tool_names")
    print("")
    print("# 创建 React Agent")
    print("agent = create_react_agent(llm, TOOLS_LIST, prompt)")
    print("# 获取自动批准工具列表")
    print("auto_approve_tools = get_auto_approve_tool_names()")
    print("# 使用 agent 执行任务")
    print("agent.invoke({'input': '查询北京的天气'})")
    print("agent.invoke({'input': '我父亲叫什么名字'})")