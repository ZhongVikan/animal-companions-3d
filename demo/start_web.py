"""Serve an extracted Web build on the local computer and open it."""

import argparse
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Timer


class WebBuildHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".wasm": "application/wasm",
        ".pck": "application/octet-stream",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    options = parser.parse_args()
    directory = Path(__file__).resolve().parent
    if not (directory / "index.html").is_file():
        parser.error("Place this script next to the exported index.html.")

    handler = partial(WebBuildHandler, directory=directory)
    with ThreadingHTTPServer(("127.0.0.1", options.port), handler) as server:
        url = f"http://127.0.0.1:{server.server_port}/index.html"
        print(f"动物派对 Web 版  {url}\n按 Ctrl+C 关闭。", flush=True)
        if not options.no_browser:
            Timer(0.25, webbrowser.open, args=(url,)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
