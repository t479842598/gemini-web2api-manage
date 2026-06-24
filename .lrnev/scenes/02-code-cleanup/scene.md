---
id: '02-code-cleanup'
number: 2
name: 'code-cleanup'
status: active
created: '2026-06-24'
intent: '全面优化 gemini-web2api 代码质量、安全性和部署可靠性'
---

# Code Cleanup

## L0 摘要

对 gemini-web2api 进行全面代码质量优化：统一 Cookie 环境变量管理、修复依赖声明、消除重复代码、修正线程安全问题、改进 Dockerfile 和 .gitignore，确保项目可安全部署到 Vercel 和本地环境。

## L1 概览

### 业务背景

上游同步完成后，项目存在多处代码质量问题：配置重复字段、敏感凭据明文存储、依赖声明不一致、httpx 全局单例线程不安全、根目录与模块包代码重复、Dockerfile 端口不对齐等。需要系统性清理。

### 边界与范围

**包含**：
- Cookie 凭据迁移到 .env 环境变量管理
- pyproject.toml 依赖声明修复
- httpx.Client 线程安全修复
- config.json 重复字段清理
- Dockerfile 端口和文件对齐
- .gitignore 安全性增强
- server.py 代码去重
- 根目录冗余文件清理
- 文档更新

**不包含**：
- 不引入速率限制
- 不迁移到异步框架
- 不引入 tiktoken（token 计数保持估算）
- 不构建 web-admin 管理后台
- 不添加单元测试（后续单独场景）

### 关键术语

| 术语 | 定义 |
|------|------|
| .env | 本地环境变量文件，存储 GEMINI_COOKIE 等敏感配置 |
| Vercel env | Vercel 部署平台的环境变量系统 |
| Scotty upload | Google Gemini 的可恢复文件上传协议 |

### 相关 Scene

- 01-upstream-sync（已完成）

## 维护说明

- 本文档由 AI 主导编写
- 修改后应同步更新 `.abstract.md` / `.overview.md`
