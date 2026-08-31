# 更新日志

## v3.3.1 (2026-08-31)

### 修复

- **修复扩展读不到 `SAPISID` / `SID`，导致推送一直提示“会话不完整”**。用户实测反馈：「检查会话」只读到 8 条 cookie、`SAPISID` 与会话 Cookie 全部缺失，但 `SNlM0e` 能取到（说明浏览器确实已登录）—— 即问题在扩展读取逻辑而不是登录态。两个叠加原因：
  1. **主因：`manifest.json` 的 `host_permissions` 只声明了 `www` / `gemini` / `accounts` 等子域，都不覆盖 `.google.com` 主域。** 官方文档明确 `getAll()`「仅检索扩展程序具有主机权限的网域的 Cookie」，而 `SAPISID`/`SID`/`HSID` 全设在 `.google.com` 上，于是被权限模型直接过滤。已补上 `https://google.com/*` 与 `https://*.google.com/*`。
  2. **次因：分区 cookie（CHIPS）。** 官方文档：「默认情况下，所有 API 方法都针对未分区的 Cookie 运行」，`__Secure-*PSID*` 这类可能被标为 Partitioned 的项必须带 `partitionKey` 再查一轮（Chrome 119+）。

  根因已用**建模了 Chrome 权限过滤与分区语义的反向对照实验**逐项确认：v1.0 只剩子域项（复现用户现象）→ 只修权限则 `SAPISID`/`SID` 回来但仍缺 `__Secure-1PSID` → 只修查询依旧全缺（证明权限是主因）→ 两者都改后关键项齐全。

### 变更

- **cookie 查询改为多路合并**：三个子域 `url` 查询 + `{domain: "google.com"}` 域查询，各自再叠加带/不带 `partitionKey` 的变体；老版本 Chrome 不认识 `partitionKey` / `hasCrossSiteAncestor` 时逐个试错降级，不整体失败。同名去重时**未分区那份优先**（服务端发的是第一方请求，不该误用 iframe 场景的值）。
- **「检查会话」新增诊断输出**：列出实际读到的 cookie 名与「原始 N 条 / 去重后 M 条」，下次再出问题能直接定位。
- **新增「会话不完整时也强制推送」逃生阀**，避免关键字段缺失时完全卡住。

### 升级注意

改了 `host_permissions`，必须在 `chrome://extensions` 点扩展卡片上的 **重新加载（↻）** 才会生效，只刷新 Gemini 页面不够。

### 验证

扩展逻辑 **12/12**（mock 已建模权限过滤与分区语义）、解析 **13/13**、推送端到端 **21/21**、协议回归 **17/17**，共 63 项断言全通过。

## v3.3.0 (2026-08-31)

### 新增

- **一键获取并送达 Gemini Cookie**：解决“关键鉴权 cookie 全是 HttpOnly、控制台脚本拿不到、Chrome Application 面板只能一条条看”的老问题。新增自带扩展 `tools/gemini-cookie-sync/`，用 `chrome.cookies.getAll()` 读取**含 HttpOnly** 的完整 cookie（`SAPISID` / `__Secure-1PSID` / `SNlM0e` 这些 `document.cookie` 根拿不到的都在），点一下直接推送到服务端并**立即生效（无需重启）**。扩展同时提供「复制到剪贴板」兼容手动粘贴。
- **推送端点 `POST /admin/api/cookie-push`**：走独立推送令牌（`X-Cookie-Push-Token`），**默认关闭** —— `cookie_push_token` 为空时返回 404 且与“该端点不存在”不可区分，不会在公网凭空多一个写入口。令牌用 `hmac.compare_digest` 常量时间比较，按来源 IP 滑窗限流（5 分钟内 8 次失败 → 429），长度不足 16 字符的令牌直接拒绝。不用管理台会话 Cookie 鉴权，是因为扩展是 `chrome-extension://` 源，跳域携带凭据会被浏览器 CORS 禁止。
- **宽容粘贴解析（服务端，React 前端零改动即受益）**：管理台 Cookie 输入框现在自动识别并归一四种输入 —— 裸 `k=v; k=v`、DevTools「Copy as cURL」（bash 与 Windows cmd 两种续行风格）、扩展导出的 `gemini-auth.json`、`Cookie:` 头或整块请求头。落盘只保存归一后的纯 cookie 串。
- **推送/粘贴时一并应用随带字段**：来源若携带 `auth_user` / `xsrf_token` / `gemini_bl`，一次动作全部生效，不再需要手工改四个配置键。
- **Cookie 写入可回滚**：任一环节失败则恢复 CONFIG 原值并删除已写的 cookie 文件，一坑坏推送不会把可用配置搞坏。

### 变更

- **不再需要上游的 `gemini-auth.json` 手工链路**：旧流程（扩展导出文件 → `cp` 到项目 → `jq` 改 `config.json` 四个键 → 重启）在服务跑在远程机器时基本走不通；现在一次推送完成。上游扩展与 submodule 保持原样不动，本层在主仓库自带一份。
- **扩展权限最小化**：服务端地址用 `optional_host_permissions` + 运行时 `chrome.permissions.request` 只对用户填写的那一个源申请，不在安装时索要全站权限。

### 安全

- Cookie 串等同 Google 账号登录态：接口响应与服务端日志**只记录条数与关键字段存在性，绝不回显明文**；cookie 文件写入后 `chmod 600`；`config.json` 落盘前保留 `.pre-push.bak`。
- 怀疑泄露时：服务端改掉 `cookie_push_token` 即可作废。

### 验证

- `cookie_ingest` 解析测试 **13/13 PASS**（含真实形态的 cURL bash/cmd、整块请求头、带 `=` 的 COMPASS 值、同名去重、垃圾输入不崩）；额外修正一处真 bug：`detect_format` 的 header 判定漏了 `re.I`，导致 `Cookie:` 大写开头时整块输入落到 raw 分支、把 `charset=UTF-8` 当成 cookie 名。
- 推送端点端到端测试 **21/21 PASS**：401/429/404 关闭态、裸串与 JSON 与 cURL 三种推送、随带字段应用、`gemini_bl` 更新、落盘内容与 600 权限、重启后持久、弱令牌拒绝、管理台粘贴归一。
- 扩展逻辑测试 **11/11 PASS**：在 Node 中注入 mock 的 `chrome.*` 与最小 DOM、执行 `popup.js` 真实源码，`fetch` 打到真实本地服务端 —— 验证能读出 HttpOnly、丢弃非 Google 域项、推送成功、令牌错误时提示清晰。
  - 诚实说明：未能在自动化浏览器里真实加载扩展。Chrome 152 稳定版已禁用 `--load-extension`（自 v135 起非企业策略不允许），已用最小 manifest + ASCII 路径对比确认是环境限制而非扩展缺陷。用户侧真实 Chrome 加载路径未自动化验证。

## v3.2.0 (2026-08-31)

### 新增

- **响应透出官网实际服务的模型**：新增从 Gemini 响应 `inner[42]` 解析真实服务模型，`/v1/chat/completions`、`/v1/responses`、Google `generateContent` 及流式 chunk 均会把 `model` 写为**实际服务模型**，并新增 `requested_model` / `served_model` 保留用户请求的模型名。此前响应把用户请求的模型名原样回显，而实测匿名请求无论要哪个档位都返回 `3.5 Flash-Lite`，等于对用户谎报模型。可用 `expose_served_model: false` 关闭（管理台配置页可改，无需重启）。
- **透出会话 ID 与出口地区**：新增解析响应 `inner[1]`（`c_`/`r_` 会话与响应 ID）与 `inner[5]`/`inner[8]`（官网看到的出口 IP 归属地），响应中新增 `gemini_conversation_id`、`gemini_response_id`、`gemini_region`、`gemini_region_code`；`/admin/api/status` 新增 `last_generation` 块，便于排查区域限流与“模型没生效”。
- **`GET /health` 无鉴权探活端点**：返回 `status`/`version`/`models`/`gemini_bl`/`cookie_configured`/`streaming`/`proxy` 等。此前只有 `/`（302 跳 /admin），部署探活拿不到健康状态。
- **`bl` 版本号后台定期刷新**：新增守护线程按 `bl_refresh_sec`（默认 21600 秒）周期跟随官网版本号。实测官网 `bl` 几天一发且**按会话 A/B 分片下发**（连续两次加载分别得到 `20260827.05_p0` 与 `20260830.05_p0`），仅启动时取一次会越漂越远。刷新失败保留旧值且不抛出到请求路径。
- **浏览器画像可配置**：新增 `browser_profile` 配置项（可覆盖任意画像字段）与 `gemini_hl`（语言标记，不再硬编码 `en`）。

### 变更

- **请求头对齐真实 Chrome 152/153 抓包**：以 headless Chrome + CDP 拦截官网原始请求为基准，补齐 `Accept: */*`、`Content-Type` 的 `charset=UTF-8`、完整 Chrome UA（原为被截断的 `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36`，缺 `KHTML, like Gecko` 与版本号）、11 个 `sec-ch-ua-*` Client Hints、4 个 `x-goog-ext-*` 扩展头；`x-goog-ext-525005358-jspb` 与 payload `inner[59]` 使用同一个 UUID（与官网行为一致）。画像集中在 `protocol.BROWSER_PROFILE` 单一常量块，默认固定当前最新稳定版 **153.0.8010.12**（已实测 Google 正常接受）。
- **URL 参数补齐**：新增 `f.sid`（19 位带符号会话 ID，进程启动时生成一次）；`_reqid` 从 `int(time.time())%1000000` 改为随机起点 + 进程内递增的 7 位数。
- **payload 与官网对齐**：内层数组长度 102 → 97；`inner[6]` `[0]`→`[1]`、`inner[68]` `1`→`2`、补 `inner[91]=0`、`inner[96]=0`；语言字段与 `hl` 同源。
- **非流式路径统一到 httpx**：`generate()` 原本走 urllib 且带代理时每次重建 opener（无连接复用），现改为复用与流式相同的 httpx 共享客户端，保留 405→刷 BL 与 `BardErrorInfo` 瞬时错误重试语义；httpx 不可用时自动回落 urllib。
- **模型目录描述诚实化**：`/v1/models` 各模型描述不再暗示匿名可用高级模型，明确标注“匿名实测被服务端封顶为 3.5 Flash-Lite”与 Cookie 依赖；并写明 `gemini-3.7-flash` 与 `gemini-3.6-flash` 的 mode/think 完全相同、属别名而非独立模型。模型键名全部保留，不影响已有调用方。

### 修复

- **修复服务启动阻塞 30 秒**：CPython 的 `HTTPServer.server_bind()` 会调 `socket.getfqdn("0.0.0.0")` 取服务名，而这是一次必然超时的反向 DNS（实测本机耗时正好 30.0 秒），表现为“启动后 30 秒内端口不监听、探活全部失败”。现由 manage 层 `ThreadedServer` 跳过该查询，启动从 30s+ 降至 4s。
- **修复 `_reqid` 同秒碰撞**：原 `int(time.time())%1000000` 在 `ThreadedServer` 多线程并发下同一秒内的请求必然重号；现 200 次取样全唯一，并发 8 路实测元数据不串味。
- **修复 token 用量把非空回答算成 0**：原 `len(text)//4` 使单字符回答的 `completion_tokens` 为 0（生产实测复现：回答 `"9"` → `completion_tokens: 0`）。现改为向上取整且非空至少 1，空回答仍为 0，`total` 自洽。
- **修复 `gemini_base_url` 对生成请求完全无效**：该配置项在管理台配置页与网络检测中都被读取，但请求 URL 构造器把域名硬编码为 `https://gemini.google.com`，导致“私有反代域名”只影响诊断、不影响实际生成。现已真正接入 URL 构造，`Origin`/`Referer` 同步跟随实际域名。
- **本地 `config.json` 失效代理**：`proxy` 指向已无监听的 `127.0.0.1:7890`（实测 curl 返回 000，而直连 200），会导致本地起服务全部超时；已改为直连并在 `config.example.json` 补齐本次新增配置键。

### 已知限制

- **匿名模式无法选择模型**：实测 mode 取 1/2/3/4/5/6 与 think 取 0/4 时，响应 `inner[42]` 一律回报 `3.5 Flash-Lite`；注入真实浏览器抓到的 `inner[3]`（1.6KB protobuf token）与 `inner[4]`（32hex）**也不改变路由**。要真实路由需 Cookie，**待验证**。
- **负结果记录（避免重复逆向）**：payload `inner[3]` 大 token 由前端 `_.xK.serialize` 生成，已验证注入无收益，本层故意不生成该字段。
- **token 用量仍为估算**：已实测确认官网响应不提供真实 token 计数，本次只修正为不为 0 且自洽，未引入分词器依赖。
- **管理台前端未展示新字段**：`last_generation`、真实模型分布等已可从 `/admin/api/status` 与 `/admin/api/stats` 读到，React 页面展示属 `03-web-console-revamp` 范围，本次未改前端。
- **Cookie 路径未验证**：真实模型路由、`at` 是否强制、多模态附件均需带 Cookie 实测（`xsrf_token` 目前被写入 POST body 而非 query，与官网形态是否一致待测）。

## v3.1.1 (2026-08-21)

### Bug 修复

- **修复匿名模式长对话无法回复**：Gemini 匿名请求会随机返回 `BardErrorInfo [1060]`（实测约 20% 概率、与 prompt 长度无关），而旧错误帧正则 `BardErrorInfo\s*\[\d+\]` 无法匹配真实格式 `BardErrorInfo",[1060]]`，导致错误被静默吞成空响应、且不触发重试；长对话（多轮/Agent 工具循环连续多次请求）几乎必撞一次，表现为「匿名长对话无法正常回复」。现已修正检测并自动重试瞬时错误 1060
- **匿名模式错误透明化**：`BardErrorInfo` 按错误码区分处理——1060（瞬时）自动重试；1003（匿名不支持附件/图片）、1097（匿名不支持会话续接）快速失败并返回带中文提示的明确报错，不再静默返回空内容
- **流式重试安全**：流式路径仅在尚未输出任何内容时才重试，避免重复输出

### 已知限制

- 匿名模式无法发送图片/附件（Gemini 硬限制 `BardErrorInfo [1003]`，图片上传链路本身可用、但模型侧拒绝匿名附件绑定），需配置 Cookie；匿名会话续接（cid/rid/rcid）同样被硬拒（1097），历史以单条消息合并发送

## v3.1.0 (2026-08-20)

### 对话页增强

- **文件上传**：对话页可上传文件到服务器（`data_dir/uploads/`，10MB 限），新增 `/admin/api/files` 上传/列表/读取/删除接口（防路径穿越）
- **读取服务器本地文件**：服务器文件面板列出已上传文件，点击将内容作为上下文加入对话
- **Agent 工具循环**：对话页 Agent 开关，自动执行工具调用循环（get_weather / calc / get_time / read_file），支持多轮直至完成
- **图片上传/粘贴**：输入框支持粘贴或选择图片，以 OpenAI image_url 格式发送

### 发布与部署

- 统一 Python 包、前端包和 npm lockfile 版本为 `3.1.0`。
- 重写中英文 README，补充架构、技术栈、管理 API、systemd、Nginx、Docker、Compose 和 Vercel 部署说明。
- 增加生产管理台登录页与概览页截图，记录真实服务器验证结果。
- 新增 Linux x86_64 PyInstaller 二进制构建流程、systemd 服务文件、SHA-256 校验文件和 GitHub Actions tag 发布流程；正式生产发布以二进制 + systemd 为主。
- 修正可选源码 Docker 入口使用管理版服务，并通过 `/data` 数据卷持久化配置、Cookie、统计和上传文件。
- 补齐 Vercel 环境变量适配，包括 `GEMINI_COOKIE`、`API_KEYS`、`PROXY`、`ADMIN_PASSWORD` 和运行参数。

### 已知限制

- 图片识别：Gemini 返回 `BardErrorInfo [1003]`（上游 file binding 仍为 WIP），图片发送链路已通但模型暂无法识别图片内容

## v3.0.0 (2026-08-20)

### 前端迁移

- **前端技术栈迁移到 React 19 + TypeScript + Vite + Tailwind 4 + shadcn**：与 freebuff2api 完全一致，样式逐页对齐（porcelain-moss / tungsten-dark 亮暗主题 + 跟随系统）
- 页面全部重写：登录 / 概览（含请求统计卡片、模型用量、Key 用量）/ 对话（含导出 MD/JSON、localStorage 持久化）/ 网络检测 / 服务测试 / 配置（Cookie + API Key 管理）/ 运行日志
- 后端新增 SPA fallback：`/admin/*` 非 API 路径返回 index.html，支持客户端路由
- 删除 Vue 遗留代码（naive-ui 单文件架构）

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
