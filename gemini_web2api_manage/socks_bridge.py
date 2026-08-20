"""SOCKS5 -> local HTTP proxy bridge.

The upstream gemini client only understands http:// proxies (urllib's
ProxyHandler / httpx transport). When the admin console configures a socks5://
proxy, this module spins up a tiny local HTTP proxy in-process and rewrites
CONFIG["proxy"] to point at it. Every tunneled connection is then forwarded
through the SOCKS5 upstream via PySocks (already installed; no socksio needed).
"""
import re
import socket
import socketserver
import threading
from urllib.parse import urlparse

import socks

_READ_BUF = 65536


def parse_socks_url(proxy_url: str):
    u = urlparse(proxy_url)
    return {
        "host": u.hostname,
        "port": u.port or 1080,
        "username": u.username,
        "password": u.password,
    }


class SocksBridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, proxy_url: str, addr=("127.0.0.1", 0)):
        self.proxy = parse_socks_url(proxy_url)
        super().__init__(addr, SocksBridgeHandler)
        self._thread = None

    def start(self) -> int:
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()
        return self.server_address[1]

    def stop(self):
        try:
            self.shutdown()
        finally:
            self.server_close()


class SocksBridgeHandler(socketserver.BaseRequestHandler):
    def handle(self):
        client = self.request
        try:
            client.settimeout(60)
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = client.recv(_READ_BUF)
                if not chunk:
                    return
                head += chunk
                if len(head) > 64 * 1024:
                    return
            lines = head.split(b"\r\n")
            first = lines[0].decode("latin-1", "replace")
            body = head.partition(b"\r\n\r\n")[2]

            if first.upper().startswith("CONNECT "):
                target = first.split(" ", 2)[1]
                host, _, port = target.rpartition(":")
                try:
                    tunnel = self._tunnel(host, int(port))
                except Exception:
                    try:
                        client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                    except OSError:
                        pass
                    return
                client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                if body:
                    tunnel.sendall(body)
                self._relay(client, tunnel)
                return

            # Plain HTTP (absolute-URI or Host header)
            m = re.match(r"^\S+\s+(\S+)", first)
            if not m:
                return
            url = m.group(1)
            if "://" in url:
                parsed = urlparse(url)
                host, port = parsed.hostname or "127.0.0.1", parsed.port or 80
                rest = b" ".join(head.split(b" ")[2:]).lstrip()
                request = b" ".join(head.split(b" ")[:2]) + b" " + rest
                request += b"\r\n" + b"\r\n".join(lines[1:]) + b"\r\n\r\n"
            else:
                host = None
                for line in lines[1:]:
                    if line.lower().startswith(b"host:"):
                        host_port = line[5:].strip().decode("latin-1")
                        host, _, port_s = host_port.rpartition(":")
                        port = int(port_s) if port_s.isdigit() else 80
                        break
                if not host:
                    return
                request = head
            try:
                tunnel = self._tunnel(host, int(port))
            except Exception:
                try:
                    client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                except OSError:
                    pass
                return
            if body:
                request += body
            tunnel.sendall(request)
            self._relay(client, tunnel)
        except Exception:
            pass

    def _tunnel(self, host: str, port: int) -> socket.socket:
        p = self.server.proxy
        s = socks.socksocket()
        s.set_proxy(
            socks.SOCKS5, p["host"], p["port"],
            username=p.get("username"), password=p.get("password"),
            rdns=True,
        )
        s.settimeout(60)
        s.connect((host, port))
        return s

    def _relay(self, a: socket.socket, b: socket.socket):
        stop = threading.Event()

        def pump(src, dst):
            try:
                while not stop.is_set():
                    try:
                        data = src.recv(_READ_BUF)
                    except (socket.timeout, OSError):
                        break
                    if not data:
                        break
                    dst.sendall(data)
            except OSError:
                pass
            finally:
                stop.set()
                for s in (a, b):
                    try:
                        s.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass

        t1 = threading.Thread(target=pump, args=(a, b), daemon=True)
        t2 = threading.Thread(target=pump, args=(b, a), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()


_bridge = None
_bridge_port = None


def ensure_bridge(proxy_url: str) -> int:
    """Start (or reuse) the local HTTP proxy for a socks5:// upstream.
    Returns the local port, or None when the upstream isn't socks5."""
    global _bridge, _bridge_port
    if not proxy_url or not str(proxy_url).startswith(("socks5://", "socks5h://")):
        return None
    if _bridge is not None:
        return _bridge_port
    _bridge = SocksBridgeServer(proxy_url)
    _bridge_port = _bridge.start()
    return _bridge_port


def local_proxy_for(proxy_url: str):
    """Resolve the effective http:// proxy URL to configure upstream with."""
    port = ensure_bridge(proxy_url)
    if port:
        return f"http://127.0.0.1:{port}"
    return proxy_url


def apply_proxy_bridge(config: dict):
    """Rewrite CONFIG so upstream sees an http proxy when the configured proxy
    is socks5. The original value is kept in config['_proxy_original'] so the
    admin console still displays the user's socks5:// address."""
    proxy = config.get("proxy")
    if proxy and str(proxy).startswith(("socks5://", "socks5h://")):
        config["_proxy_original"] = proxy
        config["proxy"] = local_proxy_for(proxy)
    else:
        config.pop("_proxy_original", None)
    return config
