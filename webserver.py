import socket
import threading
import os
import datetime

# KONFIGURASI
HOST, TCP_PORT, UDP_PORT = "0.0.0.0", 8000, 9000

WWW_DIR = os.path.join(os.path.dirname(__file__), "www")
if not os.path.isdir(WWW_DIR):
    WWW_DIR = os.path.join(os.path.dirname(__file__), "HTML")

TYPES = {
    ".html": "text/html",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".ico":  "image/x-icon",
    ".mp4":  "video/mp4"
}

def log(ip, path, code):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {ip} \"{path}\" {code}")

def response(code, text, ctype, body):
    return (
        f"HTTP/1.1 {code} {text}\r\n"
        f"Content-Type: {ctype}; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode() + body

def get_error_page(code, fallback):
    file = os.path.join(WWW_DIR, "status", f"{code}.html")
    if os.path.isfile(file):
        try:
            return open(file, "rb").read()
        except:
            pass
    return f"<h1>{code} {fallback}</h1>".encode()

def handle(conn, addr):
    try:
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk
            
        if not raw:
            return

        line = raw.decode(errors="ignore").split("\r\n")[0].split()
        if len(line) < 2 or line[0] != "GET":
            body = get_error_page(400, "Bad Request")
            conn.sendall(response(400, "Bad Request", "text/html", body))
            log(addr[0], "-", 400)
            return

        path = line[1] if line[1] != "/" else "/index.html"
        file = os.path.join(WWW_DIR, os.path.normpath(path.lstrip("/")))

        real_www = os.path.realpath(WWW_DIR)
        real_file = os.path.realpath(file)
        if os.path.commonpath([real_www, real_file]) != real_www:
            body = get_error_page(403, "Forbidden")
            conn.sendall(response(403, "Forbidden", "text/html", body))
            log(addr[0], path, 403)
            return
        if not os.path.isfile(file):
            body = get_error_page(404, "Not Found")
            conn.sendall(response(404, "Not Found", "text/html", body))
            log(addr[0], path, 404)
            return

        body = open(file, "rb").read()
        conn.sendall(response(200, "OK", TYPES.get(os.path.splitext(file)[1], "application/octet-stream"), body))
        log(addr[0], path, 200)

    except Exception as e:
        body = get_error_page(500, "Internal Server Error")
        conn.sendall(response(500, "Internal Server Error", "text/html", body))
        log(addr[0], "-", 500)
    finally:
        conn.close()

def tcp():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, TCP_PORT))
    s.listen(10)
    print(f"[TCP] HTTP Server listening on port {TCP_PORT} (Folder: {WWW_DIR})")
    while True:
        c, a = s.accept()
        threading.Thread(target=handle, args=(c, a), daemon=True).start()

def udp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, UDP_PORT))
    print(f"[UDP] QoS Echo Server listening on port {UDP_PORT}")
    while True:
        d, a = s.recvfrom(1024)
        s.sendto(d, a)
        # Log penerimaan ping UDP QoS
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"[{ts}] [UDP QoS] Menerima ping dari {a[0]}:{a[1]} - Payload: {d.decode(errors='ignore')}")


if __name__ == "__main__":
    os.makedirs(WWW_DIR, exist_ok=True)
    threading.Thread(target=tcp, daemon=True).start()
    threading.Thread(target=udp, daemon=True).start()
    
    print("[INFO] Web Server berjalan. Tekan Ctrl+C untuk berhenti.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n[INFO] Web Server dihentikan.")
