---
spec: '01-00-sync-original-updates'
scene: '01-upstream-sync'
created: '2026-06-10'
---

# 01-00 Sync Original Updates - 任务清单

> 任务由 lrnev `task_create` 工具创建，不要手编。
> 状态机：pending → in_progress → completed / failed；blocked 可回 in_progress；failed 可回 pending 重试。

## 阶段 1

通过 lrnev 任务跟踪本次上游同步的对比、合并和验证步骤。

## 验收标准（整体）

- [x] 所有任务完成
- [x] 上游差异已评估
- [x] 同步后核心源码无语法错误

### T-001 对比原始项目差异 <!-- lrnev-task: status=completed, created=2026-06-10T10:14:36.491Z, updated=2026-06-10T10:30:10.949Z, validates=F-01 -->
<!-- lrnev-task-history: [{"from":"pending","to":"in_progress","at":"2026-06-10T10:15:29.983Z"},{"from":"in_progress","to":"completed","at":"2026-06-10T10:30:10.949Z","reason":"差异已识别：上游新增 auth_user/xsrf_token、Scotty 多模态上传、工具图片处理降级、BardErrorInfo 错误提示；管理版后台为本地保留范围。"}] -->

识别 gemini-web2api-oran/gemini-web2api-main 与当前项目的文件和核心源码差异。

**验收**：
- 能列出需要同步的核心文件。
- 能识别当前管理版需要保留的定制文件。

### T-002 合并上游功能更新 <!-- lrnev-task: status=completed, created=2026-06-10T10:14:47.099Z, updated=2026-06-10T10:30:43.706Z, depends_on=T-001, validates=F-02 -->
<!-- lrnev-task-history: [{"from":"pending","to":"in_progress","at":"2026-06-10T10:30:25.728Z","reason":"开始合并上游核心行为更新"},{"from":"in_progress","to":"completed","at":"2026-06-10T10:30:43.706Z","reason":"已合并上游 auth_user/xsrf_token 请求支持、Scotty 多模态上传、工具图片处理策略和 BardErrorInfo 错误提示；管理后台配置透出新增字段并重建静态资源。"}] -->

将已确认的上游功能与修复合并到当前项目，保留管理版增强。

**验收**：
- 上游核心更新已同步到当前项目。
- 管理后台和日志增强未被全量覆盖。

**依赖**：T-001

### T-003 验证同步结果 <!-- lrnev-task: status=completed, created=2026-06-10T10:14:57.128Z, updated=2026-06-10T10:31:11.711Z, depends_on=T-002, validates=F-03 -->
<!-- lrnev-task-history: [{"from":"pending","to":"in_progress","at":"2026-06-10T10:30:55.245Z","reason":"开始验证同步结果"},{"from":"in_progress","to":"completed","at":"2026-06-10T10:31:11.711Z","reason":"验证通过：npm run build 成功；python -m compileall gemini_web2api gemini_web2api.py manager.pyw 成功。"}] -->

执行可用的 Python 语法或导入级验证，确认没有同步引入的基础错误。

**验收**：
- 核心 Python 文件通过语法编译检查。
- 记录验证命令和结果。

**依赖**：T-002
