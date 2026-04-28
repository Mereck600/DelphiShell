import argparse
import json
import os
import socket
from pathlib import Path

from infer_delphi import handle_request, load_model_once


DEFAULT_SOCKET_PATH = "/tmp/delphi_shell.sock"


def parse_args():
    parser = argparse.ArgumentParser(description="Persistent Delphi inference server")
    parser.add_argument("--socket", default=DEFAULT_SOCKET_PATH, help="Unix socket path")
    return parser.parse_args()


def recv_line(conn):
    chunks = []
    while True:
        data = conn.recv(4096)
        if not data:
            break
        chunks.append(data)
        if b"\n" in data:
            break
    if not chunks:
        return ""
    return b"".join(chunks).split(b"\n", 1)[0].decode("utf-8", errors="replace")


def send_json(conn, payload):
    conn.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))


def main():
    args = parse_args()
    socket_path = Path(args.socket)

    if socket_path.exists():
        socket_path.unlink()

    load_model_once()

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(socket_path))
    server.listen(8)

    try:
        while True:
            conn, _ = server.accept()
            with conn:
                line = recv_line(conn)
                if not line:
                    send_json(conn, {"mode": "answer", "text": "Empty Delphi request."})
                    continue

                try:
                    payload = json.loads(line)
                    user_text = str(payload.get("text", "")).strip()
                except json.JSONDecodeError:
                    send_json(conn, {"mode": "answer", "text": "Invalid Delphi request."})
                    continue

                send_json(conn, handle_request(user_text))
    finally:
        server.close()
        if socket_path.exists():
            socket_path.unlink()


if __name__ == "__main__":
    main()
