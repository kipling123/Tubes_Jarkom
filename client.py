import socket
import time
import sys

PROXY_HOST = "192.168.18.49"   # IP Laptop Proxy
PROXY_PORT = 8080

SERVER_HOST = "192.168.18.122" # IP Laptop Web Server
UDP_PORT    = 9000

UDP_PACKET_COUNT = 10   # minimal 10 paket
UDP_TIMEOUT      = 1.0  # timeout 1 detik per paket

# MODE 1: HTTP via Proxy (TCP)
def http_request(path="/"):
    """Kirim HTTP GET ke proxy dan tampilkan response."""
    print(f"\n[HTTP] Menghubungi Proxy {PROXY_HOST}:{PROXY_PORT} -> GET {path}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((PROXY_HOST, PROXY_PORT))

        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {PROXY_HOST}:{PROXY_PORT}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        s.sendall(request.encode())

        # Terima response
        response = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            response += chunk
        s.close()

        # Tampilkan header dan isi response
        if b"\r\n\r\n" in response:
            header_part, body_part = response.split(b"\r\n\r\n", 1)
            print("\n=== RESPONSE HEADER ===")
            print(header_part.decode(errors="ignore"))
            print("\n=== RESPONSE BODY (maks 500 karakter) ===")
            print(body_part[:500].decode(errors="ignore"))
        else:
            print(response.decode(errors="ignore"))

    except socket.timeout:
        print("[ERROR] Koneksi timeout.")
    except ConnectionRefusedError:
        print(f"[ERROR] Proxy tidak bisa dihubungi di {PROXY_HOST}:{PROXY_PORT}.")
    except Exception as e:
        print(f"[ERROR] {e}")


# MODE 2: QoS UDP Ping
def udp_ping(count=UDP_PACKET_COUNT):
    """
    Kirim paket UDP ke server dan ukur RTT.
    Menampilkan statistik: Min/Avg/Max RTT, Packet Loss, Jitter.
    """
    print(f"\n[QoS] UDP Ping ke {SERVER_HOST}:{UDP_PORT} ({count} paket)")
    print("-" * 55)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(UDP_TIMEOUT)

    rtts = []
    lost = 0
    prev_rtt = None

    for seq in range(1, count + 1):
        timestamp = time.time()
        payload = f"Ping {seq} {timestamp}"

        try:
            s.sendto(payload.encode(), (SERVER_HOST, UDP_PORT))
            t_send = time.time()

            data, _ = s.recvfrom(1024)
            t_recv = time.time()

            rtt_ms = (t_recv - t_send) * 1000
            rtts.append(rtt_ms)
            print(f"Paket {seq:2d}: RTT = {rtt_ms:.2f} ms  | Payload: {data.decode(errors='ignore')[:30]}")
            prev_rtt = rtt_ms

        except socket.timeout:
            print(f"Paket {seq:2d}: Request timed out")
            lost += 1
            prev_rtt = None

        time.sleep(0.1)  # jeda antar paket

    s.close()


    # Statistik akhir
    print("\n" + "=" * 55)
    print("STATISTIK QoS")
    print("=" * 55)
    print(f"Paket dikirim  : {count}")
    print(f"Paket diterima : {count - lost}")
    print(f"Paket hilang   : {lost}")
    packet_loss_pct = (lost / count) * 100
    print(f"Packet Loss    : {packet_loss_pct:.1f}%")

    if rtts:
        min_rtt = min(rtts)
        avg_rtt = sum(rtts) / len(rtts)
        max_rtt = max(rtts)

        # Jitter = rata-rata selisih RTT berurutan
        jitter_vals = [abs(rtts[i] - rtts[i-1]) for i in range(1, len(rtts))]
        jitter = sum(jitter_vals) / len(jitter_vals) if jitter_vals else 0.0

        print(f"\nMin RTT : {min_rtt:.2f} ms")
        print(f"Avg RTT : {avg_rtt:.2f} ms")
        print(f"Max RTT : {max_rtt:.2f} ms")
        print(f"Jitter  : {jitter:.2f} ms")
    else:
        print("\n[!] Tidak ada paket yang berhasil diterima.")

    print("=" * 55)


# MAIN: Menu pilihan mode
def main():
    print("=" * 55)
    print("  CLIENT - Sistem Client-Proxy-Server")
    print("=" * 55)
    print("1. HTTP Request (melalui Proxy)")
    print("2. QoS UDP Ping (langsung ke Web Server)")
    print("3. Keduanya sekaligus")
    print("=" * 55)

    # Bisa juga dijalankan dengan argumen CLI:
    # python client.py http /index.html
    # python client.py udp 15
    if len(sys.argv) >= 2:
        mode = sys.argv[1].lower()
        if mode == "http":
            path = sys.argv[2] if len(sys.argv) >= 3 else "/"
            http_request(path)
        elif mode == "udp":
            count = int(sys.argv[2]) if len(sys.argv) >= 3 else UDP_PACKET_COUNT
            udp_ping(count)
        elif mode == "all":
            http_request("/")
            udp_ping()
        return

    # Mode interaktif
    choice = input("\nPilih mode [1/2/3]: ").strip()

    if choice == "1":
        path = input("Masukkan path URL (default /): ").strip() or "/"
        http_request(path)

    elif choice == "2":
        count_str = input(f"Jumlah paket (default {UDP_PACKET_COUNT}): ").strip()
        count = int(count_str) if count_str.isdigit() else UDP_PACKET_COUNT
        udp_ping(count)

    elif choice == "3":
        path = input("Path HTTP (default /): ").strip() or "/"
        count_str = input(f"Jumlah paket UDP (default {UDP_PACKET_COUNT}): ").strip()
        count = int(count_str) if count_str.isdigit() else UDP_PACKET_COUNT
        http_request(path)
        udp_ping(count)

    else:
        print("[!] Pilihan tidak valid.")

if __name__ == "__main__":
    main()