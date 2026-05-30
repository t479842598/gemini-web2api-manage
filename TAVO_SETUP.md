# Tavo / 酒馆接入说明

## 启动服务

推荐双击运行：

```text
manager.pyw
```

管理器可以启动、关闭、重启服务，显示运行状态、端口、Base URL 和日志，不会额外显示终端窗口。

## Tavo 配置

- 接入类型：`Custom` / `OpenAI Protocol`
- Base URL：
  - Tavo 和本服务在同一台电脑：`http://127.0.0.1:8881/v1`
  - Tavo 在手机或另一台设备：`http://电脑局域网IP:8881/v1`
- API Key：可随便填，例如 `none`
- Model：`gemini-3.5-flash-thinking`

注意：Base URL 只填到 `/v1`，不要填 `/v1/chat/completions`。

## 如果连接失败

1. 先在管理器里确认状态是“运行中”。
2. 确认端口和 Tavo 里填的一致。
3. 手机端不要用 `localhost` 或 `127.0.0.1`，要用电脑的局域网 IP。
4. 如果开启 Windows 防火墙拦截，需要允许 Python 监听该端口。
