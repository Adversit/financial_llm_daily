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
    PROVIDER_QWEN_MODEL: str = "qwen-plus"  # 使用qwen-plus作为默认(性价比最高)

    # LLM 成本配置 (人民币元/百万tokens)
    # 格式: provider:model = {"input": 输入价格, "output": 输出价格}
    # 如果模型未配置,将使用 provider 的默认定价
    # 价格来源: DeepSeek官网 2025-01-13, 通义千问官网(需核实)
    LLM_PRICING: dict = {
        # DeepSeek 定价 (更新于 2025-01-13)
        # 来源: https://api-docs.deepseek.com/zh-cn/quick_start/pricing
        # 注: 暂不考虑缓存命中(¥0.2/M),使用缓存未命中价格
        "deepseek:deepseek-chat": {"input": 2.0, "output": 3.0},
        "deepseek:deepseek-reasoner": {"input": 2.0, "output": 3.0},
        "deepseek:default": {"input": 2.0, "output": 3.0},
        # Qwen 定价 (更新于 2025-01-13)
        # qwen3-max: 输入 ¥0.006/千tokens = ¥6/百万tokens
        #            输出 ¥0.024/千tokens = ¥24/百万tokens
        # qwen-plus-2025: 输入 ¥0.0008/千tokens = ¥0.8/百万tokens
        #                 输出 ¥0.002/千tokens = ¥2.0/百万tokens
        # 注: 长上下文(>32k)定价可能不同,当前配置为标准定价
        "qwen:qwen-max": {"input": 6.0, "output": 24.0},
        "qwen:qwen-plus": {"input": 0.8, "output": 2.0},
        "qwen:qwen-turbo": {"input": 0.3, "output": 0.6},  # 待核实
        "qwen:default": {"input": 6.0, "output": 24.0},
    }

    # 采集配置
    CRAWL_CONCURRENCY_RSS: int = 10
    CRAWL_CONCURRENCY_WEB: int = 2
    CRAWL_CONCURRENCY_DYNAMIC: int = 2  # 动态采集并发数
    CRAWL_TIMEOUT_SEC: int = 30
    CRAWL_RETRY_TIMES: int = 3

    # Playwright 配置
    PLAYWRIGHT_MAX_BROWSERS: int = 5  # 最大浏览器上下文数
    PLAYWRIGHT_HEADLESS: bool = True  # 无头模式
    PLAYWRIGHT_TIMEOUT_MS: int = 30000  # 页面加载超时（毫秒）
    PLAYWRIGHT_WAIT_UNTIL: str = "domcontentloaded"  # 等待策略: load/domcontentloaded/networkidle
    PLAYWRIGHT_PROXY: str = ""  # 代理服务器（如 "http://127.0.0.1:7890"），留空则不使用代理

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

    # 词云配置
    WORDCLOUD_CACHE_TTL: int = 86400  # 词云缓存时间(秒)
    WORDCLOUD_MIN_KEYWORD_FREQ: int = 2  # 最小词频阈值
    WORDCLOUD_MAX_WORDS: int = 100  # 最多显示词数
    WORDCLOUD_SIMILARITY_THRESHOLD: float = 0.8  # 关键词相似度阈值

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
