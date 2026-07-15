"""
client.py
Client aplikasi File Transfer berbasis CLI (menu interaktif).

Jalankan:
    python3 client.py
"""

import getpass
import os
import socket
import sys

from config import BUFFER_SIZE, PORT
from protocol import (
    print_progress,
    recv_file_bytes,
    recv_json,
    send_file_bytes,
    send_json,
    sha256_of_file,
)

DOWNLOAD_DIR = 'downloads'


def connect(host: str, port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    return sock


def login(sock) -> bool:
    username = input('Username: ').strip()
    password = getpass.getpass('Password: ')
    send_json(sock, {'cmd': 'LOGIN', 'username': username, 'password': password})
    resp = recv_json(sock)
    if resp is None:
        print('Server tidak merespons.')
        return False
    print(f"[{resp['status']}] {resp['message']}")
    return resp['status'] == 'OK'


def cmd_list(sock):
    send_json(sock, {'cmd': 'LIST'})
    resp = recv_json(sock)
    if resp['status'] != 'OK':
        print(f"Gagal: {resp['message']}")
        return
    files = resp['files']
    if not files:
        print('(Belum ada file di server)')
        return
    print(f"{'Nama File':40} {'Ukuran (bytes)':>15}")
    print('-' * 56)
    for f in files:
        print(f"{f['name']:40} {f['size']:>15}")


def cmd_upload(sock):
    path = input('Path file yang ingin diupload: ').strip()
    if not os.path.isfile(path):
        print('File tidak ditemukan di lokal.')
        return

    filename = os.path.basename(path)
    filesize = os.path.getsize(path)
    checksum = sha256_of_file(path)

    send_json(sock, {'cmd': 'UPLOAD', 'filename': filename, 'filesize': filesize, 'checksum': checksum})
    resp = recv_json(sock)
    if resp['status'] != 'OK':
        print(f"Server menolak: {resp['message']}")
        return

    def progress(cur, total):
        print_progress(cur, total, prefix=f'  Upload {filename}')

    send_file_bytes(sock, path, BUFFER_SIZE, progress_cb=progress)

    result = recv_json(sock)
    print(f"[{result['status']}] {result['message']}")


def cmd_download(sock):
    filename = input('Nama file di server yang ingin diunduh: ').strip()
    send_json(sock, {'cmd': 'DOWNLOAD', 'filename': filename})
    resp = recv_json(sock)
    if resp['status'] != 'OK':
        print(f"Gagal: {resp['message']}")
        return

    filesize = resp['filesize']
    expected_checksum = resp['checksum']

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    dest = os.path.join(DOWNLOAD_DIR, filename)

    def progress(cur, total):
        print_progress(cur, total, prefix=f'  Download {filename}')

    received = recv_file_bytes(sock, dest, filesize, BUFFER_SIZE, progress_cb=progress)

    if received != filesize:
        print('Transfer tidak lengkap!')
        return

    actual_checksum = sha256_of_file(dest)
    if actual_checksum == expected_checksum:
        print(f'Download selesai & terverifikasi -> {dest}')
    else:
        print('PERINGATAN: checksum tidak cocok, file mungkin rusak!')


def cmd_delete(sock):
    filename = input('Nama file di server yang ingin dihapus: ').strip()
    send_json(sock, {'cmd': 'DELETE', 'filename': filename})
    resp = recv_json(sock)
    print(f"[{resp['status']}] {resp['message']}")


def print_menu():
    print('''
========= MENU FILE TRANSFER =========
1. Lihat daftar file di server (LIST)
2. Upload file                  (UPLOAD)
3. Download file                (DOWNLOAD)
4. Hapus file di server         (DELETE)
5. Keluar                       (EXIT)
=======================================''')


def main():
    host = input(f'Alamat IP server [default: 127.0.0.1]: ').strip() or '127.0.0.1'
    port_input = input(f'Port server [default: {PORT}]: ').strip()
    port = int(port_input) if port_input else PORT

    try:
        sock = connect(host, port)
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        print(f'Tidak dapat terhubung ke {host}:{port} -> {e}')
        sys.exit(1)

    print(f'Terhubung ke server {host}:{port}')

    if not login(sock):
        sock.close()
        sys.exit(1)

    try:
        while True:
            print_menu()
            choice = input('Pilih menu: ').strip()

            if choice == '1':
                cmd_list(sock)
            elif choice == '2':
                cmd_upload(sock)
            elif choice == '3':
                cmd_download(sock)
            elif choice == '4':
                cmd_delete(sock)
            elif choice == '5':
                send_json(sock, {'cmd': 'EXIT'})
                resp = recv_json(sock)
                print(f"[{resp['status']}] {resp['message']}")
                break
            else:
                print('Pilihan tidak valid.')
    except KeyboardInterrupt:
        print('\nDitutup oleh pengguna.')
    finally:
        sock.close()


if __name__ == '__main__':
    main()
