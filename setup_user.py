"""
setup_user.py
Script bantuan untuk membuat akun user (username/password) sebelum
server dijalankan. Password akan disimpan dalam bentuk hash (bukan plaintext)
di dalam users.json.

Jalankan:
    python3 setup_user.py
"""

import getpass

from auth import add_user


def main():
    print('=== Setup Akun User File Transfer Server ===')
    while True:
        username = input('Username baru: ').strip()
        if not username:
            print('Username tidak boleh kosong.')
            continue

        password = getpass.getpass('Password: ')
        password2 = getpass.getpass('Ulangi password: ')

        if password != password2:
            print('Password tidak sama, coba lagi.\n')
            continue

        if add_user(username, password):
            print(f'User "{username}" berhasil dibuat.\n')
        else:
            print(f'User "{username}" sudah ada, gunakan username lain.\n')

        lanjut = input('Tambah user lain? (y/n): ').strip().lower()
        if lanjut != 'y':
            break

    print('Setup selesai. Anda bisa menjalankan server dengan: python3 server.py')


if __name__ == '__main__':
    main()
