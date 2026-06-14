import socket, threading, os, datetime

HOST, TCP_PORT, UDP_PORT = "0.0.0.0", 8000, 9000
WWW_DIR = os.path.join(os.path.dirname(__file__), "HTML")
TYPES = {".html":"text/html",".css":"text/css",".js":"application/javascript",
         ".png":"image/png",".jpg":"image/jpeg",".ico":"image/x-icon"}

def log(ip, path, code):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {ip} {path} {code}")

def response(code, text, ctype, body):
    return f"HTTP/1.1 {code} {text}\r\nContent-Type: {ctype}; charset=utf-8\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode() + body

def handle(conn, addr):
    try:
        raw = b""
        while b"\r\n\r\n" not in raw:
            raw += conn.recv(4096)
        line = raw.decode(errors="ignore").split("\r\n")[0].split()
        if len(line) < 2 or line[0] != "GET":
            conn.sendall(response(400, "Bad Request", "text/html", b"<h1>400</h1>")); return
        path = line[1] if line[1] != "/" else "/index.html"
        file = os.path.join(WWW_DIR, os.path.normpath(path.lstrip("/")))
        if not os.path.isfile(file):
            conn.sendall(response(404, "Not Found", "text/html", b"<h1>404 Not Found</h1>"))
            log(addr[0], path, 404); return
        body = open(file, "rb").read()
        conn.sendall(response(200, "OK", TYPES.get(os.path.splitext(file)[1], "application/octet-stream"), body))
        log(addr[0], path, 200)
    except Exception as e:
        conn.sendall(response(500, "Internal Server Error", "text/html", f"<h1>500 {e}</h1>".encode()))
    finally:
        conn.close()

def tcp():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, TCP_PORT)); s.listen(10)
    print(f"[TCP] HTTP :{TCP_PORT}  |  folder: {WWW_DIR}")
    while True:
        c, a = s.accept()
        threading.Thread(target=handle, args=(c, a), daemon=True).start()

def udp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, UDP_PORT))
    print(f"[UDP] Echo :{UDP_PORT}")
    while True:
        d, a = s.recvfrom(1024); s.sendto(d, a)

os.makedirs(WWW_DIR, exist_ok=True)
# Buat index.html default kalau belum ada
if not os.path.exists(os.path.join(WWW_DIR, "index.html")):
    open(os.path.join(WWW_DIR, "index.html"), "w").write(
        "<h1>Halo dari Web Server!</h1><a href='/page.html'>page.html</a>")
if not os.path.exists(os.path.join(WWW_DIR, "page.html")):
    open(os.path.join(WWW_DIR, "page.html"), "w").write(
        "<h1>Page 2</h1><a href='/index.html'>back</a>")

threading.Thread(target=tcp, daemon=True).start()
threading.Thread(target=udp, daemon=True).start()
print("[INFO] Web Server jalan. Ctrl+C untuk stop.")
try: threading.Event().wait()
except KeyboardInterrupt: print("Stop.")