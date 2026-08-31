/**
 * Gemini Cookie Push —— 一键读取含 HttpOnly 的完整登录 Cookie 并推送到
 * gemini-web2api-manage。
 *
 * 为什么必须走扩展：本项目鉴权最关键的 SAPISID / __Secure-1PSID / SNlM0e
 * 全是 HttpOnly，控制台里的 document.cookie 根本读不到，所以"网页端自动提取"
 * 这条路对普通脚本不成立。chrome.cookies.getAll() 是唯一能在浏览器内拿到
 * 完整集合的正规 API。
 *
 * 隐私：只读取 Google 域下的 cookie 与页面上的两个元数据字段，推送到用户在
 * 设置里显式填写的服务器地址；不采集其它浏览数据。
 */

const GEMINI_URL = "https://gemini.google.com/app";
// 主查询用 gemini 页面 URL —— 浏览器实际会发给它的集合就是我们要的集合；
// 再补两个 Google 域入口，兜住只设在 .google.com 上的少数项。
const LOOKUP_URLS = [
  "https://gemini.google.com/app",
  "https://www.google.com/",
  "https://accounts.google.com/",
];

const CRITICAL = ["SAPISID"];
const SESSION_CANDIDATES = ["__Secure-1PSID", "__Secure-3PSID", "SID"];
// 排在前面便于人核对；其余 cookie 仍会全部导出（Google 会新增字段，
// 白名单式导出迟早会漏）
const PREFERRED_ORDER = [
  "SID", "HSID", "SSID", "APISID", "SAPISID", "LSID", "OSID", "LOGIN_INFO",
  "__Secure-1PSID", "__Secure-1PSIDTS", "__Secure-1PSIDCC",
  "__Secure-3PSID", "__Secure-3PSIDTS", "__Secure-3PSIDCC",
  "__Secure-ENID", "__Host-1PLSID", "__Host-3PLSID",
  "COMPASS", "__Secure-COMPASS", "NID", "DN", "ISOLATION", "AEC",
];

const $ = (id) => document.getElementById(id);
const inspectBtn = $("inspect");
const copyBtn = $("copy");
const pushBtn = $("push");
const statusEl = $("status");
const serverInput = $("server");
const tokenInput = $("token");

function setStatus(message, kind = "") {
  statusEl.textContent = message;
  statusEl.className = kind;
}

function normalizeDomain(domain = "") {
  return String(domain || "").replace(/^\./, "").toLowerCase();
}

function isGoogleScoped(cookie) {
  const d = normalizeDomain(cookie.domain);
  return d === "google.com" || d.endsWith(".google.com") || d === "googleapis.com"
    || d.endsWith(".googleapis.com");
}

/** 同名 cookie 多份时挑最可能是浏览器实际发送的那一份。 */
function scoreCookie(cookie) {
  let s = 0;
  if (cookie.secure) s += 8;
  if (cookie.httpOnly) s += 4;          // 关键鉴权项都是 HttpOnly，优先保留
  const dom = normalizeDomain(cookie.domain);
  s += Math.min(4, (dom.match(/\./g) || []).length);   // 域越具体越优先
  if (cookie.session) {
    s += 1;
  } else if (cookie.expirationDate) {
    s += 2;                              // 有明确过期时间的持久 cookie 更可信
  }
  if (cookie.value && cookie.value.length > 3) s += 1;
  return s;
}

async function readGoogleCookies() {
  const stores = await chrome.cookies.getAllCookieStores();
  const all = [];
  for (const store of stores) {
    for (const url of LOOKUP_URLS) {
      try {
        const found = await chrome.cookies.getAll({ storeId: store.id, url });
        all.push(...found);
      } catch {
        // 某些 store 可能不支持按 url 查询，忽略
      }
    }
  }
  const byName = new Map();
  for (const c of all) {
    if (!c || !c.name || !c.value) continue;
    if (!isGoogleScoped(c)) continue;
    const prev = byName.get(c.name);
    if (!prev || scoreCookie(c) > scoreCookie(prev)) byName.set(c.name, c);
  }
  return byName;
}

function orderedNames(byName) {
  const present = new Set(byName.keys());
  const head = PREFERRED_ORDER.filter((n) => present.has(n));
  const tail = [...present].filter((n) => !head.includes(n)).sort();
  return [...head, ...tail];
}

function buildCookieString(byName) {
  return orderedNames(byName)
    .map((n) => `${n}=${byName.get(n).value}`)
    .join("; ");
}

function validate(byName) {
  const missingCore = CRITICAL.filter((n) => !byName.has(n));
  const sessionCookie = SESSION_CANDIDATES.find((n) => byName.has(n)) || null;
  return {
    valid: missingCore.length === 0 && Boolean(sessionCookie),
    missingCore,
    sessionCookie,
  };
}

function chooseGeminiTab(tabs) {
  return tabs.find((t) => (t.url || "").startsWith("https://gemini.google.com/")) || null;
}

/**
 * 读取页面上的 SNlM0e（xsrf）与 cfb2h（build label）。
 * 两者都是 HttpOnly，document.cookie 读不到；WIZ_global_data 是首选来源，
 * 页面 HTML 与 performance 条目作为兜底。
 */
async function readPageMetadata(tabs) {
  const tab = chooseGeminiTab(tabs);
  if (!tab?.id) {
    return { error: "请先打开并登录 https://gemini.google.com/app 然后刷新页面。" };
  }
  try {
    const result = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      world: "MAIN",
      func: () => {
        const wiz = globalThis.WIZ_global_data || {};
        const html = document.documentElement?.innerHTML || "";
        const decode = (v) => {
          if (!v) return null;
          try { return JSON.parse(`"${v.replace(/"/g, '\\"')}"`); }
          catch {
            return String(v).replace(/\\u003d/gi, "=").replace(/\\u0026/gi, "&")
              .replace(/\\u003c/gi, "<").replace(/\\u003e/gi, ">");
          }
        };
        const regexValue = (name) => {
          for (const re of [
            new RegExp(`"${name}"\\s*:\\s*"([^"\\n]+)"`),
            new RegExp(`\\\\"${name}\\\\"\\s*:\\s*\\\\"([^"\\n]+)\\\\"`),
          ]) {
            const m = html.match(re);
            if (m?.[1]) return decode(m[1]);
          }
          return null;
        };
        let resourceBl = null;
        try {
          for (const e of performance.getEntriesByType("resource")) {
            if (!e?.name?.includes("gemini.google.com")) continue;
            try {
              const bl = new URL(e.name).searchParams.get("bl");
              if (bl) { resourceBl = bl; break; }
            } catch { /* 非法 URL 跳过 */ }
          }
        } catch { /* performance 不可用 */ }

        const u = (location.pathname || "").match(/\/u\/(\d+)/);
        return {
          xsrfToken: wiz.SNlM0e || regexValue("SNlM0e") || null,
          geminiBl: wiz.cfb2h || resourceBl || regexValue("cfb2h") || null,
          authUser: u ? parseInt(u[1], 10) : 0,
          url: location.href,
        };
      },
    });
    return result?.[0]?.result || { error: "读取页面数据失败。" };
  } catch (error) {
    return { error: error?.message || String(error) };
  }
}

async function buildSession() {
  const tabs = await chrome.tabs.query({ url: "https://gemini.google.com/*" });
  const byName = await readGoogleCookies();
  const meta = await readPageMetadata(tabs);
  return { byName, meta, authUser: Number.isInteger(meta.authUser) ? meta.authUser : 0 };
}

function describe(s) {
  const v = validate(s.byName);
  const lines = [
    `Cookie 条数：${s.byName.size}`,
    `SAPISID：${s.byName.has("SAPISID") ? "已取到" : "缺失"}`,
    `会话 Cookie：${v.sessionCookie || "缺失（需 __Secure-1PSID / __Secure-3PSID / SID 之一）"}`,
    `XSRF (SNlM0e)：${s.meta.xsrfToken ? "已取到" : "未取到"}`,
    `bl (cfb2h)：${s.meta.geminiBl || "未取到（将保留服务端现值）"}`,
    `auth_user：${s.authUser}`,
  ];
  if (s.meta.error) lines.push(`页面数据：${s.meta.error}`);
  if (!v.valid) {
    lines.push("", "会话不完整：需要在同一个浏览器里登录 Gemini 后刷新页面再试。");
  }
  return lines.join("\n");
}

async function loadSettings() {
  const { server = "", token = "" } = await chrome.storage.local.get(["server", "token"]);
  serverInput.value = server;
  tokenInput.value = token;
  return { server, token };
}

async function saveSettings() {
  const server = serverInput.value.trim().replace(/\/+$/, "");
  const token = tokenInput.value.trim();
  await chrome.storage.local.set({ server, token });
  if (server) {
    // 只对用户填写的那个源申请权限，避免安装时就索要全站权限
    try {
      await chrome.permissions.request({ origins: [server + "/*"] });
    } catch { /* 用户拒绝也能用复制方案 */ }
  }
  return { server, token };
}

async function pingServer(server) {
  const res = await fetch(server + "/health", { method: "GET", credentials: "omit" });
  if (!res.ok) throw new Error(`服务端 /health 返回 ${res.status}`);
  const data = await res.json();
  if (!data || data.status !== "ok") throw new Error("服务端 /health 响应异常");
  return data;
}

inspectBtn.addEventListener("click", async () => {
  inspectBtn.disabled = true;
  setStatus("正在读取 cookie 与页面数据…");
  try {
    const s = await buildSession();
    setStatus(describe(s), validate(s.byName).valid ? "ok" : "warn");
  } catch (e) {
    setStatus(String(e?.message || e), "warn");
  } finally {
    inspectBtn.disabled = false;
  }
});

copyBtn.addEventListener("click", async () => {
  copyBtn.disabled = true;
  setStatus("正在拼接 cookie…");
  try {
    const s = await buildSession();
    const v = validate(s.byName);
    if (!v.valid) { setStatus(describe(s), "warn"); return; }
    const text = buildCookieString(s.byName);
    await navigator.clipboard.writeText(text);
    setStatus(
      `已复制 ${s.byName.size} 条 cookie（${text.length} 字符）到剪贴板。\n\n` +
      "直接粘进管理台「配置 → Cookie」保存即可 —— 服务端会自动识别裸串 / cURL / JSON。",
      "ok");
  } catch (e) {
    setStatus(String(e?.message || e), "warn");
  } finally {
    copyBtn.disabled = false;
  }
});

pushBtn.addEventListener("click", async () => {
  pushBtn.disabled = true;
  try {
    const { server, token } = await chrome.storage.local.get(["server", "token"]);
    if (!server) { setStatus("请先在「服务器设置」里填写服务地址。", "warn"); return; }
    if (!token) { setStatus("请先在「服务器设置」里填写推送令牌。", "warn"); return; }

    setStatus("正在读取 cookie…");
    const s = await buildSession();
    const v = validate(s.byName);
    if (!v.valid) { setStatus(describe(s), "warn"); return; }
    const cookie = buildCookieString(s.byName);

    setStatus("正在推送…");
    const payload = {
      cookie,
      sapisid: s.byName.get("SAPISID")?.value || null,
      auth_user: s.authUser,
      xsrf_token: s.meta.xsrfToken || null,
      gemini_bl: s.meta.geminiBl || null,
      label: "chrome",
    };
    const res = await fetch(server + "/admin/api/cookie-push", {
      method: "POST",
      credentials: "omit",
      headers: {
        "Content-Type": "application/json",
        "X-Cookie-Push-Token": token,
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data?.error?.message || data?.error || `HTTP ${res.status}`;
      const hint = res.status === 404
        ? "\n（404 通常表示服务端未设置 cookie_push_token，该功能处于关闭状态）"
        : res.status === 401 ? "\n（401 表示令牌不匹配）"
        : res.status === 429 ? "\n（429 表示失败过多被限流，等 5 分钟）" : "";
      setStatus(`推送失败：${msg}${hint}`, "warn");
      return;
    }
    setStatus(
      `推送成功。\n\n已应用 cookie：${data.cookie_count} 条（SAPISID ${data.has_sapisid ? "有" : "无"}）\n` +
      `随带字段：${Object.keys(data.applied || {}).join(", ") || "无"}\n` +
      `落盘位置：${data.cookie_file}\n\n无需重启，下一个请求即用新 Cookie。`,
      "ok");
  } catch (e) {
    setStatus(`推送失败：${e?.message || e}\n\n检查服务器地址是否可访问、是否 HTTPS、`
      + "以及扩展是否被授予该域名权限（点「保存并授权该域名」）。", "warn");
  } finally {
    pushBtn.disabled = false;
  }
});

$("save").addEventListener("click", async () => {
  const { server } = await saveSettings();
  setStatus(server ? `已保存。服务器：${server}` : "已保存（服务器地址为空，仅可用复制方案）。",
    server ? "ok" : "warn");
});

$("test").addEventListener("click", async () => {
  const server = serverInput.value.trim().replace(/\/+$/, "");
  if (!server) { setStatus("请先填写服务器地址。", "warn"); return; }
  try {
    await saveSettings();
    const data = await pingServer(server);
    setStatus(`连通正常：v${data.version}，bl=${data.gemini_bl}\n`
      + `Cookie 已配置：${data.cookie_configured ? "是" : "否"}`, "ok");
  } catch (e) {
    setStatus(`连通失败：${e?.message || e}`, "warn");
  }
});

loadSettings();
