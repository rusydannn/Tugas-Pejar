# Aplikasi File Transfer Client-Server (Python Socket) — Kali Linux

Aplikasi layanan jaringan sederhana untuk **mengirim dan menerima file** antara
client dan server menggunakan **TCP Socket** dengan bahasa **Python 3**,
dibangun dari nol (bukan modifikasi tool pihak ketiga) agar mudah dijelaskan
konsep dan alur kerjanya saat sidang tugas akhir mata kuliah Pemrograman
Jaringan.

---

## 1. Fitur Aplikasi

| Fitur | Keterangan |
|---|---|
| Multi-client | Server menangani banyak client sekaligus dengan `threading` |
| Autentikasi | Login username/password, password disimpan ter-hash (SHA-256 + salt) |
| Upload | Client mengirim file ke server |
| Download | Client mengambil file dari server |
| List | Menampilkan daftar file yang ada di server |
| Delete | Menghapus file di server |
| Verifikasi integritas | Checksum SHA-256 dihitung & dicocokkan setelah transfer |
| Progress bar | Progres upload/download ditampilkan real-time di terminal |
| Logging | Semua aktivitas server (login, upload, download, error) dicatat ke `server.log` |
| Anti path-traversal | Nama file disanitasi agar client tidak bisa mengakses folder lain (`../../etc/passwd`) |
| Batas ukuran file | Mencegah upload file yang terlalu besar |

**Zero-dependency**: hanya menggunakan Python Standard Library (`socket`,
`threading`, `json`, `hashlib`, `struct`, `logging`, `getpass`), sehingga
tidak perlu `pip install` apa pun di Kali Linux.

---

## 2. Arsitektur & Struktur Proyek

```
file_transfer_app/
├── config.py          # Konstanta (HOST, PORT, BUFFER_SIZE, dll)
├── auth.py             # Autentikasi user (hash password + salt)
├── protocol.py          # Definisi protokol komunikasi (dipakai server & client)
├── server.py            # Server multi-client
├── client.py             # Client CLI interaktif
├── setup_user.py          # Script membuat akun sebelum server dijalankan
├── requirements.txt
├── server_files/          # Tempat penyimpanan file di server (dibuat otomatis)
└── README.md
```

### 2.1 Desain Protokol Aplikasi

Karena TCP adalah *stream protocol* (tidak mengenal batas pesan), aplikasi
ini mendefinisikan protokol sendiri di atas TCP dengan skema
**length-prefixed JSON header**, diikuti data biner bila diperlukan:

```
[4 byte panjang header (big-endian)] [header JSON] [payload file biner (opsional)]
```

Contoh header untuk perintah upload:
```json
{"cmd": "UPLOAD", "filename": "laporan.pdf", "filesize": 204800, "checksum": "a1b2c3..."}
```

Alur perintah yang didukung: `LOGIN`, `LIST`, `UPLOAD`, `DOWNLOAD`, `DELETE`, `EXIT`.

### 2.2 Diagram Alur Upload (untuk laporan/sidang)

```
CLIENT                                   SERVER
  |-- LOGIN (user, pass) ---------------->|
  |<------------- status: OK -------------|
  |                                       |
  |-- UPLOAD (filename, size, checksum)-->|
  |<---------- status: OK (siap) ---------|
  |-- [stream byte file] ---------------->|
  |                                       | (simpan file, hitung checksum)
  |<-- status: OK (checksum cocok) -------|
```

### 2.3 Diagram Alur Download

```
CLIENT                                   SERVER
  |-- DOWNLOAD (filename) --------------->|
  |<-- status: OK (filesize, checksum) ---|
  |<--------- [stream byte file] ---------|
  | (hitung ulang checksum lokal, bandingkan)
```

---

## 3. Tahapan Instalasi & Menjalankan di Kali Linux

### Langkah 1 — Pastikan Python 3 terpasang
Kali Linux sudah menyertakan Python 3 secara default. Cek versinya:
```bash
python3 --version
```
Disarankan Python 3.10 ke atas.

### Langkah 2 — Salin/ekstrak folder proyek
```bash
cd ~/
# salin folder file_transfer_app ke sini, lalu:
cd file_transfer_app
```

### Langkah 3 — Buat akun user (dijalankan sekali di sisi server)
```bash
python3 setup_user.py
```
Ikuti prompt untuk membuat username & password (contoh: `mate` / `password123`).
Kredensial akan disimpan ter-hash di `users.json` (dibuat otomatis).

### Langkah 4 — Jalankan server
```bash
python3 server.py
```
Output yang diharapkan:
```
2026-07-09 13:44:09 [INFO] Server berjalan di 0.0.0.0:5001, direktori penyimpanan: server_files/
2026-07-09 13:44:09 [INFO] Menunggu koneksi client...
```
Biarkan terminal ini tetap berjalan (server harus aktif selama pengujian).

### Langkah 5 — Jalankan client (di terminal/mesin lain)
Buka terminal baru (atau mesin/VM Kali Linux kedua bila ingin simulasi
jaringan sungguhan), lalu:
```bash
cd file_transfer_app
python3 client.py
```
Masukkan:
- **Alamat IP server** — `127.0.0.1` jika satu mesin, atau IP LAN server bila dua mesin/VM berbeda (cek dengan `ip a` di sisi server)
- **Port** — default `5001`
- **Username / Password** — sesuai akun yang dibuat di Langkah 3

### Langkah 6 — Gunakan menu interaktif
```
1. Lihat daftar file di server (LIST)
2. Upload file
3. Download file
4. Hapus file di server
5. Keluar
```

---

## 4. Skenario Pengujian untuk Laporan Sidang

Berikut skenario pengujian yang disarankan dimasukkan ke bab pengujian (BAB IV):

1. **Uji fungsional dasar**: upload file kecil (txt), verifikasi muncul di `LIST`, download kembali, bandingkan checksum awal vs akhir → harus identik.
2. **Uji file besar**: upload file berukuran puluhan/ratusan MB, amati progress bar & waktu transfer, hitung throughput (MB/s).
3. **Uji multi-client**: buka 2–3 terminal client sekaligus, upload/download bersamaan, buktikan server tetap responsif (bukti kerja `threading`).
4. **Uji autentikasi gagal**: masukkan password salah → koneksi ditolak, tercatat di `server.log`.
5. **Uji keamanan path traversal**: coba nama file `../../etc/passwd` saat upload/download → server menolak/menyimpan hanya di `server_files/`.
6. **Uji koneksi terputus**: matikan client di tengah transfer (Ctrl+C) → server mendeteksi file tidak lengkap dan menghapusnya otomatis.
7. **Uji dengan Wireshark** *(opsional, nilai tambah)*: capture trafik di loopback/`eth0` port `5001` saat transfer berlangsung, tunjukkan paket TCP handshake, data payload, dan analisis ukuran paket — bagus untuk bab analisis di laporan.
   ```bash
   sudo wireshark &
   # filter: tcp.port == 5001
   ```
8. **Uji log audit**: tunjukkan isi `server.log` sebagai bukti seluruh aktivitas (login, upload, download, delete, error) tercatat dengan timestamp.

---

## 5. Kustomisasi Cepat

| Kebutuhan | File | Perubahan |
|---|---|---|
| Ganti port | `config.py` | `PORT = 5001` |
| Batas ukuran upload | `config.py` | `MAX_FILE_SIZE` |
| Lokasi penyimpanan server | `config.py` | `SERVER_DIR` |
| Tambah user baru | jalankan ulang `setup_user.py` | — |

---

## 6. Pengembangan Lanjutan (opsional, untuk nilai tambah di sidang)

Jika ingin menaikkan bobot proyek, beberapa fitur lanjutan yang bisa
ditambahkan dan dijelaskan sebagai *future work*:
- **Enkripsi transport** dengan `ssl.wrap_socket` (TLS) agar data terenkripsi selama pengiriman, tidak hanya autentikasi.
- **GUI** menggunakan `tkinter` atau versi web dengan `Flask` + `Streamlit`.
- **Resume transfer** (melanjutkan upload/download yang terputus, bukan mengulang dari awal).
- **Kompresi file** sebelum transfer (`zlib`) untuk menghemat bandwidth.
- **Role-based access** (admin vs user biasa) pada `auth.py`.

---

## 7. Troubleshooting

| Masalah | Penyebab Umum | Solusi |
|---|---|---|
| `Connection refused` | Server belum dijalankan / port salah | Pastikan `server.py` aktif dan port sama di client |
| `Address already in use` | Port 5001 masih dipakai proses sebelumnya | `sudo lsof -i :5001` lalu `kill <PID>`, atau ganti `PORT` di `config.py` |
| Tidak bisa connect dari mesin lain | Firewall Kali (`ufw`) memblokir | `sudo ufw allow 5001/tcp` |
| Login selalu gagal | Belum menjalankan `setup_user.py` | Jalankan `python3 setup_user.py` di sisi server terlebih dahulu |

---

Selamat mengerjakan tugas akhir — semoga sidangnya lancar! 🎓
