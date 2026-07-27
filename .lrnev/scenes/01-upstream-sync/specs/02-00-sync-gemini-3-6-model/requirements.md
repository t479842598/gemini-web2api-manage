---
spec: '02-00-sync-gemini-3-6-model'
scene: '01-upstream-sync'
status: draft
priority: P1
created: '2026-07-27'
---

# 02-00 Sync Gemini 3 6 Model - 需求

## L0 摘要

同步原始项目的 Gemini 3.6 Flash 网页端模型映射、默认配置和管理端展示。

## L1 概览

### 目标

让管理版识别 `gemini-3.6-flash`，并与原始项目当前的 mode 1 路由和网页 build label 保持一致，同时保留 `gemini-3.5-flash` 兼容别名。

### 用户故事

- 作为 API 使用者，我希望模型列表和默认模型包含 Gemini 3.6 Flash，以便明确调用网页端当前最新的 Flash 路由。
- 作为现有客户端使用者，我希望旧的 Gemini 3.5 Flash 名称继续可用，以便升级后无需立即修改客户端配置。

### 范围

**包含**：
- Python 模型映射、默认模型和 Gemini 网页 build label。
- Web 管理台默认模型与构建产物。
- 配置示例、使用文档和变更记录。

**不包含**：
- 不接入 Google 官方 Gemini API，也不把官方 API 模型 ID 直接映射到网页内部 mode。
- 不修改流式网络处理、鉴权或并发逻辑。

## L2 详情

### 详细需求

#### F-01 Gemini 3.6 Flash 模型映射
- 描述：新增 `gemini-3.6-flash` 并映射到网页端 mode 1，保留 `gemini-3.5-flash` 为同一路由的兼容别名。
- 验收：WHEN 客户端请求 `gemini-3.6-flash` THEN 模型解析结果保持该名称且 mode 为 1，不再降级到 3.5。

#### F-02 默认配置同步
- 描述：默认模型更新为 `gemini-3.6-flash`，网页 build label 更新为原始项目当前值。
- 验收：WHEN 未指定模型或使用示例配置启动 THEN 默认选择 3.6，且请求 URL 使用同步后的 build label。

#### F-03 管理端与文档一致
- 描述：管理台默认值、构建产物、README、环境变量示例和扩展文档同步展示 3.6。
- 验收：WHEN 查看管理台模型列表或部署文档 THEN 3.6 为推荐默认项，3.5 明确标记为兼容别名。

### 非功能性需求

- 性能：不得新增运行时网络探测或启动阻塞。
- 兼容性：保留现有 3.5、Thinking、Pro、Auto 和 Lite 模型名及 mode 映射。

### 边界与依赖

依据原始项目 `Sophomoresty/gemini-web2api` 的 `d227668`、`fbd5dde` 和 `9c3d2fe`；网页内部 mode 与 Google 官方 Gemini API 模型目录不是同一契约。

### 验收标准

最初失败信号：当前 `resolve_model("gemini-3.6-flash")` 会静默返回 `gemini-3.5-flash`，配置仍使用 2026-05 的 build label。

- [ ] `gemini-3.6-flash` 出现在兼容模型列表并解析为 mode 1。
- [ ] 默认模型和 build label 与原始项目当前值一致。
- [ ] 管理台构建和 Python 静态验证通过。
- [ ] 文档说明官方 API 模型目录不能直接驱动网页内部模型路由。
