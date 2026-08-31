# Gemini Cookie Push（浏览器扩展）

一键读取 Gemini 登录 Cookie（**含 HttpOnly**）并直接推送到
[gemini-web2api-manage](../../README.md)，或复制到剪贴板手动粘贴。

## 为什么需要扩展

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

## 使用

### 路径 A：一键推送（推荐）

1. 在服务端启用推送令牌（见下）
2. 在已登录 `https://gemini.google.com/app` 的浏览器里打开扩展
3. 展开「服务器设置」，填服务地址与令牌 → 点 **保存并授权该域名**
4. 点 **一键推送到服务器**

成功后无需重启服务，下一个请求即用新 Cookie。

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
| `host_permissions: *.google.com` | 上述读取的作用域 |
| `optional_host_permissions` | 运行时只对你填写的那一个服务地址申请权限，不在安装时索要全站权限 |
