# 更新日志

## v2.2.0 (2026-08-20)

### 功能

- **新增请求统计**：每次 /v1 生成调用自动记录（端点 / 模型 / 脱敏 Key / 成败 / 耗时 / Token 用量），落盘 `data_dir/requests.jsonl`（10MB 限容），重启不丢失
- **新增管理接口** `GET /admin/api/stats?range=1d|3d|7d|30d|all`：返回总请求 / 成功 / 失败 / 成功率 / Token 消耗 / 平均耗时，以及按模型、按 API Key、按端点的用量聚合与时间趋势
- **XSRF（at token）自动获取**：Google StreamGenerate 现在强制要求 `at` 参数，服务会自动从 400 响应提取新 token 缓存并重试，无需手动配置 `xsrf_token`
- **SOCKS5 代理支持**：配置页可填 `socks5://` 代理，服务自动启动本地 HTTP 桥接（pysocks 隧道），上游零改动；原始 socks5 地址在管理台正常显示
- 统计记录受 `log_requests` 配置控制；API Key 仅存脱敏前缀，不落盘完整密钥

### 已知限制

- 图片上传（多模态）：上游 fork 的 file binding 仍为 WIP，Gemini 返回 `BardErrorInfo [1003]`，待上游修复或深度逆向（详见测试记录）

## v2.1.2 (2026-08-20)

### Bug 修复

- **修复导入 Cookie 后刷新/重启即丢失**：配置与 Cookie 文件统一写入稳定数据目录（`GEMINI_WEB2API_DATA_DIR` > 项目根），启动时改为优先从该目录加载配置，systemd / Docker 等 cwd 与数据目录分离的部署不再丢配置
- **Cookie 保存协议升级为全量快照（`cookie_items`）**：编辑已有 Cookie 复用原文件、新增自动接续编号不覆盖、删除真正生效
- 配置写入前自动生成 `config.json.bak` 备份
- 前端：导入 Cookie 后提示「点击保存配置后生效」，保存成功回显已落盘 Cookie 数量

## v2.1.1 (2026-08-16)

### 上游同步（upstream/main 2bb988b）

- **新增 `gemini-3.7-flash` 模型**：上游新增最新模型并调整 3.6 描述
- **OpenAI 多模态输入支持**：`image_url` / base64 / data URL 图片输入 + SSRF 防护 + MIME 自动识别（`detect_image_mime`）
- **chunked request body 支持**：兼容 `Transfer-Encoding: chunked` 的客户端请求
- **模块化包流式同步**：上游官方将 streaming 修复（role:assistant 首 chunk、Responses 完整事件序列）同步到模块化目录，与本地 fork 已移植功能对齐
- **BL 自动更新保留**：合并后保留 fork 独有的 `gemini_bl` 自动更新 + 405 重试
- 上游模块化同步测试（`tests/test_modular_sync.py`，18 项）全部通过

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
