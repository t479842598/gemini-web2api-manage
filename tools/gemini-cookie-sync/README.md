# Gemini Cookie Push（浏览器扩展）

一键读取 Gemini 登录 Cookie（**含 HttpOnly**）并直接推送到
[gemini-web2api-manage](../../README.md)，或复制到剪贴板手动粘贴。

当前版本 **v1.1**：修正了 `.google.com` 主域权限声明缺失，导致
`SAPISID` / `SID` 完全读不到的问题（详见文末「v1.1 修了什么」）。

## 为什么不装扩展就根本拿不全

本项目鉴权最关键的几个 cookie 全是 **HttpOnly**：

| Cookie | 用途 | `document.cookie` 能读到吗 |
|---|---|---|
| `SAPISID` | 计算 `Authorization: SAPISIDHASH`，登录态鉴权核心 | ❌ 读不到 |
| `__Secure-1PSID` / `__Secure-3PSID` / `SID` | Google 会话标识 | ❌ 读不到 |
| `SNlM0e` | XSRF token | ❌ 读不到（在 `WIZ_global_data` 里） |

所以在网页控制台里跑脚本、或者从 Chrome「Application → Cookies」面板一条条手工拼
`k=v; k=v`，都拿不全也容易错。`chrome.cookies.getAll()` 是浏览器内唯一能拿到完整
集合的正规 API —— 这就是本扩展存在的理由。

## 安装（一次性）

1. 打开 `chrome://extensions`
2. 右上角开启 **开发者模式**
3. 点 **加载已解压的扩展程序**
4. 选择本目录（`tools/gemini-cookie-sync`）

> Chrome 135 起稳定版不再支持用 `--load-extension` 命令行参数加载扩展，
> 必须走上面这个界面，这是 Chrome 的安全策略。
>
> **从 v1.0 升级**：因为改了 `host_permissions`，必须在 `chrome://extensions`
> 点本扩展卡片上的 **重新加载**（↻）图标，改权限才会生效。只刷新 Gemini 页面不够。

## 使用

### 路径 A：一键推送（推荐）

1. 在服务端启用推送令牌（见下）
2. 在已登录 `https://gemini.google.com/app` 的浏览器里打开扩展
3. 展开「服务器设置」，填服务地址与令牌 → 点 **保存并授权该域名**
4. 点 **一键推送到服务器**

成功后无需重启服务，下一个请求即用新 Cookie。

「检查会话」面板会列出**实际读到的 cookie 名**，出问题时直接看那行就知道缺了什么。

### 路径 B：不装扩展（零配置）

1. 打开 `https://gemini.google.com/app` 并确保已登录
2. F12 → **Network** → 任选一条发往 `gemini.google.com` 的请求
3. 右键 → **Copy** → **Copy as cURL**
4. 打开管理台「配置 → Cookie」，把整段 cURL **原样粘进输入框** → 保存配置

服务端会自动识别并归一，支持这四种输入格式：

- 裸串：`SID=...; SAPISID=...`
- DevTools 的 Copy as cURL（bash 与 Windows cmd 两种续行风格都支持）
- 本扩展导出的 `gemini-auth.json` 内容
- `Cookie: ...` 请求头或整块请求头

若粘贴的是 JSON，随带的 `auth_user` / `xsrf_token` / `gemini_bl` 也会一并应用。

## 服务端启用推送令牌

令牌为空时 `/admin/api/cookie-push` **完全关闭**，返回 404 且与"该端点不存在"
不可区分 —— 不会在公网上凭空多一个写入口。

启用方式（任选其一）：

```bash
# 1) 环境变量
COOKIE_PUSH_TOKEN="$(openssl rand -hex 24)"

# 2) 管理台 API（需先登录）
curl -X POST https://<你的域名>/admin/api/config \
  -H 'Content-Type: application/json' -b "gw_admin=<会话cookie>" \
  -d '{"cookie_push_token":"<至少 16 字符的随机串>"}'
```

令牌少于 16 字符会被拒绝（400）。改回空串即关闭功能；改令牌即刻作废旧令牌。

## 安全须知

- **Cookie 串等同你的 Google 账号登录态。** 不要分享、不要截图、不要提交到 Git。
- 扩展只在本地读取 cookie，只向你**在设置里显式填写**的那个地址推送。
- 服务端响应与日志只记录 cookie 条数与关键字段存在性，**绝不回显 cookie 明文**。
- 推送端点按来源 IP 对失败尝试限流（5 分钟内 8 次失败即 429），令牌用常量时间比较。
- 生产环境请只通过 **HTTPS** 使用推送功能。
- 怀疑泄露时：在服务端把 `cookie_push_token` 改掉即可作废；必要时到
  Google 账号安全页登出全部会话。

## 扩展用到的权限

| 权限 | 用途 |
|---|---|
| `cookies` | 读取 Google 域 cookie（含 HttpOnly） |
| `tabs` + `scripting` | 在 Gemini 页面读取 `SNlM0e` / `cfb2h` / 账号序号 |
| `storage` | 本地保存服务地址与令牌 |
| `clipboardWrite` | 复制到剪贴板 |
| `host_permissions: https://*.google.com/*` | **必须含主域通配**，否则 `.google.com` 上的 `SAPISID`/`SID` 会被权限模型过滤掉 |
| `optional_host_permissions` | 运行时只对你填写的那一个服务地址申请权限，不在安装时索要全站权限 |

## v1.1 修了什么

两个叠加原因导致关键 cookie 读不到，已用**建模了 Chrome 权限与分区语义的反向对照
实验**逐项确认：

1. **主因：`host_permissions` 少了 `.google.com` 主域。** 官方文档明确 `getAll()`
   「仅检索扩展程序具有主机权限的网域的 Cookie」。`SAPISID`/`SID`/`HSID` 都设在
   `.google.com` 这个域上，而 v1.0 只声明了 `https://www.google.com/*`、
   `https://gemini.google.com/*` 这类子域，**都不覆盖 `.google.com`**，于是这些项
   被权限模型直接过滤掉。现补上 `https://google.com/*` 与 `https://*.google.com/*`。
2. **次因：分区 cookie（CHIPS）。** 官方文档：「默认情况下，所有 API 方法都针对
   未分区的 Cookie 运行」。`__Secure-*PSID*` 这类可能被标为 Partitioned 的项，
   必须带 `partitionKey` 再查一轮才拿得到（Chrome 119+）。

对照实验结果：

| 场景 | 读到的关键项 |
|---|---|
| v1.0（旧权限 + 旧查询） | 只剩子域项，`SAPISID`/`SID`/`__Secure-1PSID` **全缺** |
| 只修权限 | `SAPISID`/`SID` 回来，仍缺 `__Secure-1PSID` |
| 只修查询 | 依旧全缺（证明权限才是主因） |
| v1.1（两者都改） | **全部齐全** |

另外新增：查询改为多路合并（三个子域 `url` 查询 + `{domain: "google.com"}` 域查询 ×
带/不带 `partitionKey` 变体），未分区那份优先（服务端发的是第一方请求）；
「检查会话」列出实际读到的 cookie 名；加了「会话不完整时也强制推送」逃生阀。
