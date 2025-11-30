# 🚀 快速开始 - 金融情报日报系统

## 一键启动

```bash
# 在 WSL 中执行
cd /mnt/d/work/project/Fin_daily_report/V4
source .venv/bin/activate
./scripts/start_all.sh
```

## 访问系统

- 🌐 **Web管理台**: http://localhost:8000
- 🔐 **管理员登录**: `xtyydsf` / `xtyydsf`
- 📧 **普通用户**: 白名单邮箱 + OTP验证码

## 主要功能

| 功能 | URL | 说明 |
|------|-----|------|
| 登录 | /login | OTP或密码登录 |
| 报告列表 | /reports | 查看所有日报 |
| 报告详情 | /reports/{date} | 查看指定日期报告 |
| 词云 | /stats/wordcloud | 生成词云图片 |
| 用户偏好 | /preferences | 管理提示词模板 |
| 信息源管理 | /admin/sources | 管理采集源 |
| 收件人管理 | /admin/recipients | 管理收件人 |

## 停止服务

```bash
./scripts/stop_all.sh
```

## 查看日志

```bash
# Web服务日志
tail -f logs/web.log

# Celery日志
tail -f logs/celery_worker.log
```

## 常见问题

### 数据库连接失败
```bash
sudo service postgresql start
```

### Redis连接失败
```bash
sudo service redis-server start
```

### 端口被占用
```bash
# 查找进程
sudo lsof -i :8000

# 杀死进程
sudo kill -9 <PID>
```

## 详细文档

📚 完整文档请查看: `docs/STARTUP_GUIDE.md`

---

**版本**: v2.0 | **更新**: 2025-11-09
