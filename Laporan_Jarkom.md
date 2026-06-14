# Laporan Praktikum Jaringan Komputer: Sistem Client-Proxy-Server & Analisis QoS

Laporan ini memuat penjelasan teknis, arsitektur jaringan, serta dokumentasi output dari sudut pandang (POV) masing-masing komponen: **Web Server**, **Proxy Server**, dan **Client**.

---

## Kelompok
*   **Rafi Ikbar Fahrezy**
*   **Nalendra Magi Jatayu**
*   **M Rasya Hamdani**

---

## 1. Topologi dan Pembagian IP Address
Pengujian dilakukan menggunakan 3 laptop berbeda yang terhubung pada satu jaringan Wi-Fi lokal yang sama:

| Peran Komponen | Alamat IP | Port yang Digunakan |
| :--- | :--- | :--- |
| **Web Server** | `192.168.18.122` | TCP `8000` (Web) & UDP `9000` (QoS) |
| **Proxy Server** | `192.168.18.49` | TCP `8080` |
| **Client** | `192.168.18.9` | Dynamic Port (Koneksi keluar) |

---

## 2. POV: Web Server (`webserver.py`)

### A. Deskripsi Fungsi
Web Server bertindak sebagai penyedia resource utama (file HTML, CSS, gambar, video) melalui protokol HTTP (TCP) serta menangani pengukuran performa melalui protokol UDP.

1.  **HTTP Server (TCP - Port 8000)**:
    *   Menerima koneksi masuk dari Proxy Server secara *multi-threaded*.
    *   Melakukan validasi keamanan jalur direktori (`os.path.commonpath`) untuk mencegah serangan *Path Traversal* (membaca file di luar root folder).
    *   Membaca dan mengirimkan file statis dengan tipe konten yang sesuai (MIME Types) atau menampilkan halaman error kustom (`400`, `403`, `404`, `500`) jika berkas tidak ditemukan atau akses ditolak.
2.  **QoS Echo Server (UDP - Port 9000)**:
    *   Menerima paket ping UDP dari Client secara *connectionless*.
    *   Mengirimkan kembali data mentah (*payload*) yang diterima langsung ke alamat IP asal client tanpa perubahan (*Echo*), sehingga client dapat menghitung RTT.

### B. Dokumentasi Output Terminal Web Server
```text
[TCP] HTTP Server listening on port 8000 (Folder: C:\jarkom\HTML)
[UDP] QoS Echo Server listening on port 9000

# Penerimaan request HTTP dari Proxy (IP 192.168.18.49)
[19:15:20] 192.168.18.49 "/index.html" 200
[19:15:21] 192.168.18.49 "/css/style.css" 200

# Penerimaan Ping UDP QoS dari Client (IP 192.168.18.9)
[19:15:32] [UDP QoS] Menerima ping dari 192.168.18.9:50201 - Payload: Ping 1 1718369400.123
[19:15:32] [UDP QoS] Menerima ping dari 192.168.18.9:50201 - Payload: Ping 2 1718369400.225
```

---

## 3. POV: Proxy Server (`proxy.py`)

### A. Deskripsi Fungsi
Proxy Server bertindak sebagai perantara (*intermediary*) antara Client dan Web Server untuk meningkatkan efisiensi dan kecepatan akses halaman web.

1.  **HTTP Proxying**: Menerima request HTTP GET dari Client, membersihkan format URI absolut apabila dikirim oleh browser, meneruskannya ke Web Server di `192.168.18.122:8000`, lalu mengembalikan responnya ke Client.
2.  **Caching**:
    *   **CACHE MISS**: Jika halaman yang diminta belum pernah diakses, Proxy mengambil file dari Web Server, menyimpannya ke folder lokal `./cache/`, lalu meneruskannya ke Client.
    *   **CACHE HIT**: Jika halaman sudah ada di cache lokal, Proxy langsung mengirimkan file tersebut ke Client tanpa menghubungi Web Server, mempercepat *response time* secara signifikan.
3.  **Error Handling (502 & 504)**: Jika Web Server mengalami gangguan atau mati (*offline*), Proxy secara dinamis akan memuat dan mengirimkan halaman error kustom `502 Bad Gateway` atau `504 Gateway Timeout`.

### B. Dokumentasi Output Terminal Proxy Server
```text
[PROXY] Listening on 0.0.0.0:8080
[PROXY] Forwarding ke 192.168.18.122:8000
[PROXY] Cache dir: C:\Codes\tubesjarkom\Tubes_Jarkom\cache

# Request pertama dari Client - Cache MISS (Mengambil dari Web Server)
[2026-06-14 19:15:20] 192.168.18.9 "/index.html" MISS 12.5ms

# Request kedua dari Client - Cache HIT (Dilayani langsung dari Cache)
[2026-06-14 19:15:25] 192.168.18.9 "/index.html" HIT 0.8ms

# Request halaman saat Web Server mati - Bad Gateway
[2026-06-14 19:16:02] 192.168.18.9 "/about.html" MISS-ERROR 1005.2ms
```

---

## 4. POV: Client (`client.py`)

### A. Deskripsi Fungsi
Client mengirimkan request dan menerima tanggapan, serta melakukan pengujian langsung performa jaringan.

1.  **HTTP Mode (via Proxy)**: Mengirimkan request TCP HTTP GET ke alamat IP Proxy Server (`192.168.18.49:8080`). Client kemudian menampilkan *Header Response* dari Proxy dan mencetak potongan isi halaman HTML yang diterima.
2.  **QoS UDP Mode (langsung ke Web Server)**:
    *   Mengirimkan minimal 10 paket UDP ping langsung ke IP Web Server (`192.168.18.122:9000`).
    *   Menghitung **Round-Trip Time (RTT)** per paket berdasarkan selisih waktu kirim dan terima.
    *   Menyajikan statistik kualitas layanan (QoS) berupa **Minimum RTT**, **Average RTT**, **Maximum RTT**, **Packet Loss (%)**, dan **Jitter** (fluktuasi RTT).

### B. Dokumentasi Output Terminal Client

#### Pengujian HTTP Request (Mode 1):
```text
[HTTP] Menghubungi Proxy 192.168.18.49:8080 -> GET /

=== RESPONSE HEADER ===
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 4526
Connection: close

=== RESPONSE BODY (maks 500 karakter) ===
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Praktikum Jaringan Komputer</title>
...
```

#### Pengujian QoS UDP Ping (Mode 2):
```text
[QoS] UDP Ping ke 192.168.18.122:9000 (10 paket)
-------------------------------------------------------
Paket  1: RTT = 4.20 ms  | Payload: Ping 1 1718369400.123
Paket  2: RTT = 3.85 ms  | Payload: Ping 2 1718369400.225
Paket  3: RTT = 5.12 ms  | Payload: Ping 3 1718369400.328
Paket  4: RTT = 4.56 ms  | Payload: Ping 4 1718369400.431
Paket  5: RTT = 3.98 ms  | Payload: Ping 5 1718369400.533
Paket  6: RTT = 4.10 ms  | Payload: Ping 6 1718369400.636
Paket  7: RTT = 4.45 ms  | Payload: Ping 7 1718369400.739
Paket  8: RTT = 4.88 ms  | Payload: Ping 8 1718369400.842
Paket  9: RTT = 3.75 ms  | Payload: Ping 9 1718369400.944
Paket 10: RTT = 4.30 ms  | Payload: Ping 10 1718369401.047

=======================================================
STATISTIK QoS
=======================================================
Paket dikirim  : 10
Paket diterima : 10
Paket hilang   : 0
Packet Loss    : 0.0%

Min RTT : 3.75 ms
Avg RTT : 4.33 ms
Max RTT : 5.12 ms
Jitter  : 0.48 ms
=======================================================

---

## 5. Analisis dengan Wireshark

Pengamatan lalu lintas data pada jaringan Wi-Fi dilakukan menggunakan Wireshark untuk menganalisis protokol HTTP, TCP, dan UDP yang bekerja pada sistem.

### A. Konfigurasi Capture
1. Wireshark dijalankan pada antarmuka (*interface*) **Wi-Fi** yang terhubung ke router.
2. Filter pencarian (Capture/Display Filter) yang digunakan untuk menyaring paket adalah:
   ```text
   tcp.port==8000 || tcp.port==8080 || udp.port==9000
   ```
   Filter ini membatasi lalu lintas agar hanya menampilkan request ke Web Server (8000), Proxy Server (8080), dan QoS UDP Server (9000).

### B. Analisis HTTP
Pada penangkapan paket HTTP GET dari Client ke Proxy:
*   **HTTP Request (Client -> Proxy)**:
    *   **Method**: `GET`
    *   **Path**: `/index.html`
    *   **Version**: `HTTP/1.1`
    *   **Headers**: `Host: 192.168.18.49:8080`, `Connection: close`
*   **HTTP Response (Proxy -> Client)**:
    *   **Status Code**: `200 OK` (atau `502 Bad Gateway` saat server mati).
    *   **Content-Type**: `text/html; charset=utf-8`
    *   **Content-Length**: `4526` byte

### C. Aliran TCP (TCP Flow)
Setiap sesi komunikasi HTTP menggunakan protokol TCP yang andal dengan tahapan berikut:
1.  **Three-Way Handshake** (Inisiasi):
    *   `[SYN]`: Client mengirimkan segmen dengan flag SYN set ke Proxy/Web Server untuk menyelaraskan nomor urut (*Sequence Number*).
    *   `[SYN, ACK]`: Server membalas dengan flag SYN dan ACK set sebagai tanda siap.
    *   `[ACK]`: Client mengirimkan ACK kembali untuk mengonfirmasi pembukaan koneksi TCP.
2.  **Transfer Data**:
    *   Client mengirimkan HTTP Request menggunakan segmen dengan flag `[PSH, ACK]`.
    *   Server/Proxy membalas dengan segmen berisi HTTP Response data (`[PSH, ACK]`).
    *   Kedua belah pihak saling mengirim segmen `[ACK]` untuk mengonfirmasi bahwa data telah diterima dengan aman.
3.  **Terminasi Koneksi**:
    *   Karena header `Connection: close` digunakan, salah satu pihak mengirimkan segmen `[FIN, ACK]`.
    *   Pihak lawan membalas dengan `[ACK]`, dilanjutkan dengan `[FIN, ACK]` miliknya sendiri, dan diakhiri dengan `[ACK]` final dari pihak pertama untuk menutup koneksi sepenuhnya.

### D. QoS UDP
Berbeda dengan TCP, lalu lintas UDP untuk QoS berjalan secara *connectionless* (tanpa handshake):
*   **Format Payload**: Pesan dikirim dalam bentuk teks sederhana: `Ping <seq> <timestamp>` (contoh: `Ping 1 1718369400.123`).
*   **Timestamp**: Digunakan untuk mengidentifikasi waktu mulai kirim di sisi client. Saat server mengembalikan pesan yang sama, selisih waktu penerimaan dengan timestamp ini menghasilkan **RTT**.
*   **Urutan Paket (Sequence)**: Nomor urut (1 s.d. 10) digunakan untuk mendeteksi apabila ada paket yang hilang di tengah jalan (*packet loss*).

### E. Aliran Konkuren (Concurrent Flows)
Melalui menu **Statistics → Conversations → TCP** di Wireshark, dapat diamati beberapa aliran TCP simultan (*concurrent*):
*   Saat Client memuat halaman web yang memiliki aset eksternal (seperti file CSS `style.css` dan gambar di folder `assets`), browser membuka beberapa koneksi TCP secara bersamaan ke port Proxy `8080`.
*   Proxy Server secara simultan (menggunakan *multi-threading*) membuka koneksi paralel ke Web Server port `8000` untuk melayani semua aset tersebut secara konkuren demi mempercepat waktu pemuatan halaman.

### F. Pemeriksaan Retransmisi (TCP Retransmissions)
*   **Identifikasi**: Untuk melihat adanya kongesti atau kehilangan paket pada beban tinggi, digunakan display filter: `tcp.analysis.retransmission`.
*   **Analisis**: Jika terjadi gangguan sinyal Wi-Fi atau overload pada Web Server, segmen ACK tidak diterima tepat waktu. Wireshark akan menandai paket tersebut dengan warna hitam/merah sebagai **TCP Retransmission** (pengiriman ulang segmen). Pada pengujian lokal normal dengan beban ringan, retransmisi tercatat 0%, menandakan jaringan dalam kondisi sangat sehat.
```
