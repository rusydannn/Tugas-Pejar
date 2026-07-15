"""
config.py
Berisi konstanta konfigurasi untuk server & client.
Ubah nilai-nilai ini sesuai kebutuhan environment Kali Linux Anda.
"""

# Alamat & port server
HOST = '0.0.0.0'          # Server mendengarkan di semua interface
PORT = 5001                # Ganti jika port sudah dipakai proses lain

# Ukuran buffer untuk transfer data (byte)
BUFFER_SIZE = 4096

# Direktori penyimpanan file di sisi server
SERVER_DIR = 'server_files'

# File log aktivitas server
LOG_FILE = 'server.log'

# File penyimpanan kredensial user (username -> password hash)
USERS_FILE = 'users.json'

# Maksimal ukuran file yang boleh diupload (bytes) -> 200 MB
MAX_FILE_SIZE = 200 * 1024 * 1024
