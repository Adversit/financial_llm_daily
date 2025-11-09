"""
配置管理模块
使用 pydantic-settings 管理所有环境变量和配置项
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # 基础配置
    TZ: str = "Asia/Shanghai"
    ENV: str = "development"

    # 数据库
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # LLM Provider - DeepSeek
    PROVIDER_DEEPSEEK_API_KEY: str
    PROVIDER_DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    PROVIDER_DEEPSEEK_MODEL: str = "deepseek-chat"

    # LLM Provider - Qwen
    PROVIDER_QWEN_API_KEY: str
    PROVIDER_QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    PROVIDER_QWEN_MODEL: str = "qwen-max"

    # 采集配置
    CRAWL_CONCURRENCY_RSS: int = 10
    CRAWL_CONCURRENCY_WEB: int = 2
    CRAWL_TIMEOUT_SEC: int = 30
    CRAWL_RETRY_TIMES: int = 3

    # LLM 配置
    LLM_TIMEOUT_SEC: int = 90
    LLM_RETRIES: int = 2
    LLM_CHUNK_BUDGET: float = 0.7
    LLM_CHUNK_OVERLAP_CHARS: int = 200
    LLM_MAX_CHUNKS_PER_ARTICLE: int = 8
    LLM_LONGFORM_STRATEGY: str = "summary_then_extract"
    LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING: bool = False

    # 报告配置
    REPORT_TOPN: int = 5
    CONFIDENCE_THRESHOLD: float = 0.6
    MIN_CONTENT_LEN: int = 120
    ATTACHMENT_MAX_ITEMS: int = 500  # 附件最多包含的事实观点数量，防止邮件过大
    REPORT_USE_LLM_SECTIONS: bool = False  # 是否使用 LLM 生成分区报告（False=仅展示卡片）
    REPORT_LLM_MODEL_LIMIT: int = 64000  # LLM 模型输入限制（token，DeepSeek/Qwen 64K 上下文）
    REPORT_LLM_BUDGET: float = 0.7  # 可用预算比例（70%，即约 44800 tokens）
    REPORT_SECTION_MAX_ITEMS_PER_CHUNK: int = 20  # 每次 LLM 调用最多处理的事实观点数（分块用）

    # JWT 配置
    JWT_SECRET_KEY: str = "dev-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    # OTP 配置
    OTP_TTL_SECONDS: int = 600
    OTP_RESEND_INTERVAL: int = 60
    OTP_MAX_ATTEMPTS: int = 5

    # 前端配置
    THEME_PRIMARY_COLOR: str = "#1d4ed8"
    STOPWORDS_PATH: str = "./config/stopwords_zh.txt"

    # 安全配置
    ENABLE_CSRF: bool = False
    ENABLE_RATE_LIMIT: bool = False
    ALLOWED_HOSTS: str = "*"
    CORS_ORIGINS: str = "*"

    # 缓存配置
    WORDCLOUD_CACHE_TTL: int = 86400

    # 邮件配置
    SMTP_HOST: str = "smtp.163.com"
    SMTP_PORT: int = 465
    SMTP_USER: str
    SMTP_PASS: str
    MAIL_BATCH_LIMIT: int = 50
    MAIL_RATE_LIMIT_PER_SEC: float = 1.0
    # 注：串行执行模式下无需时间窗口限制，任务完成即发送


# 全局配置实例
settings = Settings()
