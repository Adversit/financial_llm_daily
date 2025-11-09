# 阶段二完成事项记录

1. **依赖与配置扩展**  
   - 在 `pyproject.toml` / `requirements.txt` 中加入 JWT、OTP、词云、前端交互所需的依赖（PyJWT、passlib[bcrypt]、email-validator、bleach、wordcloud、matplotlib、python-multipart、itsdangerous 等）。  
   - `.env.example` 与 `src/config/settings.py` 补全 JWT/OTP/主题色/停用词/缓存等配置项，确保前端安全与可视化功能可以通过环境变量控制。

2. **数据模型与迁移**  
   - 新建 `src/models/user.py`（User、UserPreference、WatchlistRule、BlocklistRule、ReportNote 等枚举与表）和 `src/models/system.py`（SystemSetting、AdminAuditLog）。  
   - 更新 `src/models/__init__.py` 与 `src/db/session.py` 以注册新模型。  
   - 编写 Alembic 迁移 `20251109_1200_b0c3d3c1d2a3_add_stage2_models.py`，创建所有阶段二新增表并预置管理员账号（`xtyydsf@system.local / xtyydsf`）及系统默认配置。

3. **Web 模块骨架**  
   - 创建 `src/web` 目录，包含 `app.py`、`security.py`、`auth.py`、`deps.py`、`routes/*`、`templates/*`、`static/*` 等。  
   - 实现 OTP 登录、JWT Cookie 会话、报告列表/详情、偏好模板 CRUD、统计占位、管理员页面占位及基础 Tailwind/HTMX/JS 支持。  
   - 使用 bleach 对报告 HTML 做安全净化，并提供前端异步请求 OTP 的脚本。

4. **安全与默认账号调整**  
   - 在 `src/web/security.py` 与迁移脚本中加入 bcrypt 72 字节裁剪逻辑，避免“password cannot be longer than 72 bytes”错误。  
   - 统一默认管理员账号/密码为 `xtyydsf`，并允许登录表单直接输入用户名（缺省域名自动补全 `@system.local`）。
