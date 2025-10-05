"""
Configuration Management

환경변수 및 설정 중앙 관리 모듈
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application Configuration"""

    # Azure OpenAI Configuration
    AOAI_API_KEY: str = os.getenv("AOAI_API_KEY", "")
    AOAI_ENDPOINT: str = os.getenv("AOAI_ENDPOINT", "")
    AOAI_API_VERSION: str = os.getenv("AOAI_API_VERSION", "2024-05-01-preview")
    AOAI_DEPLOY_GPT4O: str = os.getenv("AOAI_DEPLOY_GPT4O", "")
    AOAI_EMBEDDING_DEPLOYMENT: str = os.getenv("AOAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")

    # MCP Server Configuration
    MCP_SERVER_HOST: str = os.getenv("MCP_SERVER_HOST", "localhost")
    MCP_SERVER_PORT: str = os.getenv("MCP_SERVER_PORT", "9000")
    MCP_SERVER_PROTOCOL: str = os.getenv("MCP_SERVER_PROTOCOL", "http")
    MCP_BASE_PATH: str = os.getenv("MCP_BASE_PATH", "/mcp")
    MCP_TIMEOUT: int = int(os.getenv("MCP_TIMEOUT", "30"))

    # Atlassian Configuration
    ATLASSIAN_URL: str = os.getenv("ATLASSIAN_URL", "")
    ATLASSIAN_EMAIL: str = os.getenv("ATLASSIAN_EMAIL", "")
    ATLASSIAN_API_TOKEN: str = os.getenv("ATLASSIAN_API_TOKEN", "")

    # Database Configuration
    DB_PATH: str = os.getenv("DB_PATH", "history.db")

    # RAG Configuration
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
    RAG_SCORE_THRESHOLD: float = float(os.getenv("RAG_SCORE_THRESHOLD", "0.7"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    # Data Collection Schedule
    COLLECTION_SCHEDULE_JIRA: str = os.getenv("COLLECTION_SCHEDULE_JIRA", "0 */6 * * *")
    COLLECTION_SCHEDULE_CONFLUENCE: str = os.getenv("COLLECTION_SCHEDULE_CONFLUENCE", "0 0 * * *")

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "app/logs/system.log")

    # Langfuse Configuration (Optional)
    LANGFUSE_PUBLIC_KEY: Optional[str] = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY: Optional[str] = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST: Optional[str] = os.getenv("LANGFUSE_HOST")

    # Support Configuration
    SUPPORT_EMAIL: str = os.getenv("SUPPORT_EMAIL", "support@company.com")
    SUPPORT_PHONE: str = os.getenv("SUPPORT_PHONE", "1234-5678")

    @classmethod
    def get_mcp_server_url(cls) -> str:
        """Get full MCP server URL"""
        return f"{cls.MCP_SERVER_PROTOCOL}://{cls.MCP_SERVER_HOST}:{cls.MCP_SERVER_PORT}{cls.MCP_BASE_PATH}"

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_fields = [
            ("AOAI_API_KEY", cls.AOAI_API_KEY),
            ("AOAI_ENDPOINT", cls.AOAI_ENDPOINT),
            ("AOAI_DEPLOY_GPT4O", cls.AOAI_DEPLOY_GPT4O),
        ]

        missing = [name for name, value in required_fields if not value]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True


# Singleton instance
config = Config()
