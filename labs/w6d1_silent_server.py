"""labs/w6d1_silent_server.py -- Week 6 Din 1.
Accepts TCP connections on 127.0.0.1:8099 and never sends a byte back. A client sees a connection that
succeeds and a response that never starts. Stop it with Ctrl+C or Stop-Process."""
import socket

s = socket.socket()
s.bind(("127.0.0.1", 8099))
s.listen(16)
held = []
print("silent_server listening 127.0.0.1:8099", flush=True)
while True:
    conn, addr = s.accept()
    held.append(conn)  # keep a reference so the socket is not closed
    print(f"accepted {addr}", flush=True)
