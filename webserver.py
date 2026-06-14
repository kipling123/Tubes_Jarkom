import socket
import threading
import os
import datetime

# KONFIGURASI
HOST = "0.0.0.0"
TCP_PORT = 8000       # Port HTTP
UDP_PORT = 9000       # Port QoS Echo
WWW_DIR = os.path.join(os.path.dirname(__file__), "www")

# HELPER: Logging
def log(client_ip, path, status_code):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {client_ip} \"{path}\" {status_code}")

# HELPER: Build HTTP Response
def build_response(status_code, status_text, content_type, body_bytes):
    header = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: {content_type}; charset=utf-8\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"Connection: close\r\n"
        "\r\n"
    )
    return header.encode() + body_bytes

# HELPER: Ambil isi custom error page dari status/
# Fallback ke HTML sederhana jika file tidak ada
def get_error_page(status_code, fallback_text):
    error_file = os.path.join(WWW_DIR, "status", f"{status_code}.html")
    if os.path.isfile(error_file):
        with open(error_file, "rb") as f:
            return f.read()
    return f"<h1>{status_code} {fallback_text}</h1>".encode()

# TCP: Handle satu client HTTP
def handle_http_client(conn, addr):
    client_ip = addr[0]
    try:
        # Terima request (maks 4096 byte)
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk

        if not raw:
            conn.close()
            return

        # Parse baris pertama: "GET /path HTTP/1.1"
        first_line = raw.decode(errors="ignore").split("\r\n")[0]
        parts = first_line.split()

        # Validasi request
        if len(parts) < 2 or parts[0] != "GET":
            body = b"<h1>400 Bad Request</h1>"
            conn.sendall(build_response(400, "Bad Request", "text/html", body))
            log(client_ip, first_line, 400)
            conn.close()
            return

        url_path = parts[1]

        # Bersihkan path: "/" -> "/index.html"
        if url_path == "/":
            url_path = "/index.html"

        # Cegah path traversal
        safe_path = os.path.normpath(url_path.lstrip("/"))
        file_path = os.path.join(WWW_DIR, safe_path)

        # Pastikan file_path masih di dalam WWW_DIR
        if not os.path.realpath(file_path).startswith(os.path.realpath(WWW_DIR)):
            body = b"<h1>403 Forbidden</h1>"
            conn.sendall(build_response(403, "Forbidden", "text/html", body))
            log(client_ip, url_path, 403)
            conn.close()
            return

        # Cek keberadaan file
        if not os.path.isfile(file_path):
            body = get_error_page(404, "Not Found")
            conn.sendall(build_response(404, "Not Found", "text/html", body))
            log(client_ip, url_path, 404)
            conn.close()
            return

        # Tentukan Content-Type
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".html": "text/html",
            ".css":  "text/css",
            ".js":   "application/javascript",
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".ico":  "image/x-icon",
            ".mp4":  "video/mp4",
        }
        content_type = content_types.get(ext, "application/octet-stream")

        # Baca file dan kirim response
        with open(file_path, "rb") as f:
            body = f.read()

        conn.sendall(build_response(200, "OK", content_type, body))
        log(client_ip, url_path, 200)

    except Exception as e:
        print(f"[ERROR] handle_http_client: {e}")
        try:
            body = get_error_page(500, "Internal Server Error")
            conn.sendall(build_response(500, "Internal Server Error", "text/html", body))
            log(client_ip, "-", 500)
        except:
            pass
    finally:
        conn.close()

# TCP Server: HTTP (Thread-per-connection)
def start_tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, TCP_PORT))
    server.listen(10)
    print(f"[TCP] HTTP Server listening on {HOST}:{TCP_PORT}")
    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_http_client, args=(conn, addr), daemon=True)
        t.start()

# UDP Server: QoS Echo
def start_udp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((HOST, UDP_PORT))
    print(f"[UDP] QoS Echo Server listening on {HOST}:{UDP_PORT}")
    while True:
        try:
            data, addr = server.recvfrom(1024)
            # Echo balik payload tanpa diubah
            server.sendto(data, addr)
        except Exception as e:
            print(f"[ERROR] UDP echo: {e}")

# MAIN
if __name__ == "__main__":
    # Jalankan TCP dan UDP di thread terpisah
    t_tcp = threading.Thread(target=start_tcp_server, daemon=True)
    t_udp = threading.Thread(target=start_udp_server, daemon=True)

    t_tcp.start()
    t_udp.start()

    print("[INFO] Web Server running. Tekan Ctrl+C untuk berhenti.")
    try:
        t_tcp.join()
    except KeyboardInterrupt:
        print("\n[INFO] Server dihentikan.")