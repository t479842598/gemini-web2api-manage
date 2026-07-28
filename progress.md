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

## 2026-07-28 - Task: 重构项目结构 — 上游 submodule + manage 扩展包

### What was done

将上游 Sophomoresty/gemini-web2api 通过 git submodule 引入到 `_upstream/`，当前项目只保留增量价值（管理台扩展）。此前每次上游更新需要手动 diff 合并；重构后只需 `git submodule update --remote`。

- 创建 `gemini_web2api_manage/` 扩展包：`__init__.py`（_upstream path setup）、`config.py`（注入 manage 专用配置键）、`server.py`（继承上游 GeminiHandler 注入 admin 路由）、`__main__.py`（新入口）
- 将原 `admin.py` + `admin_static/` 从 `gemini_web2api/` 移入 `gemini_web2api_manage/`
- 备份并清除了 `gemini_web2api/` 中与上游重复的 8 个核心文件
- 引入上游 submodule 到 `_upstream/`
- 更新 `api/index.py`（Vercel 入口）、`pyproject.toml`、`manager.pyw` 以使用新入口

### Testing

- `python3 -m compileall gemini_web2api_manage/ api/index.py` — 全部通过
- 所有 7 个 Python 文件 `py_compile` 通过
- `.gitmodules` 正确配置；`git submodule status` 确认上游在 `9c3d2fe`

### Notes

**改动文件清单：**
- `gemini_web2api_manage/__init__.py` — 新建，扩展包入口，设 _upstream 到 sys.path
- `gemini_web2api_manage/config.py` — 新建，扩展上游配置，加入 manage 专用键
- `gemini_web2api_manage/server.py` — 新建，继承上游 GeminiHandler，注入 admin 路由
- `gemini_web2api_manage/__main__.py` — 新建，manage 版入口（python -m gemini_web2api_manage）
- `gemini_web2api_manage/admin.py` — 从 gemini_web2api/ 移入
- `gemini_web2api_manage/admin_static/` — 从 gemini_web2api/ 移入
- `api/index.py` — Vercel 入口改为从 gemini_web2api_manage 导入
- `pyproject.toml` — 包名改为 gemini-web2api-manage v2.0.0
- `manager.pyw` — 启动命令改为 -m gemini_web2api_manage
- `.gitmodules` — 新增上游 submodule 配置
- `_upstream/` — 新增：Sophomoresty/gemini-web2api git submodule
- `gemini_web2api/` — 清除了与上游重复的 8 个核心文件 + admin 文件

**回滚点：**
- `git reset --hard HEAD~1` 回退所有改动
- 核心模块备份在 `/tmp/gemini_web2api_core_backup_*`

## 2026-07-28 - Task: 前端管理台视觉重构和功能增强

### What was done

对 `web-admin/` 前端管理台进行 4 个 Phase 的改造，改善首屏视觉体验和交互能力。

**Phase 1: 概览页视觉重构**
- 健康状态 hero 卡片：全宽展示服务状态（绿色/红色渐变边框 + 大图标 + 版本/模型/IP 概要）
- 快捷操作栏：按钮直达对话、服务测试、复制 Base URL、日志、网络检测
- 调用地址列表：key 改为中文标签，新增"打开"按钮
- 运行环境卡片：每个环境项用独立卡片 + 图标 + 彩色状态文字
- 可用模型列表：点击模型直接跳转到服务测试页

**Phase 2: 导航和交互优化**
- 导航 badge：服务异常时显示红色圆点
- 顶栏新增"复制 URL"快捷按钮

**Phase 3: 对话页增强**
- localStorage 持久化：对话记录刷新不丢失
- System Prompt 输入框
- 导出 Markdown 按钮
- 复制按钮拆分为"复制 JSON"和"导出 MD"

**Phase 4: 其他页面微调**
- 日志页搜索/过滤
- 网络页连通性 status tag（连通/不可达 + 延迟 ms）

**构建优化**
- `web-admin/vite.config.js` 输出路径更新到 `gemini_web2api_manage/admin_static/`

### Testing

- `npm run build` 成功，产物输出到 `gemini_web2api_manage/admin_static/`
- 所有 Vue 组件模板变更编译通过
- Python compileall 通过

### Notes

**改动文件清单：**
- `web-admin/src/App.vue` — 概览页重写 + 导航 badge + 对话增强 + 日志搜索 + 网络指示器
- `web-admin/src/styles.css` — 新增 hero-card、quick-actions、env-grid、model-grid、nav-badge 样式
- `web-admin/vite.config.js` — 输出路径更新
- `gemini_web2api_manage/admin_static/` — 前端重新构建产物

**回滚点：**
- `cd web-admin && git checkout src/App.vue src/styles.css vite.config.js` 恢复前端源码
