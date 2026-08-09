# 更新日志

## v2.1.0 (2026-08-09)

### Bug 修复

- **修复管理台登录 500**：`send_json` 不支持 `headers` 参数导致登录/登出接口抛 `TypeError`（返回 500 且无法设置 Cookie），现已在 `GeminiHandler` 中覆盖 `send_json` 支持可选 `headers`

### 上游同步（f92a31c）

- **gemini_bl 自动更新**：启动时自动抓取最新 BL，请求遇 405 时自动更新并重试（流式回退非流式），无需再手动改配置
- **`temporary_chats` 配置项**：控制临时对话标志，管理台新增开关
- **Chat 流式兼容**：首 chunk 补 `role:"assistant"`，适配严格 OpenAI SDK
- **Responses API 流式**：补全完整事件序列（created/in_progress/output_item/content_part/delta/done/completed），修复 Codex CLI 兼容

### 前端

- **默认暗色主题**：进入管理台默认暗色，顶栏可切换 暗色（默认）/ 跟随系统 / 亮色，选择持久化
- **主题防闪**：首帧前应用主题，避免亮色闪烁

## v2.0.0 (2026-07-28)

### 项目结构重构

- **上游 submodule 接入**：将上游 `Sophomoresty/gemini-web2api` 通过 git submodule 引入到 `_upstream/`，后续只需 `git submodule update --remote` 即可同步，不再需要手动 diff 合并
- **扩展包 `gemini_web2api_manage/`**：新建扩展包，继承上游 `GeminiHandler` 并注入管理台路由（`/admin`, `/admin/api/*`）
- **入口变更**：启动命令从 `python -m gemini_web2api` 改为 `python -m gemini_web2api_manage`
- **包名更新**：`pyproject.toml` 包名改为 `gemini-web2api-manage` v2.0.0

### 前端管理台视觉重构

- **概览页 hero 卡片**：全宽健康状态卡片（绿色/红色渐变边框 + 大图标 + 版本/模型/IP 概要），替代原来的 3 个 metric 卡片
- **快捷操作栏**：新增一排按钮直达对话、服务测试、复制 Base URL、日志、网络检测
- **调用地址列表**：URL 名称改为中文标签（`current` → 当前地址 等），每行新增"打开"按钮
- **运行环境卡片**：替换 NStatistic 列表，每个环境项用独立卡片 + 图标 + 彩色状态文字
- **可用模型列表**：新增全宽面板展示所有模型名和描述，点击直接跳转到服务测试页

### 前端功能增强

- **导航 badge**：服务异常时概览项显示红色圆点
- **顶栏快捷操作**：新增"复制 URL"按钮
- **对话持久化**：对话记录、模型、流式模式、System Prompt 通过 localStorage 保存，刷新不丢失
- **System Prompt**：对话页新增输入框，作为 system 消息发送到 API
- **导出 Markdown**：对话页新增导出按钮，一键复制为 Markdown 格式
- **日志搜索**：日志页新增关键词过滤输入框，实时过滤日志行
- **网络连通性指示器**：Gemini/Google 连通性面板新增 status tag（连通/不可达 + 延迟 ms）

### 构建优化

- **vite 输出路径**：从 `gemini_web2api/admin_static/` 更新为 `gemini_web2api_manage/admin_static/`
