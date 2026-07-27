# Progress Log

## 2026-07-27 - Task: 完全同步上游 gemini-web2api 能力并增强管理台

### What was done

**Phase 1: 核心能力对齐**
- `models.py`：新增 `gemini-3.6-flash`（mode=1, think=4）放首位，`gemini-3.5-flash` 改为兼容别名，`resolve_model` 默认值改为 `gemini-3.6-flash`
- `config.py`：`default_model` 更新为 `gemini-3.6-flash`，`gemini_bl` 更新为 `boq_assistant-bard-web-server_20260716.08_p0`
- `gemini.py`：`clean_text()` 增加 `strip` 参数（默认 True），`generate_stream()` 改用 `emitted_raw_text` 基线逻辑替代 `prev_text` 长度差，增加 `resp.raise_for_status()` 和内容变化检测
- `server.py`：`_authorized()` 扩展支持 `x-goog-api-key` 和 `?key=` 查询参数鉴权，GET/POST 路由前缀从 `/v1/` 改为 `/v1` 覆盖 `/v1beta`，`log_message` 输出客户端 IP
- `server.py`：让 `force_non_stream` 真正覆盖 Chat Completions、Responses 和 Gemini CLI 流式入口，避免管理台开关只展示不生效
- `config.example.json`：同步更新 `default_model` 和 `gemini_bl`
- `.env.example`：`DEFAULT_MODEL` 更新为 `gemini-3.6-flash`

**Phase 2: 管理台增强**
- `admin.py`：`admin_config_payload()` 新增 `gemini_bl` 字段透传，`save_config()` 的 allowed 集合新增 `gemini_bl`
- `web-admin/src/App.vue`：
  - 概览页运行环境新增：Gemini BL、流式模式、CLI 兼容状态、鉴权模式
  - 配置页新增：Gemini BL 输入框、强制非流式开关
  - 默认模型引用统一更新为 `gemini-3.6-flash`
- `README.md` / `README_CN.md` / `README_EN.md`：补充 3.6 模型、3.5 兼容别名、默认值和 `/v1beta` 鉴权说明
- 前端重新构建，输出到 `gemini_web2api/admin_static/`

### Testing

- Python 语法编译验证：全部 5 个核心文件通过
- 模型解析验证：`gemini-3.6-flash`、`gemini-3.5-flash`、`gemini-auto`、unknown fallback 均正确
- `clean_text(strip=True/False)` 行为验证通过
- `_authorized()` 鉴权方法：Bearer / x-api-key / x-goog-api-key / ?key= 全部覆盖
- 路由前缀 `/v1` 覆盖 `/v1beta` 验证通过
- HTTP 回归验证通过：`/v1`、`/v1beta` 鉴权矩阵、3.6 模型列表和 `force_non_stream` 响应行为
- `admin_config_payload` 返回 gemini_bl、force_non_stream、default_model 验证通过
- `save_config` allowed 集合包含 gemini_bl 验证通过
- `config.example.json` 与默认值一致性验证通过
- 前端 npm build 成功

### Notes

**改动文件清单：**
- `gemini_web2api/models.py` — 新增 gemini-3.6-flash，更新默认值
- `gemini_web2api/config.py` — 更新 gemini_bl 和 default_model 默认值
- `gemini_web2api/gemini.py` — clean_text 增加 strip 参数，generate_stream 改用 emitted_raw_text 基线
- `gemini_web2api/server.py` — 鉴权扩展、路由前缀统一、日志加客户端 IP
- `gemini_web2api/admin.py` — admin_config_payload 透传 gemini_bl，save_config 允许 gemini_bl
- `web-admin/src/App.vue` — 概览诊断、配置表单、默认模型引用
- `config.example.json` — 同步默认值
- `.env.example` — 同步 DEFAULT_MODEL
- `README.md` / `README_CN.md` / `README_EN.md` — 更新模型、默认配置和鉴权文档
- `gemini_web2api/admin_static/` — 前端重新构建

**回滚点：**
- Phase 1 回滚：`git checkout HEAD -- gemini_web2api/models.py gemini_web2api/config.py gemini_web2api/gemini.py gemini_web2api/server.py config.example.json .env.example`
- Phase 2 回滚：`git checkout HEAD -- gemini_web2api/admin.py web-admin/src/App.vue && cd web-admin && npx vite build`

## 2026-07-27 - Task: 部署最新版本到 VPS

### What was done

- 备份服务器原项目到 `/root/gemini-web2api-backups/20260727_234847`，包含项目归档、`config.json` 和原工作树差异补丁。
- 将 `/opt/gemini-web2api-manage` 更新到 GitHub 提交 `4186a9e`，保留 `.venv`、运行配置和日志目录。
- 将运行配置的 `default_model` 更新为 `gemini-3.6-flash`，`gemini_bl` 更新为 `boq_assistant-bard-web-server_20260716.08_p0`。
- 重启并确认 `gemini-web2api.service` 正常运行，Nginx 公网域名为 `geminiapi.274747.xyz`。

### Testing

- systemd 状态：`active (running)`。
- 本机 `GET /v1/models`、`GET /v1beta/models`：HTTP 200，均包含 `gemini-3.6-flash`。
- 本机 `/admin`：HTTP 200，管理台静态资源可用。
- 公网 `https://geminiapi.274747.xyz/`：HTTP 302；`/v1/models` 和 `/v1beta/models`：HTTP 200。

### Notes

**改动文件清单：**
- `progress.md` — 追加 VPS 备份、部署和验证记录。

**回滚点：**
- 停止服务后使用 `/root/gemini-web2api-backups/20260727_234847/project.tar.gz` 恢复项目，并用同目录 `config.json` 恢复运行配置；恢复后执行 `systemctl restart gemini-web2api.service`。
