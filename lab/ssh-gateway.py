"""Fixed TCP relay: publish SSH without giving the restricted host an uplink."""
import select
import socket
import socketserver

class Relay(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            with socket.create_connection(("10.203.77.3", 22), timeout=10) as upstream:
                upstream.settimeout(None)
                sockets = [self.request, upstream]
                while True:
                    ready, _, _ = select.select(sockets, [], [], 300)
                    if not ready:
                        continue
                    for source in ready:
                        data = source.recv(65536)
                        if not data:
                            return
                        (upstream if source is self.request else self.request).sendall(data)
        except (OSError, ConnectionError):
            return

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

with Server(("0.0.0.0", 2222), Relay) as server:
    server.serve_forever()
