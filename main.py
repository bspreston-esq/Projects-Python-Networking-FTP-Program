#!/usr/bin/env python3
"""A small FTP client, plus a loopback FTP server used by the demo."""
import argparse
import ftplib
import os
import socket
import tempfile
import threading

class MiniFTPServer:
    """Minimal PASV-mode FTP server: USER, PASS, TYPE, PASV, LIST, RETR, STOR, DELE, QUIT."""

    def __init__(self, root: str, host: str = "127.0.0.1", port: int = 0):
        self.root = os.path.abspath(root)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(5)
        self.host, self.port = self.sock.getsockname()[:2]
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.running = False
        self.sock.close()
        if self.thread:
            self.thread.join(timeout=2)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    def _accept_loop(self):
        while self.running:
            try:
                connection, _ = self.sock.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(connection,), daemon=True).start()

    def _path(self, name: str) -> str:
        return os.path.join(self.root, os.path.basename(name))

    def _handle(self, connection: socket.socket):
        connection.settimeout(10)
        reader = connection.makefile("rb")
        connection.sendall(b"220 MiniFTP ready\r\n")
        data_listener = None
        try:
            while True:
                line = reader.readline()
                if not line:
                    break
                command, _, argument = line.decode("utf-8", "replace").strip().partition(" ")
                command = command.upper()
                if command == "USER":
                    connection.sendall(b"331 password required\r\n")
                elif command == "PASS":
                    connection.sendall(b"230 logged in\r\n")
                elif command == "SYST":
                    connection.sendall(b"215 UNIX Type: L8\r\n")
                elif command == "TYPE":
                    connection.sendall(b"200 type set\r\n")
                elif command == "PWD":
                    connection.sendall(b'257 "/" is current directory\r\n')
                elif command == "CWD":
                    connection.sendall(b"250 directory changed\r\n")
                elif command == "PASV":
                    if data_listener:
                        data_listener.close()
                    data_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    data_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    data_listener.bind((self.host, 0))
                    data_listener.listen(1)
                    port = data_listener.getsockname()[1]
                    numbers = ",".join(self.host.split(".")) + f",{port >> 8},{port & 255}"
                    connection.sendall(f"227 Entering Passive Mode ({numbers})\r\n".encode())
                elif command in ("LIST", "NLST"):
                    connection.sendall(b"150 opening data connection\r\n")
                    with data_listener.accept()[0] as data:
                        lines = []
                        for name in sorted(os.listdir(self.root)):
                            path = os.path.join(self.root, name)
                            if os.path.isfile(path):
                                lines.append(f"-rw-r--r-- 1 demo demo {os.path.getsize(path):>8} Jan 01 00:00 {name}\r\n")
                        data.sendall("".join(lines).encode())
                    data_listener.close(); data_listener = None
                    connection.sendall(b"226 transfer complete\r\n")
                elif command == "RETR":
                    path = self._path(argument)
                    if not os.path.isfile(path):
                        connection.sendall(b"550 no such file\r\n")
                        continue
                    connection.sendall(b"150 opening data connection\r\n")
                    with open(path, "rb") as source, data_listener.accept()[0] as data:
                        data.sendall(source.read())
                    data_listener.close(); data_listener = None
                    connection.sendall(b"226 transfer complete\r\n")
                elif command == "STOR":
                    path = self._path(argument)
                    connection.sendall(b"150 ready for data\r\n")
                    with open(path, "wb") as target, data_listener.accept()[0] as data:
                        while True:
                            chunk = data.recv(65536)
                            if not chunk:
                                break
                            target.write(chunk)
                    data_listener.close(); data_listener = None
                    connection.sendall(b"226 transfer complete\r\n")
                elif command == "DELE":
                    try:
                        os.remove(self._path(argument))
                        connection.sendall(b"250 deleted\r\n")
                    except OSError:
                        connection.sendall(b"550 delete failed\r\n")
                elif command == "QUIT":
                    connection.sendall(b"221 goodbye\r\n")
                    break
                else:
                    connection.sendall(b"502 command not implemented\r\n")
        finally:
            if data_listener:
                data_listener.close()
            connection.close()

def demo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        download_dir = os.path.join(tmp, "downloads")
        os.makedirs(download_dir)
        with open(os.path.join(tmp, "hello.txt"), "w") as fh:
            fh.write("Hello from the FTP server.\n")
        with MiniFTPServer(tmp) as server:
            client = ftplib.FTP()
            client.connect(server.host, server.port, timeout=5)
            print("welcome:", client.getwelcome())
            client.login("demo", "demo")
            print("listing:")
            client.dir(lambda line: print("  " + line))
            local = os.path.join(download_dir, "hello.txt")
            with open(local, "wb") as fh:
                client.retrbinary("RETR hello.txt", fh.write)
            print("downloaded:", open(local).read().strip())
            client.storbinary("STOR upload.txt", open(local, "rb"))
            print("upload exists:", os.path.exists(os.path.join(tmp, "upload.txt")))
            client.quit()

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host")
    parser.add_argument("--port", type=int, default=21)
    parser.add_argument("--user", default="anonymous")
    parser.add_argument("--password", default="guest")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--get")
    parser.add_argument("--put")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo or not args.host:
        demo()
        return
    client = ftplib.FTP()
    try:
        client.connect(args.host, args.port, timeout=10)
        client.login(args.user, args.password)
        if args.list:
            client.dir(print)
        if args.get:
            with open(os.path.basename(args.get), "wb") as fh:
                client.retrbinary(f"RETR {args.get}", fh.write)
        if args.put:
            with open(args.put, "rb") as fh:
                client.storbinary(f"STOR {os.path.basename(args.put)}", fh)
        client.quit()
    except (OSError, ftplib.all_errors) as exc:
        print(f"FTP error: {exc}")

if __name__ == "__main__":
    main()
