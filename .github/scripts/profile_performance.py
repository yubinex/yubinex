#!/usr/bin/env python3
"""Measure isolated Chromium rendering, not GitHub/network performance.

Requires Chromium and Python's websockets package (benchmark only).
Example: profile_performance.py --panel hero --out /tmp/opencode/before.json
CPU seconds include Chromium's renderer/GPU child processes on Linux.
"""
import argparse
import asyncio
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request

import websockets


class CDP:
    def __init__(self, socket):
        self.socket, self.sequence = socket, 0

    async def call(self, method, params=None):
        self.sequence += 1
        seq = self.sequence
        await self.socket.send(json.dumps(dict(id=seq, method=method, params=params or {})))
        while True:
            msg = json.loads(await asyncio.wait_for(self.socket.recv(), timeout=30))
            if msg.get("id") == seq:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})


def cpu_seconds(group):
    total = 0
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            # comm may contain spaces/parentheses; fields below start at field 3.
            fields = path.read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) == group:
                total += int(fields[11]) + int(fields[12])
        except (OSError, ValueError, IndexError):
            continue
    return total / os.sysconf("SC_CLK_TCK")


async def measure(args, url, temp):
    executable = shutil.which("chromium") or shutil.which("google-chrome")
    if not executable:
        raise RuntimeError("Chromium/Google Chrome not found")
    command = [executable, "--headless", "--no-sandbox", "--disable-dev-shm-usage",
               "--no-first-run", "--no-default-browser-check", "--disable-background-networking", "--disable-extensions",
               "--remote-debugging-port=0", f"--user-data-dir={temp}", "about:blank"]
    with open(Path(temp) / "browser.log", "w") as log:
        browser = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
        try:
            portfile = Path(temp) / "DevToolsActivePort"
            for _ in range(200):
                if portfile.exists():
                    break
                if browser.poll() is not None:
                    raise RuntimeError("Chromium exited; inspect browser.log")
                await asyncio.sleep(.05)
            port = int(portfile.read_text().splitlines()[0])
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list") as response:
                target = next(t for t in json.load(response) if t["type"] == "page")
            async with websockets.connect(target["webSocketDebuggerUrl"], max_size=None) as socket:
                cdp = CDP(socket)
                await cdp.call("Page.enable")
                await cdp.call("Emulation.setDeviceMetricsOverride", dict(width=1000, height=1200,
                               deviceScaleFactor=1, mobile=False))
                await cdp.call("Emulation.setEmulatedMedia", dict(media="screen", features=[
                    dict(name="prefers-reduced-motion", value="reduce" if args.reduced_motion else "no-preference")]))
                await cdp.call("Page.navigate", dict(url=url))
                # Let images load and entrance animations settle before measuring.
                for _ in range(200):
                    result = await cdp.call("Runtime.evaluate", dict(expression=
                        "document.readyState === 'complete' && [...document.images].every(i => i.complete && i.naturalWidth > 0)"))
                    if result.get("result", {}).get("value"):
                        break
                    await asyncio.sleep(.05)
                else:
                    raise RuntimeError("Benchmark images failed to load")
                await asyncio.sleep(args.warmup)
                await cdp.call("Tracing.start", dict(categories="devtools.timeline,disabled-by-default-devtools.timeline",
                                                    transferMode="ReturnAsStream"))
                start_cpu, start = cpu_seconds(browser.pid), time.monotonic()
                await asyncio.sleep(args.seconds)
                elapsed, cpu = time.monotonic() - start, cpu_seconds(browser.pid) - start_cpu
                await cdp.call("Tracing.end")
                while True:
                    event = json.loads(await asyncio.wait_for(socket.recv(), timeout=30))
                    if event.get("method") == "Tracing.tracingComplete":
                        handle = event["params"]["stream"]
                        break
                chunks = []
                while True:
                    chunk = await cdp.call("IO.read", dict(handle=handle))
                    chunks.append(chunk["data"])
                    if chunk.get("eof"):
                        break
                await cdp.call("IO.close", dict(handle=handle))
                trace = json.loads("".join(chunks))
                if args.screenshot:
                    import base64
                    image = await cdp.call("Page.captureScreenshot", dict(format="png"))
                    Path(args.screenshot).write_bytes(base64.b64decode(image["data"]))
                totals = {}
                for event in trace["traceEvents"]:
                    if event.get("ph") == "X" and event.get("dur"):
                        entry = totals.setdefault(event["name"], dict(count=0, total_ms=0, max_ms=0))
                        ms = event["dur"] / 1000
                        entry["count"] += 1
                        entry["total_ms"] += ms
                        entry["max_ms"] = max(entry["max_ms"], ms)
                result = dict(panel=args.panel, theme=args.theme, reduced_motion=args.reduced_motion, warmup_seconds=args.warmup,
                              elapsed_seconds=elapsed, browser_cpu_seconds=cpu,
                              cpu_percent_one_core=cpu / elapsed * 100,
                              events=totals)
                Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
                print(json.dumps({k: v for k, v in result.items() if k != "events"}, indent=2))
        finally:
            # All Chromium children share the new process group.
            import signal
            try:
                os.killpg(browser.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            browser.wait(timeout=10)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=15)
    ap.add_argument("--warmup", type=float, default=12)
    ap.add_argument("--theme", choices=("dark", "light"), default="dark")
    ap.add_argument("--panel", choices=("all", "hero", "rest", "empty"), default="all")
    ap.add_argument("--reduced-motion", action="store_true")
    ap.add_argument("--screenshot")
    args = ap.parse_args()
    panels = {"all": ["hero", "labfile", "worldlines", "feed", "footer"], "hero": ["hero"],
              "rest": ["labfile", "worldlines", "feed", "footer"], "empty": []}[args.panel]
    background = "#0d1117" if args.theme == "dark" else "#ffffff"
    images = "".join(f'<p><img src="/assets/{p}-{args.theme}.svg" width="{600 if p == "footer" else 880}"></p>' for p in panels)
    page = f'<html><head><style>body{{margin:24px;background:{background};text-align:center}}img{{max-width:100%}}</style></head><body>{images}</body></html>'

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/__benchmark__":
                body = page.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                super().do_GET()

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(args.root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="profile-benchmark-", dir=os.environ.get("TMPDIR")) as temp:
            asyncio.run(measure(args, f"http://127.0.0.1:{server.server_port}/__benchmark__", temp))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
