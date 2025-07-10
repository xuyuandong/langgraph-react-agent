import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings(BaseSettings):
    """配置管理类"""
    
    # DeepSeek配置
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "sk-")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.siliconflow.cn/v1")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3")
    
    # 向量数据库配置
    chroma_persist_directory: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
    
    # 记忆配置
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "./data/memory.db")
    
    # Web搜索配置
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    
    # MCP配置
    mcp_server_host: str = os.getenv("MCP_SERVER_HOST", "localhost")
    mcp_server_port: int = int(os.getenv("MCP_SERVER_PORT", "8080"))
    
    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 数据目录
    data_directory: str = os.getenv("DATA_DIRECTORY", "./data")
    

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保数据目录存在
        os.makedirs(self.data_directory, exist_ok=True)
        os.makedirs(self.chroma_persist_directory, exist_ok=True)
        os.makedirs(os.path.dirname(self.sqlite_db_path), exist_ok=True)


# 全局配置实例
settings = Settings()
