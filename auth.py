"""
auth.py
Modul autentikasi sederhana berbasis file JSON.
Password TIDAK disimpan dalam bentuk plaintext, melainkan di-hash
menggunakan SHA-256 + salt acak per-user (agar tugas akhir mudah
dijelaskan konsep keamanannya saat sidang).
"""

import hashlib
import json
import os
import secrets

from config import USERS_FILE


def _hash_password(password: str, salt: str) -> str:
    """Hash password menggunakan SHA-256 dengan salt."""
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()


def load_users() -> dict:
    """Memuat data user dari file JSON. Jika belum ada, buat file kosong."""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)


def save_users(users: dict) -> None:
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)


def add_user(username: str, password: str) -> bool:
    """Menambahkan user baru. Mengembalikan False jika username sudah ada."""
    users = load_users()
    if username in users:
        return False
    salt = secrets.token_hex(8)
    users[username] = {
        'salt': salt,
        'hash': _hash_password(password, salt)
    }
    save_users(users)
    return True


def verify_user(username: str, password: str) -> bool:
    """Memverifikasi kombinasi username & password."""
    users = load_users()
    if username not in users:
        return False
    record = users[username]
    return _hash_password(password, record['salt']) == record['hash']
