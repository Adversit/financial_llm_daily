# 金融情报日报系统 - 文档索引

**版本**: v1.1
**更新日期**: 2025-11-06

---

## 📚 文档目录

### 📋 需求与设计文档

| 文档 | 说明 | 状态 |
|------|------|------|
| **PRD.md** | 产品需求文档 | ✅ 完整 |
| **TDD-1.md** | 技术设计文档 (第一阶段) | ✅ 完整 |
| **task.md** | 任务清单与进度跟踪 | ✅ 已更新 |

### 🏗️ 架构文档

| 文档 | 格式 | 说明 | 推荐 |
|------|------|------|------|
| **architecture-phase1-updated.md** | Markdown | 系统分层架构说明 (已更新) | ⭐ 推荐 |
| **architecture-phase1.drawio** | DrawIO XML | 原始架构图 (可视化) | 参考 |
| **dataflow-phase1-updated.md** | Markdown | 数据流程与时间线 (已更新) | ⭐ 推荐 |
| **dataflow-phase1.drawio** | DrawIO XML | 原始数据流图 (可视化) | 参考 |
| **ARCHITECTURE_UPDATE.md** | Markdown | 架构更新说明与对比 | ⭐ 必读 |

### 📊 架构图查看方式

#### 方式 1: Markdown 文档 (推荐)

**优点**: 易于阅读、搜索、维护
**查看工具**: 任何 Markdown 阅读器、GitHub、VS Code

```bash
# 查看架构图
cat docs/architecture-phase1-updated.md

# 查看数据流图
cat docs/dataflow-phase1-updated.md
```

#### 方式 2: DrawIO 可视化图

**优点**: 可视化效果好、支持交互
**查看工具**: [diagrams.net](https://app.diagrams.net/) 或 VS Code 插件 `Draw.io Integration`

1. 访问 https://app.diagrams.net/
2. 选择 "Open Existing Diagram"
3. 上传 `architecture-phase1.drawio` 或 `dataflow-phase1.drawio`

---

## 🔍 文档使用指南

### 新手入门路径

1. **了解系统** → 阅读 `PRD.md`（产品需求）
2. **技术方案** → 阅读 `TDD-1.md`（技术设计）
3. **架构总览** → 阅读 `architecture-phase1-updated.md`（系统架构）
4. **数据流程** → 阅读 `dataflow-phase1-updated.md`（数据流）
5. **开发任务** → 阅读 `task.md`（任务清单）

### 开发人员路径

1. **架构理解** → `architecture-phase1-updated.md`
2. **数据流理解** → `dataflow-phase1-updated.md`
3. **代码对照** → 查看 `src/` 目录对应模块
4. **测试编写** → 参考 `tests/` 目录现有测试

### 维护人员路径

1. **架构变更** → 先阅读 `ARCHITECTURE_UPDATE.md` 了解变更历史
2. **更新文档** → 优先更新 Markdown 版本
3. **同步 DrawIO** → 可选，用于演示

---

## 📝 架构图更新说明

### 为什么有两个版本?

1. **DrawIO 版本** (`*.drawio`):
   - 原始设计稿
   - 可视化效果好
   - 但维护成本高（XML 格式复杂）

2. **Markdown 版本** (`*-updated.md`):
   - 与实际代码同步
   - 易于维护和搜索
   - 支持版本控制

### 更新时间

- **创建时间**: 2025-11-05 (DrawIO 版本)
- **更新时间**: 2025-11-06 (Markdown 版本)
- **更新原因**: 与实际代码实现同步

### 主要差异

详见 `ARCHITECTURE_UPDATE.md`，主要包括：

| 类型 | 说明 |
|------|------|
| ✅ **已实现** | Orchestrator、完整测试覆盖 |
| ⚠️ **未实现** | 动态采集器、队列监控、成本统计聚合 |
| ✅ **已同步** | 所有核心模块与实际代码一致 |

---

## 🎯 快速定位

### 我想了解...

**系统整体架构** → `architecture-phase1-updated.md`

**数据如何流转** → `dataflow-phase1-updated.md`

**哪些模块已完成** → `task.md` (项目进度概览)

**某个模块的实现** → 查看对应文件:
- 采集: `src/crawlers/`
- 抽取: `src/nlp/`
- 成稿: `src/composer/`
- 邮件: `src/mailer/`
- 任务: `src/tasks/`

**如何运行系统** → `../README.md` (项目根目录)

**测试怎么写** → `tests/` 目录

---

## 📖 文档约定

### 文件命名规范

- 设计文档: 大写 `PRD.md`, `TDD-1.md`
- 架构图: 小写 `architecture-*.md`, `dataflow-*.md`
- 更新版本: 后缀 `-updated.md`
- 原始图: 后缀 `.drawio`

### 更新规则

1. **代码变更时**: 同步更新 Markdown 架构图
2. **重大架构调整**: 记录到 `ARCHITECTURE_UPDATE.md`
3. **任务进度**: 实时更新 `task.md`
4. **需求变更**: 更新 `PRD.md` 并标注版本

---

## ✅ 文档状态

| 文档 | 状态 | 最后更新 |
|------|------|---------|
| PRD.md | ✅ 最新 | 2025-11-05 |
| TDD-1.md | ✅ 最新 | 2025-11-05 |
| task.md | ✅ 最� | 2025-11-06 |
| architecture-phase1.drawio | ⚠️ 参考 | 2025-11-05 |
| dataflow-phase1.drawio | ⚠️ 参考 | 2025-11-05 |
| architecture-phase1-updated.md | ✅ 最新 | 2025-11-06 |
| dataflow-phase1-updated.md | ✅ 最新 | 2025-11-06 |
| ARCHITECTURE_UPDATE.md | ✅ 最新 | 2025-11-06 |

---

## 🤝 贡献

### 发现文档问题

1. 检查文档是否为最新版本（查看更新日期）
2. 对照实际代码验证
3. 提交 Issue 或直接修改

### 更新文档

1. 修改对应的 Markdown 文件
2. 在 `ARCHITECTURE_UPDATE.md` 中记录变更
3. 更新本文档的"文档状态"表

---

**维护者**: 开发团队
**联系方式**: 见项目 README
**文档版本**: v1.1
