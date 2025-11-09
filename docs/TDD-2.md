# 金融情报日报系统 · 技术设计文档（TDD · 第二阶段｜前端与可视化）

**版本**：v2.0  
**日期**：2025-11-05（Asia/Shanghai）  
**范围**：基于阶段一（MVP）后端与数据面，新增登录与权限、管理台、报告浏览与下载、词云与基础统计、用户定制化提示词、部门内功能，均采用 **FastAPI + Jinja2 SSR + 少量 HTMX/Alpine**。  
**不含**：容器化（第三阶段）、RAG/DeepSearch 逻辑实现（仅预留入口），接口限流/CSRF（按 PRD 暂不启用）。

---

## 1. 架构与依赖

### 1.1 组件

- **Web（FastAPI）**：同步渲染页面，REST/JSON 仅供前端异步小交互。
  
- **模板**：Jinja2 + Tailwind（本地构建产物或 CDN），HTMX/Alpine 处理微交互（表格分页/开关）。
  
- **鉴权**：邮箱白名单 + 邮箱验证码（OTP）；角色 `admin/user`；**JWT 存 HttpOnly Cookie**。
  
- **可视化**：词云 PNG 服务端渲染（`wordcloud` + `jieba`），统计图使用简单 HTML 表/进度条（不引入前端大图表库）。
  
- **安全**：生产环境同源部署；暂不启用 CSRF/限流（预留开关）。
  

### 1.2 新增依赖（在阶段一基础上）

`jinja2==3.*         # (阶段一已含) itsdangerous==2.*   # 签名辅助（可选） pyjwt[crypto]==2.*  # JWT passlib[bcrypt]==1.*# 仅管理员密码变更时用（保留） email-validator==2.*# 邮箱校验 wordcloud==1.*      # 词云 jieba==0.42.*       # 中文分词 bleach==6.*         # 报告HTML展示时安全净化`

### 1.3 目录增量（相对阶段一）

`src/web/   __init__.py   app.py                 # FastAPI 装配   deps.py                # 依赖与安全   auth.py                # 登录/OTP/JWT   views/                 # 页面路由     home.py     reports.py     admin.py     settings.py     assets.py            # 词云/下载   templates/     base.html     auth_login.html     reports_list.html     report_detail.html     admin_sources.html     admin_recipients.html     admin_whitelist.html     admin_settings.html     admin_audit.html     admin_status.html     _partials/*.html     # 片段   static/                # 主题资源/Logo`

---

## 2. 数据模型与迁移（第二阶段）

> 在 **F 章（阶段一）数据结构不变**基础上，增加 4 张轻量表；通过 Alembic 创建增量迁移。

### 2.1 新增表

1. **`user_preferences`**（用户偏好/定制模板）
   

`id, user_email, name, scope{daily,article}, prompt_text, is_default, created_at, updated_at 约束：每用户最多 5 条；(user_email, name) 唯一`

2. **`watchlist_rules`**（关注来源/关键词，置顶）
   

`id, type{source,keyword}, pattern, created_by, is_enabled, created_at, updated_at`

3. **`blocklist_rules`**（禁止词/来源黑名单，供过滤与视图隐藏）
   

`id, type{source,keyword}, pattern, created_by, is_enabled, created_at, updated_at`

4. **`report_notes`**（运营备注，附加到当日报告顶部或区块）
   

`id, report_date, scope{global,section}, section_key(nullable), author_email, content_md, created_at`

> 注：OTP 不落库，存 **Redis** 短期 Key（`otp:{email}`，TTL 10 分钟），避免修改 `users` 表结构。

---

## 3. 鉴权与会话（Auth）

### 3.1 白名单与 OTP

- **请求验证码**：POST `/auth/otp/request`
  
    - 入参：`email`；校验其存在于 `report_recipients(type='whitelist', enabled=true)`
      
    - 生成 6 位数字 OTP，存 Redis `otp:{email}`，TTL 10 分钟；使用阶段一 `mailing.smtp_client` 发送简易文本邮件（主题：登录验证码）。
    
- **提交验证码**：POST `/auth/otp/verify`
  
    - 校验 Redis 中 OTP，一次性消费；发放 **JWT**（7 天，HttpOnly, SameSite=Lax）。
      
    - 首次登录的 `user` 自动在 `users` 表落档（便于审计）。
      

### 3.2 管理员账号

- 固定 `xtyydsf / xtyydsf`（邮箱可写成 `xtyydsf@system.local`）；支持在“系统设置”中修改（写 `system_settings`，加 bcrypt 存储）。
  

### 3.3 中间件/依赖

- `get_current_user()`：从 HttpOnly Cookie 解 JWT；加载 `role`。
  
- `require_role('admin')`：装饰器保护管理端路由。
  

---

## 4. 页面与 API 设计

### 4.1 登录

- GET `/login` → `auth_login.html`
  
- POST `/auth/otp/request` → 200（通用提示“若邮箱在白名单将收到验证码”）；频率：每邮箱 60s 间隔（Redis 锁）
  
- POST `/auth/otp/verify` → Set-Cookie(JWT) + 302 到 `/`
  

### 4.2 首页 / 报告浏览

- GET `/` → 重定向 `/reports`
  
- GET `/reports?date=YYYY-MM-DD&page=1&q=...&region=...&layer=...`
  
    - 列表：日期、摘要片段、区块统计、下载入口
    
- GET `/reports/{date}` → 展示“**邮件正文 HTML**”（净化后嵌入）
  
    - 页内操作：
      
        - 下载附件：链接到 `/assets/attachment/{date}.html`（由 DB 中 `html_attachment` 即时生成）
          
        - 展开“全部事实与观点”（分页 HTMX，服务端渲染简表）
    
- GET `/assets/attachment/{date}.html` → `Content-Disposition: attachment`
  

> **安全**：使用 `bleach` 白名单净化 `html_body`（保留 a/p/ul/ol/li/h1-h4/table 基本标签）。

### 4.3 词云与统计

- GET `/stats/wordcloud?scope=day|week|month&date=YYYY-MM-DD`
  
    - 服务器端生成 PNG（`wordcloud + jieba`），来源 `extraction_items.fact/opinion`（中文文本）
      
    - 停用词：内置 + 自定义（`system_settings.stopwords`）
    
- GET `/stats/summary?date=YYYY-MM-DD`
  
    - 返回 JSON（或渲染表）：条目数、region/layer 分布、Provider 成本与平均处理时延（如阶段一未统计成本，仅显示条数）
      

### 4.4 用户定制化提示词

- GET `/preferences`：列出当前用户的模板（≤5）
  
- POST `/preferences`：创建/更新（`scope=daily|article`，文本长度上限 2k）
  
- 删除：POST `/preferences/{id}/delete`
  
- 生效机制：写入 `system_settings` 的“当日全局临时值”（`daily_prompt_overrides[date][email]`），供阶段一流水线在次日读取（阶段二仅写入；流水线读取在后续迭代挂接）。
  

### 4.5 管理台（admin）

- **信息源管理**：GET `/admin/sources`（表格：启停/并发/超时/解析器切换；HTMX 行内保存）
  
- **收件人与白名单**：
  
    - GET `/admin/recipients`（`type=recipient`）
      
    - GET `/admin/whitelist`（`type=whitelist`）
      
    - 新增/删除/启用禁用：POST 表单
    
- **系统设置**：GET/POST `/admin/settings`
  
    - 参数：TopN、阈值、分块、并发、预算、主题色、停用词等；写 `system_settings`
    
- **操作审计**：GET `/admin/audit`（最近 500 条）
  
- **系统状态**：GET `/admin/status`
  
    - 展示：队列水位、近 24h 任务数/失败率、Provider 可用性、/healthz 心跳
    
- **部门内功能**：
  
    - `/admin/watchlist`：添加来源/关键词 → 次日报告置顶区
      
    - `/admin/blocklist`：屏蔽来源/关键词（仅影响展示层）
      
    - `/admin/notes`：为某日报添加备注（顶部或某分区），存 `report_notes`
      

---

## 5. 主题与 UI 规范

- **布局**：全局导航（报告/统计/偏好；admin 看到管理菜单）；内容卡片；分页 20 条/页。
  
- **主题**：浅/深双色切换；品牌主色可在 `system_settings.theme_color` 调整（Tailwind 变量）。
  
- **可达性**：语义化 HTML；链接均有标题；日期/过滤器使用原生控件。
  

---

## 6. 安全设计

- **JWT**：RS256 或 HS256（存 `.env` 的密钥），Cookie 标记 `HttpOnly; SameSite=Lax; Secure(生产开启)`。
  
- **输入校验**：所有表单使用 Pydantic 校验；邮箱通过 `email-validator`。
  
- **HTML 展示**：`bleach` 白名单净化 DB 中的 `html_body`。
  
- **OTP**：Redis 短存（10 分钟），请求频率 60s/邮箱；错误次数 5 次/10 分钟内锁定（Redis 计数）。
  
- **审计**：所有管理员写操作记录到 `admin_audit_log`（who/what/before/after）。
  

---

## 7. 配置项（增量）

`JWT_SECRET=   # 或 JWT_PRIVATE_KEY / JWT_PUBLIC_KEY (RS256) OTP_TTL_SECONDS=600 OTP_RESEND_INTERVAL=60 THEME_PRIMARY_COLOR=#1d4ed8   # 默认蓝 STOPWORDS_PATH=./config/stopwords_zh.txt`

---

## 8. 测试计划（第二阶段）

### 8.1 单元测试

- Auth：白名单判定、OTP 生成/校验/过期、JWT 编解码
  
- Views：参数校验、分页正确性、权限保护（403/302）
  
- 词云：中文分词与停用词效果（快照尺寸/非空像素比）
  

### 8.2 集成测试

- 以 `httpx.AsyncClient` 对页面路由跑登录→浏览→下载全流程
  
- 报告展示：将阶段一产出的 `reports` 样例入库，验证净化后可渲染且链接可用
  
- 管理操作：sources 启停/收件人/白名单/设置变更 → 落库与审计日志
  

### 8.3 E2E（可选）

- 使用 Playwright（测试）对关键页面做 smoke：登录、列表筛选、下载、admin 改参数
  

### 8.4 验收标准（第二阶段 Done）

1. 用户可用白名单邮箱 + OTP 登录；7 天会话有效
   
2. 报告列表/详情可浏览，附件 HTML 可下载，页面渲染无脚本告警
   
3. 管理员能完成：启停源、维护收件人/白名单、修改参数并立即生效
   
4. 词云（日/周/月）能生成并下载 PNG
   
5. 用户可创建/保存 ≤5 个提示词模板
   
6. 审计与系统状态页可用；/healthz 绿灯
   

---

## 9. 交互与数据契约（关键 API 摘要）

- `POST /auth/otp/request`  
    **Req**：`{ email }` → **200**
    
- `POST /auth/otp/verify`  
    **Req**：`{ email, otp }` → **302 + Set-Cookie(JWT)`**
    
- `GET /reports`  
    **Query**：`date, page, q, region, layer` → **200(HTML)**
    
- `GET /reports/{date}` → **200(HTML)**
  
- `GET /assets/attachment/{date}.html` → **200(attachment)**
  
- `GET /stats/wordcloud?scope&date` → **200(image/png)**
  
- `POST /preferences` → **302**
  
- 管理端若干 `GET/POST` 表单路由（HTMX 支持）
  

---

## 10. 实施顺序（模块完成即测）

1. **Auth 子系统（白名单 + OTP + JWT）** → 单元/集成通过
   
2. **报告浏览与下载**（净化 + 详情 + 附件导出）→ 用阶段一样例入库验证
   
3. **管理员：收件人与白名单** → 增删改/审计
   
4. **管理员：信息源启停与参数设置** → 即时生效校验
   
5. **词云与统计** → PNG 输出/下载
   
6. **用户偏好与模板** → 创建/限制 ≤5/生效标记
   
7. **部门内功能**（关注/屏蔽/备注）→ 列表置顶与展示层过滤
   
8. **系统状态页** → 队列/Provider 心跳联通
   

---

## 11. 风险与回退

- 报告 HTML 净化可能去除必要样式 → 采用最小白名单并允许 `<table>` 基础样式；异常时提供“原样式查看”开关（仅 admin）。
  
- OTP 邮件延迟 → 提供“重新发送”按钮（间隔 ≥60s）。
  
- 2C/2G 下词云大文本生成慢 → 缓存 PNG（Redis，key：`wc:{scope}:{date}`，TTL 24h）。

- 
