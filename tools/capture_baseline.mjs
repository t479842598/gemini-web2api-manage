#!/usr/bin/env node
/**
 * 抓一份 Gemini 官网真实 StreamGenerate 基线，供 tools/align_check.py 做离线比对。
 *
 * 前置：一个开着 CDP 的 headless Chrome，且能访问 gemini.google.com
 *   cd ~/.pi/agent/skills/web-browser/scripts && ./start.js --headless
 *   （国内网络需给 Chrome 挂代理，见 skill 的 BROWSER_BIN 用法）
 *
 * 用法：
 *   node tools/capture_baseline.mjs [输出路径]   # 默认 /tmp/gemini_baseline.json
 *
 * 抓到的内容：URL（含全部 query）、请求头、POST body、响应体。
 * 顺带把响应体里 inner[42]（真实服务模型）、inner[1]（会话 ID）解出来存一份，
 * 便于和我们的实现对照。
 */
import { connect } from "/Users/qingtang/.pi/agent/skills/web-browser/scripts/cdp.js";
import { writeFileSync } from "node:fs";

const OUT = process.argv[2] || "/tmp/gemini_baseline.json";
const PROMPT = process.argv[3] || "1+1等于几？只回答数字。";

const cdp = await connect(8000);
const pages = await cdp.getPages();
const page = pages.find((p) => p.url.includes("gemini.google.com")) || pages[0];
if (!page) {
  console.error("找不到 gemini.google.com 页面，先 nav.js 打开它");
  process.exit(1);
}
const sid = await cdp.attachToPage(page.targetId);

const extraHeaders = new Map();
let req = null;
let respBody = null;

cdp.on("Network.requestWillBeSentExtraInfo", (p, s) => {
  if (s === sid) extraHeaders.set(p.requestId, p.headers);
});
cdp.on("Network.requestWillBeSent", (p, s) => {
  if (s === sid && p.request.url.includes("StreamGenerate")) {
    req = { requestId: p.requestId, url: p.request.url, method: p.request.method,
            headers: p.request.headers, postData: p.request.postData };
  }
});
cdp.on("Network.loadingFinished", async (p, s) => {
  if (s !== sid || !req || p.requestId !== req.requestId) return;
  try {
    const r = await cdp.send("Network.getResponseBody", { requestId: p.requestId }, sid, 20000);
    respBody = r.base64Encoded ? Buffer.from(r.body, "base64").toString("utf8") : r.body;
  } catch (e) {
    console.error("getResponseBody failed:", e.message);
  }
});

await cdp.send("Network.enable", {}, sid);
await cdp.evaluate(sid, `(() => { const e=document.querySelector("[contenteditable=true].ql-editor"); if(e) e.focus(); return !!e; })()`);
await new Promise((r) => setTimeout(r, 500));
await cdp.send("Input.insertText", { text: PROMPT }, sid);
await new Promise((r) => setTimeout(r, 800));
for (const type of ["keyDown", "keyUp"]) {
  await cdp.send("Input.dispatchKeyEvent", {
    type, key: "Enter", code: "Enter",
    windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13,
  }, sid);
}
await new Promise((r) => setTimeout(r, 14000));

if (!req) {
  console.error("没抓到 StreamGenerate —— 页面可能没登录/被拦，或输入框选择器变了");
  process.exit(1);
}
req.headers = { ...req.headers, ...(extraHeaders.get(req.requestId) || {}) };

// 从响应里解出官网自报的元数据，作为“官网到底怎么回的”的证据
let meta = null;
if (respBody) {
  for (const line of respBody.split("\n")) {
    const t = line.trim();
    if (!t.startsWith('[["wrb.fr"')) continue;
    try {
      const inner = JSON.parse(JSON.parse(t)[0][2]);
      if (Array.isArray(inner) && inner.length > 42) {
        meta = { ids: inner[1], served_model: inner[42], region: inner[5]?.[0], region_code: inner[8] };
        break;
      }
    } catch { /* 非文本帧，跳过 */ }
  }
}

writeFileSync(OUT, JSON.stringify({ captured_at: new Date().toISOString(),
  page_url: page.url, request: req, response_body: respBody, response_meta: meta }, null, 2));
console.log(`✓ baseline → ${OUT}`);
console.log(`  url      : ${req.url.slice(0, 140)}`);
console.log(`  served   : ${meta?.served_model ?? "-"}`);
console.log(`  headers  : ${Object.keys(req.headers).length}`);
console.log(`  body     : ${(req.postData || "").length} chars`);
cdp.ws.close();
process.exit(0);
