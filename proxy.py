import socket
import threading
import os
import datetime


# KONFIGURASI
HOST = "0.0.0.0"
PROXY_PORT = 8080           

# Alamat Web Server
WEB_SERVER_HOST = "192.168.18.122"  # IP Laptop Web Server
WEB_SERVER_PORT = 8000

# Folder untuk menyimpan cache lokal
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# HELPER: Logging
def log(client_ip, url, cache_status, resp_time_ms):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {client_ip} \"{url}\" {cache_status} {resp_time_ms:.1f}ms")

# HELPER: URL -> path file cache
def url_to_cache_path(url_path):
    """Ubah URL path menjadi path file cache yang aman."""
    safe = url_path.strip("/").replace("/", "_") or "index.html"
    return os.path.join(CACHE_DIR, safe)

# HELPER: Ambil isi custom error page untuk proxy
def get_custom_error_page(status_code, fallback_text):
    for folder in ["HTML", "www"]:
        path = os.path.join(os.path.dirname(__file__), folder, "status", f"{status_code}.html")
        if os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    return f.read()
            except:
                pass
    return f"<h1>{status_code} {fallback_text}</h1>".encode()


# HELPER: Forward request ke Web Server
def forward_to_webserver(request_bytes):
    """
    Kirim request ke Web Server dan kembalikan response mentah.
    Return: (response_bytes, error_string)
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)  # timeout 5 detik
        s.connect((WEB_SERVER_HOST, WEB_SERVER_PORT))
        s.sendall(request_bytes)

        # Terima seluruh response
        response = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            response += chunk
        s.close()
        return response, None

    except socket.timeout:
        return None, "timeout"
    except ConnectionRefusedError:
        return None, "refused"
    except Exception as e:
        return None, str(e)

# HELPER: Parse URL dari HTTP request
def parse_request(raw_bytes):
    """Return (method, path, raw_request_str) atau None jika invalid."""
    try:
        text = raw_bytes.decode(errors="ignore")
        first_line = text.split("\r\n")[0]
        parts = first_line.split()
        if len(parts) < 2:
            return None
        return parts[0], parts[1], text
    except:
        return None

# TCP: Handle satu client
def handle_client(conn, addr):
    client_ip = addr[0]
    t_start = datetime.datetime.now()

    try:
        # Terima request dari client
        raw = b""
        conn.settimeout(5)
        try:
            while b"\r\n\r\n" not in raw:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                raw += chunk
        except socket.timeout:
            conn.close()
            return

        if not raw:
            conn.close()
            return

        result = parse_request(raw)
        if result is None:
            conn.close()
            return

        method, url_path, _ = result

        # Clean absolute URI
        if url_path.startswith("http://") or url_path.startswith("https://"):
            parts = url_path.split("://", 1)[1].split("/", 1)
            url_path = "/" + parts[1] if len(parts) > 1 else "/"

        # Normalize path
        if url_path == "/":
            url_path = "/index.html"

        cache_file = url_to_cache_path(url_path)

        # === CEK CACHE ===
        if os.path.isfile(cache_file):
            # CACHE HIT
            with open(cache_file, "rb") as f:
                cached_response = f.read()
            conn.sendall(cached_response)
            elapsed = (datetime.datetime.now() - t_start).total_seconds() * 1000
            log(client_ip, url_path, "HIT", elapsed)
            conn.close()
            return

        # === CACHE MISS: Forward ke Web Server ===
        # Rebuild request agar Host header mengarah ke Web Server
        request_line = f"{method} {url_path} HTTP/1.1\r\n"
        headers = (
            f"Host: {WEB_SERVER_HOST}:{WEB_SERVER_PORT}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        forward_request = (request_line + headers).encode()

        response, error = forward_to_webserver(forward_request)

        if error == "timeout":
            body = get_custom_error_page(504, "Gateway Timeout")
            resp = (
                "HTTP/1.1 504 Gateway Timeout\r\n"
                "Content-Type: text/html\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode() + body
            conn.sendall(resp)
            elapsed = (datetime.datetime.now() - t_start).total_seconds() * 1000
            log(client_ip, url_path, "MISS-TIMEOUT", elapsed)
            conn.close()
            return

        if error or not response:
            body = get_custom_error_page(502, "Bad Gateway")
            resp = (
                "HTTP/1.1 502 Bad Gateway\r\n"
                "Content-Type: text/html\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode() + body
            conn.sendall(resp)
            elapsed = (datetime.datetime.now() - t_start).total_seconds() * 1000
            log(client_ip, url_path, "MISS-ERROR", elapsed)
            conn.close()
            return

        # Simpan ke cache hanya jika response 200 OK
        if response.startswith(b"HTTP/1.1 200") or response.startswith(b"HTTP/1.0 200"):
            with open(cache_file, "wb") as f:
                f.write(response)

        # Kirim response ke client
        conn.sendall(response)
        elapsed = (datetime.datetime.now() - t_start).total_seconds() * 1000
        log(client_ip, url_path, "MISS", elapsed)

    except Exception as e:
        print(f"[ERROR] handle_client: {e}")
        try:
            body = get_custom_error_page(502, "Bad Gateway")
            resp = (
                "HTTP/1.1 502 Bad Gateway\r\n"
                "Content-Type: text/html\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode() + body
            conn.sendall(resp)
        except:
            pass
    finally:
        conn.close()

# MAIN: Proxy Server (Thread-per-connection)
if __name__ == "__main__":
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PROXY_PORT))
    server.listen(10)
    print(f"[PROXY] Listening on {HOST}:{PROXY_PORT}")
    print(f"[PROXY] Forwarding ke {WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    print(f"[PROXY] Cache dir: {CACHE_DIR}")

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[INFO] Proxy dihentikan.")