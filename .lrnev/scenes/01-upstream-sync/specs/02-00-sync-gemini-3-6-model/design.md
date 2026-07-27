---
spec: '02-00-sync-gemini-3-6-model'
scene: '01-upstream-sync'
created: '2026-07-27'
---

# 02-00 Sync Gemini 3 6 Model - 设计

## L0 摘要

在现有静态模型映射内同步上游 3.6 别名、默认值和 build label，不引入动态模型发现。

## L1 概览

### 架构思路

沿用项目当前的网页端 mode 映射架构。`gemini-3.6-flash` 和旧的 `gemini-3.5-flash` 都映射到 mode 1；模型列表继续只暴露本代理确认可路由的网页模型，不混入 Google 官方 API 的完整目录。

### 主要模块

- `gemini_web2api/models.py`：模型名到 mode/think 的映射。
- `gemini_web2api/config.py`、`config.example.json`、`.env.example`：默认模型和 build label。
- `web-admin/src/App.vue`、`gemini_web2api/admin_static/`：管理端默认项和发布产物。
- `README*.md`、`docs/`：使用与维护说明。

### 关键决策

本轮是既有映射数据同步，不改变协议或架构，不单独生成 ADR。

## L2 详情

### 模块详细设计

<!-- 设计锚点规范：用 `#### D-xx 标题` 标注设计点（与 requirements 的 F-xx 对称），供 task 的 validates 引用；lrnev 只校验“D-xx 在不在”，不判断设计好坏。 -->

#### D-01 同 mode 兼容别名

在 `MODELS` 首位增加 `gemini-3.6-flash`，mode 为 1、think 为 4；保留 `gemini-3.5-flash` 并把说明改成 3.6 的兼容别名。`resolve_model` 的内部兜底默认值同步为 3.6。

#### D-02 配置和管理端一致性

默认配置、示例配置、环境变量示例和管理端初始值统一改为 3.6；build label 更新为 `boq_assistant-bard-web-server_20260716.08_p0`。重建 Vue 静态资源，确保 Python 服务实际托管的页面同步。

#### D-03 文档边界

文档注明 `/v1beta/models` 是本代理的兼容模型列表，并非对 Google `models.list` 的透传；官方目录可动态获取，但其模型 ID 不能直接作为网页 `StreamGenerate` 的 mode 值。

### 数据模型

不新增持久化数据结构，只扩展现有 `MODELS` 字典条目。

### 接口契约

`GET /v1/models`、`GET /v1beta/models` 和管理台状态接口新增 `gemini-3.6-flash`；旧模型名继续返回并可调用。

### 错误处理

保持现有未知模型降级行为不变；本轮只确保 3.6 不再被当作未知模型。

### 测试策略

执行模型解析断言、请求 URL build label 断言、Python `compileall`、管理端 `npm run build`，并启动本地服务检查两个模型列表端点。
