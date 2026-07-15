"""
protocol.py
Mendefinisikan protokol aplikasi di atas TCP socket:

  [4 byte panjang header]-[header JSON]-[payload biner opsional]

Header JSON berisi command & metadata (nama file, ukuran, checksum, dsb).
Payload biner (jika ada) dikirim langsung setelah header, sebesar
'filesize' byte, dalam potongan (chunk) sebesar BUFFER_SIZE.

Dipisah jadi modul sendiri supaya server.py & client.py bisa memakai
fungsi yang SAMA PERSIS -> menghindari bug ketidaksesuaian protokol.
"""

import hashlib
import json
import os
import struct


def send_json(sock, data: dict) -> None:
    """Mengirim dict sebagai JSON dengan length-prefix 4 byte (big-endian)."""
    payload = json.dumps(data).encode('utf-8')
    header = struct.pack('>I', len(payload))
    sock.sendall(header + payload)


def recv_exact(sock, n: int) -> bytes | None:
    """Menerima tepat n byte dari socket, atau None jika koneksi terputus."""
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def recv_json(sock) -> dict | None:
    """Menerima satu pesan JSON sesuai format length-prefixed."""
    header = recv_exact(sock, 4)
    if header is None:
        return None
    length = struct.unpack('>I', header)[0]
    payload = recv_exact(sock, length)
    if payload is None:
        return None
    return json.loads(payload.decode('utf-8'))


def sha256_of_file(filepath: str, buffer_size: int = 65536) -> str:
    """Menghitung checksum SHA-256 dari sebuah file (untuk verifikasi integritas)."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(buffer_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def send_file_bytes(sock, filepath: str, buffer_size: int, progress_cb=None) -> int:
    """Mengirim isi file secara streaming. Mengembalikan jumlah byte terkirim."""
    filesize = os.path.getsize(filepath)
    sent = 0
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(buffer_size)
            if not chunk:
                break
            sock.sendall(chunk)
            sent += len(chunk)
            if progress_cb:
                progress_cb(sent, filesize)
    return sent


def recv_file_bytes(sock, dest_path: str, filesize: int, buffer_size: int, progress_cb=None) -> int:
    """Menerima isi file secara streaming sejumlah 'filesize' byte, ditulis ke dest_path."""
    received = 0
    with open(dest_path, 'wb') as f:
        while received < filesize:
            to_read = min(buffer_size, filesize - received)
            chunk = sock.recv(to_read)
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)
            if progress_cb:
                progress_cb(received, filesize)
    return received


def print_progress(current: int, total: int, prefix: str = 'Progress') -> None:
    """Menampilkan progress bar sederhana di terminal (tanpa dependency eksternal)."""
    if total <= 0:
        return
    percent = current / total * 100
    bar_len = 30
    filled = int(bar_len * current // total)
    bar = '#' * filled + '-' * (bar_len - filled)
    end = '\n' if current >= total else ''
    print(f'\r{prefix}: |{bar}| {percent:6.2f}% ({current}/{total} bytes)', end=end, flush=True)
