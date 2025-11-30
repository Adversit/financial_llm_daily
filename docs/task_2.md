# 金融情报日报系统 · 任务二开发文档（前端管理台与可视化）

**版本**：v2.0
**日期**：2025-11-08（Asia/Shanghai）
**范围**：基于阶段一（MVP）后端与数据面，新增登录与权限、管理台、报告浏览与下载、词云与基础统计、用户定制化提示词、部门内功能
**技术栈**：FastAPI + Jinja2 SSR + HTMX/Alpine.js + Tailwind CSS
**目标**：一次生成，零 Bug，稳定可靠

---

## 目录

1. [系统架构与技术选型](#1-系统架构与技术选型)
2. [数据模型扩展](#2-数据模型扩展)
3. [环境配置](#3-环境配置)
4. [认证与鉴权系统](#4-认证与鉴权系统)
5. [前后端接口定义](#5-前后端接口定义)
6. [页面设计与模板](#6-页面设计与模板)
7. [安全与性能](#7-安全与性能)
8. [测试策略](#8-测试策略)
9. [部署与运维](#9-部署与运维)
10. [验收标准](#10-验收标准)

---

## 1. 系统架构与技术选型

### 1.1 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        浏览器 (Browser)                       │
│                  HTML + HTMX + Alpine.js                     │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP/HTTPS
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Web Server                        │
│  ┌───────────────┬──────────────┬────────────────────────┐  │
│  │  Auth Routes  │  Page Routes │  API Routes (JSON)     │  │
│  │  (登录/OTP)   │  (Jinja2 SSR)│  (异步交互)            │  │
│  └───────────────┴──────────────┴────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │          Middleware (JWT验证/CORS/日志)              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ↓             ↓             ↓
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │PostgreSQL│   │  Redis   │   │  SMTP    │
        │(用户数据)│   │(OTP/缓存)│   │(发验证码)│
        └──────────┘   └──────────┘   └──────────┘
```

### 1.2 技术栈

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web框架 | FastAPI | ^0.104.1 | 后端API和SSR |
| 模板引擎 | Jinja2 | ^3.1.2 | 服务端渲染 |
| 前端交互 | HTMX | 1.9.x (CDN) | 无刷新加载 |
| 前端状态 | Alpine.js | 3.x (CDN) | 轻量级交互 |
| 样式框架 | Tailwind CSS | 3.x (CDN) | 样式库 |
| 认证 | JWT (PyJWT) | ^2.8.0 | 用户认证 |
| OTP | Redis | ^5.0.1 | 验证码存储 |
| 词云 | wordcloud + jieba | 1.* + 0.42.* | 中文词云 |
| HTML净化 | bleach | ^6.1.0 | XSS防护 |
| 密码哈希 | passlib[bcrypt] | ^1.7.4 | 管理员密码 |
| 邮箱验证 | email-validator | ^2.1.0 | 邮箱格式验证 |

### 1.3 新增依赖

在现有 `pyproject.toml` 的基础上添加：

```toml
# 前端相关
pyjwt = {extras = ["crypto"], version = "^2.8.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
email-validator = "^2.1.0"
python-multipart = "^0.0.6"  # 表单数据解析

# 可视化
wordcloud = "^1.9.3"
jieba = "^0.42.1"
matplotlib = "^3.8.2"  # wordcloud 依赖

# 安全
bleach = "^6.1.0"
itsdangerous = "^2.1.2"  # 签名辅助（可选）
```

### 1.4 目录结构（新增部分）

```
src/
├── web/                          # 新增：Web 前端模块
│   ├── __init__.py
│   ├── app.py                   # FastAPI 应用装配
│   ├── deps.py                  # 依赖注入（数据库、当前用户）
│   ├── security.py              # 安全工具（JWT、密码哈希）
│   ├── auth.py                  # 认证逻辑（OTP、登录）
│   ├── middleware.py            # 中间件（可选）
│   ├── routes/                  # 路由模块
│   │   ├── __init__.py
│   │   ├── auth.py             # 认证路由
│   │   ├── home.py             # 首页
│   │   ├── reports.py          # 报告浏览
│   │   ├── stats.py            # 统计与词云
│   │   ├── preferences.py      # 用户偏好
│   │   ├── admin/              # 管理员路由
│   │   │   ├── __init__.py
│   │   │   ├── sources.py     # 信息源管理
│   │   │   ├── recipients.py  # 收件人管理
│   │   │   ├── settings.py    # 系统设置
│   │   │   ├── audit.py       # 操作审计
│   │   │   ├── status.py      # 系统状态
│   │   │   ├── watchlist.py   # 关注清单
│   │   │   └── blocklist.py   # 屏蔽规则
│   │   └── assets.py           # 静态资源（词云PNG、附件下载）
│   ├── templates/               # Jinja2 模板
│   │   ├── base.html           # 基础布局
│   │   ├── components/         # 可复用组件
│   │   │   ├── navbar.html
│   │   │   ├── sidebar.html
│   │   │   ├── footer.html
│   │   │   └── flash.html
│   │   ├── auth/
│   │   │   └── login.html
│   │   ├── reports/
│   │   │   ├── list.html
│   │   │   └── detail.html
│   │   ├── stats/
│   │   │   ├── wordcloud.html
│   │   │   └── summary.html
│   │   ├── preferences/
│   │   │   └── index.html
│   │   └── admin/
│   │       ├── sources.html
│   │       ├── recipients.html
│   │       ├── whitelist.html
│   │       ├── settings.html
│   │       ├── audit.html
│   │       ├── status.html
│   │       ├── watchlist.html
│   │       └── blocklist.html
│   └── static/                  # 静态文件
│       ├── css/
│       │   └── custom.css
│       ├── js/
│       │   └── app.js
│       └── images/
│           └── logo.png
└── models/                       # 扩展现有模型
    └── user.py                  # 新增用户相关模型
```

---

## 2. 数据模型扩展

### 2.1 现有模型回顾

**已有的核心表**（阶段一已实现）：

| 表名 | 主要字段 | 说明 |
|------|---------|------|
| `sources` | id, name, type, url, enabled, concurrency, timeout_sec, parser, region_hint | 信息源 |
| `articles` | id, source_id, title, url, published_at, content_text, processing_status, simhash | 文章 |
| `extraction_queue` | id, article_id, provider_hint, status, attempts, last_error | 抽取队列 |
| `extraction_items` | id, article_id, fact, opinion, region, layer, confidence, finance_relevance | 抽取结果 |
| `reports` | id, report_date, version, overview_summary, sections_json, html_body, html_attachment | 日报 |
| `report_recipients` | id, email, display_name, type, enabled | 收件人/白名单 |
| `delivery_log` | id, report_id, batch_no, status, error_message, sent_at | 投递日志 |
| `provider_usage` | id, provider_name, model_name, article_id, prompt_tokens, completion_tokens, cost | 费用统计 |

**已有的枚举类型**：

```python
# src/models/source.py
class SourceType(str, enum.Enum):
    RSS = "rss"
    STATIC = "static"
    DYNAMIC = "dynamic"

class RegionHint(str, enum.Enum):
    DOMESTIC = "国内"
    FOREIGN = "国外"
    UNKNOWN = "未知"

# src/models/extraction.py
class Region(str, enum.Enum):
    DOMESTIC = "国内"
    FOREIGN = "国外"
    UNKNOWN = "未知"

class Layer(str, enum.Enum):
    FINANCIAL_POLICY = "金融政策监管"
    FINANCIAL_ECONOMY = "金融经济"
    FINTECH_AI = "金融大模型技术"
    FINTECH = "金融科技应用"
    UNKNOWN = "未知"

# src/models/delivery.py
class RecipientType(str, enum.Enum):
    WHITELIST = "whitelist"
    RECIPIENT = "recipient"

class DeliveryStatus(str, enum.Enum):
    OK = "ok"
    FAILED = "failed"
    PARTIAL = "partial"
```

### 2.2 新增模型

#### 2.2.1 用户表 `users`

```python
# src/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from .base import Base, TimestampMixin

class UserRole(str, enum.Enum):
    """用户角色"""
    ADMIN = "admin"
    USER = "user"

class User(Base, TimestampMixin):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(200), nullable=False, unique=True, comment="邮箱地址")
    role = Column(
        SQLEnum(UserRole, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.USER,
        nullable=False,
        comment="角色"
    )
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")

    # 仅管理员使用的密码字段（普通用户通过OTP登录）
    hashed_password = Column(String(200), nullable=True, comment="哈希密码（仅admin）")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
```

**说明**：
- 普通用户（`role=user`）仅通过 OTP 登录，`hashed_password` 为 NULL
- 管理员（`role=admin`）默认账号 `xtyydsf@system.local`（登录时也可直接输入 `xtyydsf`），密码 `xtyydsf`（bcrypt 哈希存储）
- OTP 本身不落库，存 Redis（`otp:{email}`，TTL 10分钟）

#### 2.2.2 用户偏好表 `user_preferences`

```python
# src/models/user.py 中继续添加

class PreferenceScope(str, enum.Enum):
    """偏好范围"""
    DAILY = "daily"       # 全局/当日生效
    ARTICLE = "article"   # 单篇文章

class UserPreference(Base, TimestampMixin):
    """用户偏好/定制模板表"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(200), nullable=False, comment="用户邮箱")
    name = Column(String(100), nullable=False, comment="模板名称")
    scope = Column(
        SQLEnum(PreferenceScope, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="作用范围"
    )
    prompt_text = Column(Text, nullable=False, comment="提示词内容")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否默认模板")

    __table_args__ = (
        Index("idx_user_preferences_email", "user_email"),
        UniqueConstraint("user_email", "name", name="uq_user_email_name"),
    )

    def __repr__(self):
        return f"<UserPreference(id={self.id}, email={self.user_email}, name={self.name})>"
```

**约束**：
- 每用户最多 5 条偏好（应用层校验）
- `(user_email, name)` 唯一
- `prompt_text` 长度上限 2000 字符（应用层校验）

#### 2.2.3 关注清单表 `watchlist_rules`

```python
# src/models/user.py 中继续添加

class RuleType(str, enum.Enum):
    """规则类型"""
    SOURCE = "source"      # 来源匹配
    KEYWORD = "keyword"    # 关键词匹配

class WatchlistRule(Base, TimestampMixin):
    """关注清单规则表"""
    __tablename__ = "watchlist_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(
        SQLEnum(RuleType, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="规则类型"
    )
    pattern = Column(String(200), nullable=False, comment="匹配模式")
    created_by = Column(String(200), nullable=False, comment="创建者邮箱")
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级（数字越大越靠前）")

    __table_args__ = (
        Index("idx_watchlist_enabled", "is_enabled"),
    )

    def __repr__(self):
        return f"<WatchlistRule(id={self.id}, type={self.type}, pattern={self.pattern})>"
```

#### 2.2.4 黑名单表 `blocklist_rules`

```python
# src/models/user.py 中继续添加

class BlocklistRule(Base, TimestampMixin):
    """黑名单规则表"""
    __tablename__ = "blocklist_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(
        SQLEnum(RuleType, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="规则类型"
    )
    pattern = Column(String(200), nullable=False, comment="匹配模式")
    created_by = Column(String(200), nullable=False, comment="创建者邮箱")
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    reason = Column(String(500), nullable=True, comment="屏蔽原因")

    __table_args__ = (
        Index("idx_blocklist_enabled", "is_enabled"),
    )

    def __repr__(self):
        return f"<BlocklistRule(id={self.id}, type={self.type}, pattern={self.pattern})>"
```

#### 2.2.5 报告备注表 `report_notes`

```python
# src/models/user.py 中继续添加

class NoteScope(str, enum.Enum):
    """备注范围"""
    GLOBAL = "global"      # 全局（报告顶部）
    SECTION = "section"    # 分区级别

class ReportNote(Base, TimestampMixin):
    """报告备注表"""
    __tablename__ = "report_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, nullable=False, comment="报告日期")
    scope = Column(
        SQLEnum(NoteScope, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="范围"
    )
    section_key = Column(String(100), nullable=True, comment="分区键（如：国内-金融经济）")
    author_email = Column(String(200), nullable=False, comment="作者邮箱")
    content_md = Column(Text, nullable=False, comment="备注内容（Markdown）")

    __table_args__ = (
        Index("idx_report_notes_date", "report_date"),
    )

    def __repr__(self):
        return f"<ReportNote(id={self.id}, date={self.report_date}, scope={self.scope})>"
```

#### 2.2.6 系统设置表 `system_settings`（扩展）

该表已在 PRD 中定义，但需要明确具体结构：

```python
# src/models/system.py（新建）
from sqlalchemy import Column, Integer, String, JSON, DateTime, Text
from .base import Base
from src.utils.time_utils import get_local_now_naive

class SystemSetting(Base):
    """系统设置表"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, comment="配置键")
    value_json = Column(JSON, nullable=True, comment="配置值（JSON）")
    description = Column(Text, nullable=True, comment="说明")
    updated_at = Column(DateTime, default=get_local_now_naive, onupdate=get_local_now_naive, nullable=False)

    def __repr__(self):
        return f"<SystemSetting(key={self.key})>"
```

**预置配置键**：

| key | value_json 示例 | 说明 |
|-----|----------------|------|
| `report_topn` | `5` | 报告正文每区 TopN |
| `confidence_threshold` | `0.6` | 置信度阈值 |
| `min_content_len` | `120` | 最小内容长度 |
| `theme_color` | `"#1d4ed8"` | 主题色（蓝色） |
| `stopwords` | `["的", "是", "在", ...]` | 停用词列表 |
| `admin_password_hash` | `"$2b$12$..."` | 管理员密码哈希 |
| `daily_prompt_overrides` | `{"2025-11-08": {"user@example.com": "..."}}` | 当日全局提示词 |

#### 2.2.7 操作审计日志表 `admin_audit_log`

```python
# src/models/system.py 中继续添加

class AdminAuditLog(Base):
    """管理员操作审计日志"""
    __tablename__ = "admin_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_email = Column(String(200), nullable=False, comment="管理员邮箱")
    action = Column(String(100), nullable=False, comment="操作类型")
    resource_type = Column(String(50), nullable=True, comment="资源类型（source/recipient等）")
    resource_id = Column(Integer, nullable=True, comment="资源ID")
    before_json = Column(JSON, nullable=True, comment="操作前数据")
    after_json = Column(JSON, nullable=True, comment="操作后数据")
    ip_address = Column(String(50), nullable=True, comment="IP地址")
    user_agent = Column(String(500), nullable=True, comment="User-Agent")
    created_at = Column(DateTime, default=get_local_now_naive, nullable=False)

    __table_args__ = (
        Index("idx_audit_email", "admin_email"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<AdminAuditLog(id={self.id}, action={self.action})>"
```

### 2.3 数据库迁移

使用 Alembic 创建迁移文件：

```bash
# 在 WSL 环境中执行
source .venv/bin/activate
alembic revision --autogenerate -m "add_stage2_models_users_preferences_watchlist_blocklist_notes_settings_audit"
alembic upgrade head
```

迁移脚本应包含：
1. 创建 `users` 表，并插入默认管理员账号
2. 创建 `user_preferences`、`watchlist_rules`、`blocklist_rules`、`report_notes` 表
3. 创建 `system_settings` 表，并插入默认配置
4. 创建 `admin_audit_log` 表

---

## 3. 环境配置

### 3.1 环境变量扩展

在现有 `.env` 基础上添加：

```bash
# ========== 新增：JWT 配置 ==========
JWT_SECRET_KEY="your-super-secret-jwt-key-change-in-production"
JWT_ALGORITHM="HS256"
JWT_EXPIRE_DAYS=7

# ========== 新增：OTP 配置 ==========
OTP_TTL_SECONDS=600          # OTP 过期时间（10分钟）
OTP_RESEND_INTERVAL=60       # 重发间隔（60秒）
OTP_MAX_ATTEMPTS=5           # 最大尝试次数（10分钟内）

# ========== 新增：前端配置 ==========
THEME_PRIMARY_COLOR="#1d4ed8"  # 主题色（蓝色）
STOPWORDS_PATH="./config/stopwords_zh.txt"  # 停用词文件

# ========== 新增：安全配置 ==========
ENABLE_CSRF=false            # 是否启用 CSRF（首版暂不启用）
ENABLE_RATE_LIMIT=false      # 是否启用接口限流（首版暂不启用）
ALLOWED_HOSTS="*"            # 允许的主机（生产环境应限制）
CORS_ORIGINS="*"             # CORS 允许的来源（生产环境应限制）

# ========== 新增：缓存配置 ==========
WORDCLOUD_CACHE_TTL=86400    # 词云缓存时间（24小时）
```

### 3.2 配置类扩展

```python
# src/config/settings.py 中添加

class Settings(BaseSettings):
    # ... 现有配置 ...

    # JWT 配置
    JWT_SECRET_KEY: str
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
```

---

## 4. 认证与鉴权系统

### 4.1 安全工具模块

```python
# src/web/security.py
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from src.config.settings import settings

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.JWT_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """解码 JWT Token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None
```

### 4.2 OTP 管理模块

```python
# src/web/auth.py
import random
import redis
from datetime import datetime
from loguru import logger
from src.config.settings import settings
from src.mailer.smtp_client import send_email

# Redis 客户端
redis_client = redis.from_url(settings.REDIS_URL)

def generate_otp() -> str:
    """生成 6 位数字 OTP"""
    return str(random.randint(100000, 999999))

def send_otp_email(email: str, otp: str) -> bool:
    """发送 OTP 邮件"""
    try:
        subject = "【金融情报日报】登录验证码"
        body = f"""
您的登录验证码是：<b>{otp}</b>

该验证码将在 10 分钟后失效。

如果这不是您的操作,请忽略此邮件。

---
金融情报日报系统
        """
        send_email(
            to_email=email,
            subject=subject,
            body=body,
            is_html=True
        )
        return True
    except Exception as e:
        logger.error(f"发送 OTP 邮件失败: {email}, 错误: {e}")
        return False

def store_otp(email: str, otp: str) -> None:
    """存储 OTP 到 Redis"""
    key = f"otp:{email}"
    redis_client.setex(key, settings.OTP_TTL_SECONDS, otp)
    logger.info(f"OTP 已存储: {email}, 过期时间: {settings.OTP_TTL_SECONDS}秒")

def verify_otp(email: str, otp: str) -> bool:
    """验证 OTP"""
    key = f"otp:{email}"
    stored_otp = redis_client.get(key)
    if stored_otp is None:
        logger.warning(f"OTP 不存在或已过期: {email}")
        return False

    if stored_otp.decode() == otp:
        # 验证成功后删除 OTP（一次性消费）
        redis_client.delete(key)
        logger.success(f"OTP 验证成功: {email}")
        return True
    else:
        logger.warning(f"OTP 验证失败: {email}")
        return False

def check_resend_interval(email: str) -> bool:
    """检查重发间隔（防止频繁发送）"""
    key = f"otp_resend:{email}"
    if redis_client.exists(key):
        return False
    redis_client.setex(key, settings.OTP_RESEND_INTERVAL, "1")
    return True

def increment_otp_attempts(email: str) -> int:
    """增加 OTP 尝试次数"""
    key = f"otp_attempts:{email}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 600)  # 10 分钟过期
    return count

def check_otp_attempts(email: str) -> bool:
    """检查 OTP 尝试次数是否超限"""
    key = f"otp_attempts:{email}"
    count = redis_client.get(key)
    if count is None:
        return True
    return int(count) < settings.OTP_MAX_ATTEMPTS
```

### 4.3 依赖注入模块

```python
# src/web/deps.py
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.models.user import User, UserRole
from src.web.security import decode_access_token

def get_current_user(
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(None, alias="access_token")
) -> Optional[User]:
    """获取当前登录用户"""
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(access_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 格式错误"
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用"
        )

    return user

def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """要求管理员权限"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

def get_current_user_optional(
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(None, alias="access_token")
) -> Optional[User]:
    """获取当前用户（可选，不强制登录）"""
    if access_token is None:
        return None

    try:
        payload = decode_access_token(access_token)
        if payload is None:
            return None

        email: str = payload.get("sub")
        if email is None:
            return None

        user = db.query(User).filter(User.email == email).first()
        return user if user and user.is_active else None
    except:
        return None
```

---

## 5. 前后端接口定义

### 5.1 认证相关 API

#### 5.1.1 登录页面

**路由**：`GET /login`

**参数**：无

**返回**：HTML 页面（Jinja2 模板）

**模板变量**：
```python
{
    "error": str | None,  # 错误信息（如：登录失败）
    "next": str | None,   # 登录后跳转地址
}
```

---

#### 5.1.2 请求 OTP

**路由**：`POST /auth/otp/request`

**Content-Type**：`application/x-www-form-urlencoded`

**请求参数**：
```python
class OTPRequestForm:
    email: str  # 邮箱地址
```

**业务逻辑**：
1. 验证邮箱格式（使用 `email-validator`）
2. 检查邮箱是否在白名单中（`report_recipients` 表，`type='whitelist'`, `enabled=true`）
3. 检查重发间隔（Redis `otp_resend:{email}`，60秒内不可重发）
4. 生成 6 位数字 OTP
5. 存储到 Redis（`otp:{email}`，TTL 10分钟）
6. 发送邮件（使用现有 `smtp_client`）

**响应**：
```json
{
  "success": true,
  "message": "验证码已发送，请检查您的邮箱"
}
```

**错误响应**：
```json
{
  "success": false,
  "error": "邮箱格式错误" | "请稍后再试" | "邮件发送失败"
}
```

**安全措施**：
- 不论邮箱是否在白名单，均返回统一成功提示（防止邮箱枚举）
- 但仅对白名单邮箱真正发送 OTP

---

#### 5.1.3 验证 OTP 并登录

**路由**：`POST /auth/otp/verify`

**Content-Type**：`application/x-www-form-urlencoded`

**请求参数**：
```python
class OTPVerifyForm:
    email: str  # 邮箱地址
    otp: str    # 6 位验证码
```

**业务逻辑**：
1. 检查 OTP 尝试次数（Redis `otp_attempts:{email}`，10分钟内最多 5 次）
2. 从 Redis 获取存储的 OTP（`otp:{email}`）
3. 验证 OTP 是否正确
4. 验证成功后：
   - 删除 Redis 中的 OTP（一次性消费）
   - 查询 `users` 表，如果不存在则创建（`role=user`）
   - 更新 `last_login_at`
   - 生成 JWT Token（有效期 7 天）
   - 设置 HttpOnly Cookie（`access_token`）
   - 重定向到首页或 `next` 参数指定的页面

**响应**：
- 成功：`302 Redirect` + `Set-Cookie: access_token=...; HttpOnly; SameSite=Lax; Secure`
- 失败：`401 Unauthorized` + JSON 错误

**错误响应**：
```json
{
  "success": false,
  "error": "验证码错误" | "验证码已过期" | "尝试次数过多，请稍后再试"
}
```

---

#### 5.1.4 管理员密码登录

**路由**：`POST /auth/admin/login`

**Content-Type**：`application/x-www-form-urlencoded`

**请求参数**：
```python
class AdminLoginForm:
    username: str  # 默认 "admin"
    password: str  # 默认 "xtyydsf"
```

**业务逻辑**：
1. 查询 `users` 表，`email='xtyydsf@system.local'`（固定管理员账号）
2. 验证密码（bcrypt）
3. 验证成功后生成 JWT Token 并设置 Cookie
4. 重定向到管理后台首页

**响应**：
- 成功：`302 Redirect` + `Set-Cookie`
- 失败：`401 Unauthorized` + JSON 错误

---

#### 5.1.5 登出

**路由**：`POST /auth/logout`

**参数**：无

**响应**：
```python
# 清除 Cookie
response = RedirectResponse(url="/login", status_code=302)
response.delete_cookie("access_token")
return response
```

---

### 5.2 报告浏览 API

#### 5.2.1 报告列表页

**路由**：`GET /reports`

**权限**：需要登录（`user` 或 `admin`）

**查询参数**：
```python
class ReportsListQuery:
    page: int = 1           # 页码（默认 1）
    per_page: int = 20      # 每页条数（默认 20）
    date: str | None = None # 日期过滤（YYYY-MM-DD）
    region: str | None = None  # 区域过滤（国内/国外）
    layer: str | None = None   # 层级过滤（金融政策监管/金融经济/...）
    q: str | None = None    # 关键词搜索
```

**业务逻辑**：
1. 从 `reports` 表分页查询报告列表
2. 支持按日期、区域、层级过滤
3. 支持关键词搜索（在 `overview_summary` 或 `sections_json` 中搜索）
4. 每条报告显示：日期、摘要片段、区块统计（各区域/层级条数）、下载入口

**返回**：HTML 页面（Jinja2 模板）

**模板变量**：
```python
{
    "reports": List[{
        "id": int,
        "report_date": str,
        "overview_summary": str,
        "stats": {
            "total_items": int,
            "by_region": {"国内": int, "国外": int},
            "by_layer": {"金融经济": int, ...}
        },
        "download_url": str
    }],
    "pagination": {
        "page": int,
        "per_page": int,
        "total": int,
        "total_pages": int
    },
    "filters": {
        "date": str | None,
        "region": str | None,
        "layer": str | None,
        "q": str | None
    }
}
```

---

#### 5.2.2 报告详情页

**路由**：`GET /reports/{date}`

**参数**：
- `date`：报告日期（YYYY-MM-DD）

**权限**：需要登录

**业务逻辑**：
1. 从 `reports` 表查询指定日期的报告
2. 读取 `html_body`（邮件正文 HTML）
3. 使用 `bleach` 净化 HTML（白名单：`a, p, ul, ol, li, h1-h4, table, thead, tbody, tr, td, th, div, span, br`）
4. 读取该日报告的备注（`report_notes` 表，`report_date=date`）
5. 应用关注清单（`watchlist_rules`）和黑名单（`blocklist_rules`）过滤逻辑

**返回**：HTML 页面

**模板变量**：
```python
{
    "report": {
        "id": int,
        "report_date": str,
        "overview_summary": str,
        "html_body": str,  # 已净化
        "attachment_url": str,  # 附件下载地址
    },
    "notes": List[{
        "scope": str,  # global | section
        "section_key": str | None,
        "content_md": str,
        "author_email": str
    }],
    "watchlist_items": List[Dict],  # 匹配关注清单的条目（置顶）
    "stats": {
        "total_items": int,
        "filtered_items": int  # 应用黑名单后的条数
    }
}
```

---

#### 5.2.3 下载报告附件

**路由**：`GET /assets/attachment/{date}.html`

**参数**：
- `date`：报告日期（YYYY-MM-DD）

**权限**：需要登录

**业务逻辑**：
1. 从 `reports` 表查询 `html_attachment`
2. 设置响应头 `Content-Disposition: attachment; filename="daily-report-{date}.html"`
3. 返回文件内容

**响应**：
```python
return Response(
    content=html_attachment,
    media_type="text/html",
    headers={
        "Content-Disposition": f'attachment; filename="daily-report-{date}.html"'
    }
)
```

---

#### 5.2.4 展开全部事实观点（AJAX）

**路由**：`GET /api/reports/{date}/items`

**参数**：
- `date`：报告日期（YYYY-MM-DD）
- `page`：页码（默认 1）
- `per_page`：每页条数（默认 20）
- `region`：区域过滤（可选）
- `layer`：层级过滤（可选）

**权限**：需要登录

**业务逻辑**：
1. 从 `extraction_items` 表分页查询指定日期的事实观点
2. 通过 `article_id` JOIN `articles` 表获取文章标题和链接
3. 应用黑名单过滤

**返回**：JSON

```json
{
  "items": [
    {
      "fact": "事实描述",
      "opinion": "观点描述",
      "region": "国内",
      "layer": "金融经济",
      "confidence": 0.85,
      "finance_relevance": 0.9,
      "article": {
        "title": "文章标题",
        "url": "https://..."
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

---

### 5.3 统计与词云 API

#### 5.3.1 词云生成

**路由**：`GET /stats/wordcloud`

**查询参数**：
```python
class WordcloudQuery:
    scope: str = "day"  # day | week | month
    date: str           # YYYY-MM-DD（基准日期）
    width: int = 800    # 图片宽度
    height: int = 600   # 图片高度
```

**权限**：需要登录

**业务逻辑**：
1. 检查缓存（Redis `wc:{scope}:{date}:{width}x{height}`，TTL 24小时）
2. 如果缓存存在，直接返回 PNG
3. 否则：
   - 根据 `scope` 计算日期范围（day=当日，week=过去7天，month=过去30天）
   - 从 `extraction_items` 查询该范围内的所有 `fact` 和 `opinion`（非空）
   - 合并文本，使用 `jieba` 分词
   - 加载停用词（`system_settings.stopwords` + 内置停用词）
   - 生成词云（`wordcloud`）
   - 保存为 PNG（BytesIO）
   - 存入 Redis 缓存
4. 返回 PNG 图片

**响应**：
```python
return Response(
    content=image_bytes,
    media_type="image/png",
    headers={
        "Cache-Control": "public, max-age=86400"
    }
)
```

---

#### 5.3.2 统计摘要

**路由**：`GET /stats/summary`

**查询参数**：
```python
class StatsSummaryQuery:
    date: str  # YYYY-MM-DD
```

**权限**：需要登录

**业务逻辑**：
1. 查询指定日期的报告统计数据
2. 汇总各区域/层级的条目数
3. 汇总 Provider 使用量和成本（从 `provider_usage`）
4. 计算平均处理时延（从 `extraction_queue`）

**返回**：JSON 或 HTML

```json
{
  "date": "2025-11-08",
  "total_items": 120,
  "by_region": {
    "国内": 80,
    "国外": 40
  },
  "by_layer": {
    "金融政策监管": 20,
    "金融经济": 50,
    "金融大模型技术": 30,
    "金融科技应用": 20
  },
  "provider_usage": {
    "deepseek": {
      "prompt_tokens": 50000,
      "completion_tokens": 10000,
      "cost": 0.5
    },
    "qwen": {
      "prompt_tokens": 20000,
      "completion_tokens": 5000,
      "cost": 0.3
    }
  },
  "avg_processing_time_ms": 15000
}
```

---

### 5.4 用户偏好 API

#### 5.4.1 偏好列表页

**路由**：`GET /preferences`

**权限**：需要登录

**返回**：HTML 页面

**模板变量**：
```python
{
    "preferences": List[{
        "id": int,
        "name": str,
        "scope": str,  # daily | article
        "prompt_text": str,
        "is_default": bool,
        "created_at": str
    }],
    "can_create_more": bool  # 是否可创建更多（<5条）
}
```

---

#### 5.4.2 创建/更新偏好

**路由**：`POST /preferences`

**Content-Type**：`application/x-www-form-urlencoded`

**请求参数**：
```python
class PreferenceForm:
    id: int | None = None  # None=创建，非None=更新
    name: str              # 模板名称
    scope: str             # daily | article
    prompt_text: str       # 提示词内容（≤2000字）
    is_default: bool = False
```

**业务逻辑**：
1. 校验用户当前偏好数量（<5）
2. 校验 `prompt_text` 长度（≤2000）
3. 如果 `is_default=True`，将该用户其他偏好的 `is_default` 设为 `False`
4. 创建或更新 `user_preferences` 记录

**响应**：
```python
# 成功
return RedirectResponse(url="/preferences", status_code=302)
```

---

#### 5.4.3 删除偏好

**路由**：`POST /preferences/{id}/delete`

**权限**：需要登录

**响应**：
```python
return RedirectResponse(url="/preferences", status_code=302)
```

---

#### 5.4.4 设置当日全局提示词

**路由**：`POST /preferences/set-daily-prompt`

**请求参数**：
```python
class SetDailyPromptForm:
    date: str  # YYYY-MM-DD
    prompt_text: str
```

**业务逻辑**：
1. 写入 `system_settings` 表，`key='daily_prompt_overrides'`
2. 更新 JSON：`{"YYYY-MM-DD": {"user@email.com": "prompt_text"}}`
3. 流水线在次日读取该配置，应用到抽取逻辑

**响应**：JSON

```json
{
  "success": true,
  "message": "当日提示词已设置"
}
```

---

### 5.5 管理员 API

#### 5.5.1 信息源管理页

**路由**：`GET /admin/sources`

**权限**：需要 `admin` 角色

**返回**：HTML 页面

**模板变量**：
```python
{
    "sources": List[{
        "id": int,
        "name": str,
        "type": str,  # rss | static | dynamic
        "url": str,
        "enabled": bool,
        "concurrency": int,
        "timeout_sec": int,
        "parser": str | None,
        "region_hint": str,
        "created_at": str,
        "updated_at": str
    }]
}
```

---

#### 5.5.2 更新信息源

**路由**：`POST /admin/sources/{id}`

**Content-Type**：`application/x-www-form-urlencoded`

**请求参数**：
```python
class SourceUpdateForm:
    enabled: bool
    concurrency: int
    timeout_sec: int
    parser: str | None
    region_hint: str
```

**业务逻辑**：
1. 查询 `sources` 表，记录修改前的值
2. 更新字段
3. 写入审计日志（`admin_audit_log`）

**审计日志示例**：
```json
{
  "admin_email": "xtyydsf@system.local",
  "action": "update_source",
  "resource_type": "source",
  "resource_id": 1,
  "before_json": {"enabled": true, "concurrency": 10},
  "after_json": {"enabled": false, "concurrency": 5},
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2025-11-08T10:30:00"
}
```

**响应**：
```python
return RedirectResponse(url="/admin/sources", status_code=302)
```

---

#### 5.5.3 收件人管理页

**路由**：`GET /admin/recipients`

**权限**：需要 `admin`

**返回**：HTML 页面

**模板变量**：
```python
{
    "recipients": List[{
        "id": int,
        "email": str,
        "display_name": str | None,
        "type": str,  # whitelist | recipient
        "enabled": bool,
        "created_at": str
    }]
}
```

---

#### 5.5.4 添加收件人

**路由**：`POST /admin/recipients`

**请求参数**：
```python
class RecipientCreateForm:
    email: str
    display_name: str | None
    type: str  # whitelist | recipient
    enabled: bool = True
```

**业务逻辑**：
1. 验证邮箱格式
2. 检查是否已存在
3. 创建 `report_recipients` 记录
4. 写入审计日志

**响应**：
```python
return RedirectResponse(url="/admin/recipients", status_code=302)
```

---

#### 5.5.5 删除收件人

**路由**：`POST /admin/recipients/{id}/delete`

**业务逻辑**：
1. 记录删除前数据
2. 删除记录
3. 写入审计日志

**响应**：
```python
return RedirectResponse(url="/admin/recipients", status_code=302)
```

---

#### 5.5.6 系统设置页

**路由**：`GET /admin/settings`

**权限**：需要 `admin`

**返回**：HTML 页面

**模板变量**：
```python
{
    "settings": {
        "report_topn": int,
        "confidence_threshold": float,
        "min_content_len": int,
        "theme_color": str,
        "stopwords": List[str],
        "admin_password": str  # 显示为 ******
    }
}
```

---

#### 5.5.7 更新系统设置

**路由**：`POST /admin/settings`

**请求参数**：
```python
class SystemSettingsForm:
    report_topn: int
    confidence_threshold: float
    min_content_len: int
    theme_color: str
    stopwords: str  # 逗号分隔
    admin_password: str | None  # 如果非空则更新密码
```

**业务逻辑**：
1. 验证参数范围（如 `report_topn >= 1`, `0 <= confidence_threshold <= 1`）
2. 如果 `admin_password` 非空，哈希后更新 `users` 表
3. 更新 `system_settings` 表
4. 写入审计日志

**响应**：
```python
return RedirectResponse(url="/admin/settings", status_code=302)
```

---

#### 5.5.8 操作审计页

**路由**：`GET /admin/audit`

**权限**：需要 `admin`

**查询参数**：
```python
class AuditQuery:
    page: int = 1
    per_page: int = 50
    action: str | None = None  # 过滤操作类型
    admin_email: str | None = None
    date_from: str | None = None  # YYYY-MM-DD
    date_to: str | None = None
```

**返回**：HTML 页面

**模板变量**：
```python
{
    "logs": List[{
        "id": int,
        "admin_email": str,
        "action": str,
        "resource_type": str,
        "resource_id": int,
        "before_json": dict,
        "after_json": dict,
        "ip_address": str,
        "created_at": str
    }],
    "pagination": {...}
}
```

---

#### 5.5.9 系统状态页

**路由**：`GET /admin/status`

**权限**：需要 `admin`

**返回**：HTML 页面

**模板变量**：
```python
{
    "health": {
        "database": {"status": "ok", "message": "..."},
        "redis": {"status": "ok", "message": "..."},
        "celery_workers": {"status": "ok", "workers": [...]}
    },
    "queue_stats": {
        "extraction_queue": {
            "queued": 10,
            "running": 2,
            "done": 150,
            "failed": 5
        }
    },
    "recent_tasks": List[{
        "task_name": str,
        "status": str,
        "timestamp": str,
        "duration_ms": int
    }],
    "provider_status": {
        "deepseek": {"status": "ok", "last_check": "..."},
        "qwen": {"status": "ok", "last_check": "..."}
    }
}
```

---

#### 5.5.10 关注清单管理

**路由**：`GET /admin/watchlist`

**权限**：需要 `admin`

**返回**：HTML 页面

**模板变量**：
```python
{
    "rules": List[{
        "id": int,
        "type": str,  # source | keyword
        "pattern": str,
        "created_by": str,
        "is_enabled": bool,
        "priority": int,
        "created_at": str
    }]
}
```

---

**添加关注规则**：`POST /admin/watchlist`

**请求参数**：
```python
class WatchlistRuleForm:
    type: str  # source | keyword
    pattern: str
    priority: int = 0
    is_enabled: bool = True
```

---

#### 5.5.11 黑名单管理

**路由**：`GET /admin/blocklist`

**权限**：需要 `admin`

**返回**：HTML 页面

**模板变量**：
```python
{
    "rules": List[{
        "id": int,
        "type": str,  # source | keyword
        "pattern": str,
        "created_by": str,
        "is_enabled": bool,
        "reason": str,
        "created_at": str
    }]
}
```

---

**添加黑名单规则**：`POST /admin/blocklist`

**请求参数**：
```python
class BlocklistRuleForm:
    type: str  # source | keyword
    pattern: str
    reason: str | None
    is_enabled: bool = True
```

---

#### 5.5.12 报告备注管理

**路由**：`GET /admin/notes`

**权限**：需要 `admin`

**返回**：HTML 页面

---

**添加备注**：`POST /admin/notes`

**请求参数**：
```python
class ReportNoteForm:
    report_date: str  # YYYY-MM-DD
    scope: str  # global | section
    section_key: str | None  # 如 "国内-金融经济"
    content_md: str  # Markdown 格式
```

---

### 5.6 静态资源 API

#### 5.6.1 下载词云图片

**路由**：`GET /assets/wordcloud/{scope}/{date}.png`

**参数**：
- `scope`：day | week | month
- `date`：YYYY-MM-DD

**响应**：PNG 图片（同 `/stats/wordcloud`）

---

## 6. 页面设计与模板

### 6.1 基础布局模板

```html
<!-- src/web/templates/base.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}金融情报日报系统{% endblock %}</title>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>

    <!-- Alpine.js -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

    <!-- 自定义样式 -->
    <link rel="stylesheet" href="/static/css/custom.css">

    <style>
        :root {
            --primary-color: {{ theme_color | default('#1d4ed8') }};
        }
    </style>
</head>
<body class="bg-gray-50">
    <!-- 导航栏 -->
    {% include "components/navbar.html" %}

    <!-- 侧边栏（仅管理员） -->
    {% if current_user and current_user.role == 'admin' %}
        {% include "components/sidebar.html" %}
    {% endif %}

    <!-- 主内容区 -->
    <main class="container mx-auto px-4 py-8">
        <!-- Flash 消息 -->
        {% include "components/flash.html" %}

        <!-- 页面内容 -->
        {% block content %}{% endblock %}
    </main>

    <!-- 页脚 -->
    {% include "components/footer.html" %}

    <!-- 自定义脚本 -->
    <script src="/static/js/app.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### 6.2 导航栏组件

```html
<!-- src/web/templates/components/navbar.html -->
<nav class="bg-white shadow-md">
    <div class="container mx-auto px-4">
        <div class="flex justify-between items-center h-16">
            <!-- Logo -->
            <div class="flex items-center">
                <img src="/static/images/logo.png" alt="Logo" class="h-8 w-auto mr-3">
                <span class="text-xl font-bold text-gray-800">金融情报日报系统</span>
            </div>

            <!-- 导航链接 -->
            <div class="flex items-center space-x-6">
                <a href="/reports" class="text-gray-600 hover:text-blue-600">报告</a>
                <a href="/stats/wordcloud" class="text-gray-600 hover:text-blue-600">词云</a>
                <a href="/preferences" class="text-gray-600 hover:text-blue-600">偏好</a>

                {% if current_user and current_user.role == 'admin' %}
                    <a href="/admin/sources" class="text-gray-600 hover:text-blue-600">管理</a>
                {% endif %}

                <!-- 用户信息 -->
                {% if current_user %}
                    <div x-data="{ open: false }" class="relative">
                        <button @click="open = !open" class="flex items-center text-gray-700">
                            <span>{{ current_user.email }}</span>
                            <svg class="ml-2 h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                            </svg>
                        </button>

                        <div x-show="open" @click.away="open = false" class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1">
                            <form method="POST" action="/auth/logout">
                                <button type="submit" class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                    退出登录
                                </button>
                            </form>
                        </div>
                    </div>
                {% else %}
                    <a href="/login" class="text-blue-600 hover:text-blue-800">登录</a>
                {% endif %}
            </div>
        </div>
    </div>
</nav>
```

### 6.3 登录页面

```html
<!-- src/web/templates/auth/login.html -->
{% extends "base.html" %}

{% block title %}登录 - 金融情报日报系统{% endblock %}

{% block content %}
<div class="max-w-md mx-auto mt-16">
    <div class="bg-white rounded-lg shadow-md p-8">
        <h2 class="text-2xl font-bold text-center mb-6">登录</h2>

        {% if error %}
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                {{ error }}
            </div>
        {% endif %}

        <div x-data="{ step: 'email', email: '', otp: '', countdown: 0 }">
            <!-- 步骤 1: 输入邮箱 -->
            <div x-show="step === 'email'">
                <form @submit.prevent="requestOTP">
                    <div class="mb-4">
                        <label class="block text-gray-700 text-sm font-bold mb-2">
                            邮箱地址
                        </label>
                        <input
                            type="email"
                            x-model="email"
                            required
                            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="your.email@example.com"
                        >
                    </div>

                    <button
                        type="submit"
                        class="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        获取验证码
                    </button>
                </form>

                <!-- 管理员登录链接 -->
                <div class="mt-4 text-center">
                    <a href="#" @click.prevent="step = 'admin'" class="text-sm text-gray-600 hover:text-blue-600">
                        管理员登录
                    </a>
                </div>
            </div>

            <!-- 步骤 2: 输入 OTP -->
            <div x-show="step === 'otp'">
                <form @submit.prevent="verifyOTP">
                    <div class="mb-4">
                        <label class="block text-gray-700 text-sm font-bold mb-2">
                            验证码已发送至 <span x-text="email"></span>
                        </label>
                        <input
                            type="text"
                            x-model="otp"
                            required
                            maxlength="6"
                            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="请输入6位验证码"
                        >
                    </div>

                    <button
                        type="submit"
                        class="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        登录
                    </button>

                    <div class="mt-4 text-center">
                        <button
                            type="button"
                            @click="requestOTP"
                            :disabled="countdown > 0"
                            class="text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                        >
                            <span x-show="countdown > 0" x-text="countdown + '秒后重新发送'"></span>
                            <span x-show="countdown === 0">重新发送</span>
                        </button>
                    </div>
                </form>
            </div>

            <!-- 步骤 3: 管理员密码登录 -->
            <div x-show="step === 'admin'">
                <form method="POST" action="/auth/admin/login">
                    <div class="mb-4">
                        <label class="block text-gray-700 text-sm font-bold mb-2">
                            用户名
                        </label>
                        <input
                            type="text"
                            name="username"
                            value="admin"
                            readonly
                            class="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100"
                        >
                    </div>

                    <div class="mb-4">
                        <label class="block text-gray-700 text-sm font-bold mb-2">
                            密码
                        </label>
                        <input
                            type="password"
                            name="password"
                            required
                            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                    </div>

                    <button
                        type="submit"
                        class="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        登录
                    </button>

                    <div class="mt-4 text-center">
                        <a href="#" @click.prevent="step = 'email'" class="text-sm text-gray-600 hover:text-blue-600">
                            返回邮箱登录
                        </a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function requestOTP() {
    const email = this.email;

    fetch('/auth/otp/request', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ email })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            this.step = 'otp';
            this.countdown = 60;
            const timer = setInterval(() => {
                this.countdown--;
                if (this.countdown <= 0) clearInterval(timer);
            }, 1000);
        } else {
            alert(data.error);
        }
    });
}

function verifyOTP() {
    const email = this.email;
    const otp = this.otp;

    fetch('/auth/otp/verify', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ email, otp })
    })
    .then(res => {
        if (res.ok) {
            window.location.href = '/reports';
        } else {
            return res.json().then(data => {
                alert(data.error);
            });
        }
    });
}
</script>
{% endblock %}
```

### 6.4 报告列表页（示例）

由于篇幅限制，其他页面模板结构类似，均遵循以下原则：
- 使用 Tailwind CSS 样式
- HTMX 处理无刷新加载（分页、筛选）
- Alpine.js 处理简单交互（下拉菜单、模态框）
- 表单使用 POST 提交，支持 CSRF Token（如启用）

---

## 7. 安全与性能

### 7.1 安全措施

| 措施 | 实现方式 | 说明 |
|------|---------|------|
| JWT 认证 | HttpOnly Cookie | 防止 XSS 窃取 Token |
| OTP 验证 | Redis 存储 + 一次性消费 | 防止重放攻击 |
| 密码哈希 | bcrypt | 安全存储管理员密码 |
| HTML 净化 | bleach 白名单 | 防止 XSS 注入 |
| SQL 注入防护 | SQLAlchemy ORM | 参数化查询 |
| CORS 限制 | 生产环境配置 | 仅允许同源或指定域名 |
| 审计日志 | 记录所有管理操作 | 可追溯性 |
| IP 地址记录 | 审计日志中保存 | 安全分析 |

### 7.2 性能优化

| 优化点 | 方案 | 说明 |
|--------|------|------|
| 词云缓存 | Redis（24小时TTL） | 避免重复生成 |
| 数据库索引 | 关键字段建索引 | 加速查询 |
| 分页查询 | LIMIT + OFFSET | 减少内存占用 |
| 静态资源 CDN | Tailwind/HTMX/Alpine 使用 CDN | 加速加载 |
| Gzip 压缩 | FastAPI 中间件 | 减少传输体积 |

---

## 8. 测试策略

### 8.1 单元测试

**测试文件**：`tests/test_web/`

```python
# tests/test_web/test_security.py
def test_hash_password():
    """测试密码哈希"""
    from src.web.security import hash_password, verify_password

    password = "xtyydsf"
    hashed = hash_password(password)

    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)

def test_create_access_token():
    """测试 JWT 生成"""
    from src.web.security import create_access_token, decode_access_token

    token = create_access_token({"sub": "test@example.com"})
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "test@example.com"

# tests/test_web/test_auth.py
def test_generate_otp():
    """测试 OTP 生成"""
    from src.web.auth import generate_otp

    otp = generate_otp()

    assert len(otp) == 6
    assert otp.isdigit()

def test_otp_lifecycle(redis_client):
    """测试 OTP 完整生命周期"""
    from src.web.auth import store_otp, verify_otp

    email = "test@example.com"
    otp = "123456"

    # 存储
    store_otp(email, otp)

    # 验证成功
    assert verify_otp(email, otp) is True

    # 二次验证失败（已删除）
    assert verify_otp(email, otp) is False
```

### 8.2 集成测试

```python
# tests/test_web/test_routes.py
import pytest
from httpx import AsyncClient
from src.api.main import app

@pytest.mark.asyncio
async def test_login_flow():
    """测试登录流程"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 请求 OTP
        response = await client.post("/auth/otp/request", data={"email": "test@example.com"})
        assert response.status_code == 200

        # 2. 验证 OTP（需要 mock Redis）
        # ...

        # 3. 访问受保护页面
        response = await client.get("/reports")
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_admin_sources_page():
    """测试管理员信息源页面"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 登录为管理员
        # ...

        # 访问信息源管理页
        response = await client.get("/admin/sources")
        assert response.status_code == 200
        assert b"信息源管理" in response.content
```

### 8.3 E2E 测试（可选）

使用 Playwright 进行端到端测试：

```python
# tests/test_e2e/test_login.py
from playwright.sync_api import sync_playwright

def test_login_with_otp():
    """测试 OTP 登录流程"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # 访问登录页
        page.goto("http://localhost:8000/login")

        # 输入邮箱
        page.fill('input[type="email"]', 'test@example.com')
        page.click('button[type="submit"]')

        # 等待 OTP 输入框出现
        page.wait_for_selector('input[maxlength="6"]')

        # 输入 OTP（需要从测试邮箱或 Redis 获取）
        page.fill('input[maxlength="6"]', '123456')
        page.click('button[type="submit"]')

        # 验证跳转到报告页
        page.wait_for_url("http://localhost:8000/reports")

        browser.close()
```

---

## 9. 部署与运维

### 9.1 部署步骤

1. **安装依赖**

```bash
# 在 WSL 环境中
source .venv/bin/activate
poetry install
```

2. **数据库迁移**

```bash
alembic upgrade head
```

3. **初始化管理员账号**

```python
# scripts/init_admin.py
from src.db.session import get_db
from src.models.user import User, UserRole
from src.web.security import hash_password

db = next(get_db())

# 创建管理员
admin = User(
    email="xtyydsf@system.local",
    role=UserRole.ADMIN,
    hashed_password=hash_password("xtyydsf"),
    is_active=True
)
db.add(admin)
db.commit()
print("管理员账号已创建")
```

4. **启动 Web 服务**

```bash
# 开发环境
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000

# 生产环境
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 2
```

5. **启动 Celery Worker**（保持阶段一的任务调度）

```bash
celery -A src.tasks.celery_app worker --loglevel=info
celery -A src.tasks.celery_app beat --loglevel=info
```

### 9.2 健康检查

访问 `/healthz` 端点验证系统状态：

```bash
curl http://localhost:8000/healthz
```

---

## 10. 验收标准

### 10.1 功能验收

| 功能 | 验收标准 | 测试方法 |
|------|---------|---------|
| OTP 登录 | 用户可用白名单邮箱 + OTP 登录，7 天会话有效 | 手动测试 |
| 管理员登录 | 管理员可用 `xtyydsf/xtyydsf` 登录（邮箱亦可写成 `xtyydsf@system.local`） | 手动测试 |
| 报告浏览 | 用户可浏览报告列表和详情，附件可下载 | 手动测试 + E2E |
| 词云生成 | 词云（日/周/月）能生成并下载 PNG | 手动测试 |
| 用户偏好 | 用户可创建/保存 ≤5 个提示词模板 | 单元测试 + 手动测试 |
| 信息源管理 | 管理员能启停源、修改参数并立即生效 | 集成测试 + 手动测试 |
| 收件人管理 | 管理员能增删收件人/白名单 | 集成测试 + 手动测试 |
| 系统设置 | 管理员能修改参数（TopN、阈值等） | 集成测试 + 手动测试 |
| 操作审计 | 所有管理操作记录到 `admin_audit_log` | 单元测试 + 手动验证 |
| 系统状态 | `/admin/status` 页面展示健康状态和队列统计 | 手动测试 |
| HTML 净化 | 报告详情页无 XSS 风险 | 安全测试 |

### 10.2 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 页面加载时间 | < 2 秒（首屏） | 浏览器开发者工具 |
| 词云生成时间 | < 5 秒（无缓存） | 手动测试 |
| 登录响应时间 | < 1 秒（OTP 验证） | 手动测试 |
| 数据库查询 | < 100ms（90th percentile） | 慢查询日志 |

### 10.3 安全验收

| 检查项 | 验收标准 | 测试方法 |
|--------|---------|---------|
| JWT 安全 | Token 存储在 HttpOnly Cookie | 浏览器开发者工具 |
| OTP 安全 | OTP 一次性消费，10分钟过期 | 单元测试 + 手动测试 |
| 密码安全 | 管理员密码 bcrypt 哈希存储 | 数据库检查 |
| HTML 净化 | 报告详情页无可执行脚本 | 手动注入测试 |
| SQL 注入 | 所有查询参数化 | 代码审查 + 自动化扫描 |

---

## 附录：关键参数汇总

### A.1 环境变量

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `JWT_SECRET_KEY` | str | 无 | JWT 密钥（生产环境必须修改） |
| `JWT_ALGORITHM` | str | `HS256` | JWT 算法 |
| `JWT_EXPIRE_DAYS` | int | `7` | Token 有效期（天） |
| `OTP_TTL_SECONDS` | int | `600` | OTP 过期时间（秒） |
| `OTP_RESEND_INTERVAL` | int | `60` | OTP 重发间隔（秒） |
| `OTP_MAX_ATTEMPTS` | int | `5` | OTP 最大尝试次数 |
| `THEME_PRIMARY_COLOR` | str | `#1d4ed8` | 主题色 |
| `STOPWORDS_PATH` | str | `./config/stopwords_zh.txt` | 停用词文件路径 |
| `WORDCLOUD_CACHE_TTL` | int | `86400` | 词云缓存时间（秒） |

### A.2 数据库枚举

| 枚举类型 | 值 | 说明 |
|---------|---|------|
| `UserRole` | `admin`, `user` | 用户角色 |
| `PreferenceScope` | `daily`, `article` | 偏好范围 |
| `RuleType` | `source`, `keyword` | 规则类型 |
| `NoteScope` | `global`, `section` | 备注范围 |

### A.3 Redis 键命名

| 键模式 | TTL | 说明 |
|--------|-----|------|
| `otp:{email}` | 600s | OTP 验证码 |
| `otp_resend:{email}` | 60s | 重发间隔锁 |
| `otp_attempts:{email}` | 600s | OTP 尝试次数 |
| `wc:{scope}:{date}:{width}x{height}` | 86400s | 词云图片缓存 |

---

## 结语

本文档详细定义了金融情报日报系统第二阶段（前端管理台与可视化）的所有技术细节，包括：

1. **完整的数据模型**：8 张新表，所有字段和约束明确
2. **清晰的 API 接口**：50+ 个路由，参数、响应、业务逻辑全部定义
3. **安全的认证系统**：OTP + JWT + bcrypt，防止常见攻击
4. **可复用的模板设计**：Jinja2 + Tailwind + HTMX/Alpine
5. **全面的测试策略**：单元测试、集成测试、E2E 测试
6. **明确的验收标准**：功能、性能、安全三维度

开发团队可依据本文档进行实施，确保**一次生成，零 Bug，稳定可靠**。
