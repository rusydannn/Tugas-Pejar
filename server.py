"""
server.py
Server aplikasi File Transfer.

Fitur:
  - Menangani banyak client sekaligus (multi-threading)
  - Autentikasi username/password (auth.py)
  - Perintah: LOGIN, LIST, UPLOAD, DOWNLOAD, DELETE, EXIT
  - Verifikasi integritas file dengan checksum SHA-256
  - Logging seluruh aktivitas ke file server.log dan ke terminal

Jalankan:
    python3 server.py
"""

import logging
import os
import socket
import threading

from auth import verify_user
from config import BUFFER_SIZE, HOST, LOG_FILE, MAX_FILE_SIZE, PORT, SERVER_DIR
from protocol import (
    print_progress,
    recv_file_bytes,
    recv_json,
    send_json,
    sha256_of_file,
)

# ---------- Setup logging ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FileTransferServer')

os.makedirs(SERVER_DIR, exist_ok=True)


def safe_path(filename: str) -> str:
    """
    Mencegah path traversal (mis. '../../etc/passwd').
    Hanya mengambil nama file dasarnya saja lalu menggabungkan
    dengan direktori server yang sudah ditentukan.
    """
    base = os.path.basename(filename)
    return os.path.join(SERVER_DIR, base)


def handle_login(conn) -> str | None:
    """Menangani proses autentikasi. Mengembalikan username jika sukses, None jika gagal."""
    msg = recv_json(conn)
    if not msg or msg.get('cmd') != 'LOGIN':
        send_json(conn, {'status': 'ERROR', 'message': 'Harus LOGIN terlebih dahulu'})
        return None

    username = msg.get('username', '')
    password = msg.get('password', '')

    if verify_user(username, password):
        send_json(conn, {'status': 'OK', 'message': f'Selamat datang, {username}!'})
        return username
    else:
        send_json(conn, {'status': 'ERROR', 'message': 'Username atau password salah'})
        return None


def handle_list(conn):
    files = []
    for fname in os.listdir(SERVER_DIR):
        fpath = os.path.join(SERVER_DIR, fname)
        if os.path.isfile(fpath):
            files.append({'name': fname, 'size': os.path.getsize(fpath)})
    send_json(conn, {'status': 'OK', 'files': files})


def handle_upload(conn, msg, addr, username):
    filename = msg.get('filename')
    filesize = msg.get('filesize', 0)
    client_checksum = msg.get('checksum')

    if not filename or filesize <= 0:
        send_json(conn, {'status': 'ERROR', 'message': 'Metadata file tidak valid'})
        return

    if filesize > MAX_FILE_SIZE:
        send_json(conn, {'status': 'ERROR', 'message': 'Ukuran file melebihi batas maksimum'})
        return

    dest = safe_path(filename)
    send_json(conn, {'status': 'OK', 'message': 'Siap menerima file'})

    logger.info(f'[{addr}] user={username} mulai UPLOAD "{filename}" ({filesize} bytes)')

    def progress(cur, total):
        print_progress(cur, total, prefix=f'  Menerima {filename}')

    received = recv_file_bytes(conn, dest, filesize, BUFFER_SIZE, progress_cb=progress)

    if received != filesize:
        send_json(conn, {'status': 'ERROR', 'message': 'Transfer terputus / tidak lengkap'})
        logger.warning(f'[{addr}] UPLOAD "{filename}" gagal: hanya {received}/{filesize} bytes')
        os.remove(dest)
        return

    server_checksum = sha256_of_file(dest)
    if client_checksum and server_checksum != client_checksum:
        send_json(conn, {'status': 'ERROR', 'message': 'Checksum tidak cocok, file rusak'})
        logger.warning(f'[{addr}] UPLOAD "{filename}" checksum mismatch')
        os.remove(dest)
        return

    send_json(conn, {'status': 'OK', 'message': 'Upload berhasil & terverifikasi', 'checksum': server_checksum})
    logger.info(f'[{addr}] user={username} UPLOAD "{filename}" SUKSES (checksum OK)')


def handle_download(conn, msg, addr, username):
    filename = msg.get('filename')
    src = safe_path(filename) if filename else None

    if not filename or not os.path.isfile(src):
        send_json(conn, {'status': 'ERROR', 'message': 'File tidak ditemukan di server'})
        return

    filesize = os.path.getsize(src)
    checksum = sha256_of_file(src)
    send_json(conn, {'status': 'OK', 'filesize': filesize, 'checksum': checksum})

    logger.info(f'[{addr}] user={username} mulai DOWNLOAD "{filename}" ({filesize} bytes)')

    from protocol import send_file_bytes

    def progress(cur, total):
        print_progress(cur, total, prefix=f'  Mengirim {filename}')

    send_file_bytes(conn, src, BUFFER_SIZE, progress_cb=progress)
    logger.info(f'[{addr}] user={username} DOWNLOAD "{filename}" SELESAI')


def handle_delete(conn, msg, addr, username):
    filename = msg.get('filename')
    target = safe_path(filename) if filename else None

    if not filename or not os.path.isfile(target):
        send_json(conn, {'status': 'ERROR', 'message': 'File tidak ditemukan'})
        return

    os.remove(target)
    send_json(conn, {'status': 'OK', 'message': 'File berhasil dihapus'})
    logger.info(f'[{addr}] user={username} DELETE "{filename}"')


def client_thread(conn, addr):
    logger.info(f'Koneksi baru dari {addr}')
    try:
        username = handle_login(conn)
        if not username:
            logger.warning(f'[{addr}] Autentikasi gagal, koneksi ditutup')
            return

        while True:
            msg = recv_json(conn)
            if msg is None:
                break

            cmd = msg.get('cmd')
            if cmd == 'LIST':
                handle_list(conn)
            elif cmd == 'UPLOAD':
                handle_upload(conn, msg, addr, username)
            elif cmd == 'DOWNLOAD':
                handle_download(conn, msg, addr, username)
            elif cmd == 'DELETE':
                handle_delete(conn, msg, addr, username)
            elif cmd == 'EXIT':
                send_json(conn, {'status': 'OK', 'message': 'Bye'})
                break
            else:
                send_json(conn, {'status': 'ERROR', 'message': f'Command tidak dikenali: {cmd}'})

    except (ConnectionResetError, BrokenPipeError):
        logger.warning(f'[{addr}] Koneksi terputus tiba-tiba')
    except Exception as e:
        logger.exception(f'[{addr}] Error tak terduga: {e}')
    finally:
        conn.close()
        logger.info(f'Koneksi dengan {addr} ditutup')


def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(5)
    logger.info(f'Server berjalan di {HOST}:{PORT}, direktori penyimpanan: {SERVER_DIR}/')
    logger.info('Menunggu koneksi client... (Ctrl+C untuk berhenti)')

    try:
        while True:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=client_thread, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        logger.info('Server dihentikan oleh operator (Ctrl+C)')
    finally:
        server_sock.close()


if __name__ == '__main__':
    main()
