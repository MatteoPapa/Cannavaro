import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def derive_key(passwd: str) -> bytes:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(passwd.encode())
    return digest.finalize()


def generate_login_token(passwd: str, timestamp: int) -> tuple[bytes, bytes]:
    nonce = os.urandom(24)
    data = nonce + timestamp.to_bytes(8, 'little')

    iv = os.urandom(16)
    encryptor = Cipher(algorithms.AES256(derive_key(passwd)), modes.CBC(iv)).encryptor()
    ct = encryptor.update(data) + encryptor.finalize()
    return nonce, iv + ct


def verify_login_token(passwd: str, timestamp: int, token: bytes, nonce: bytes):
    decryptor = Cipher(algorithms.AES256(derive_key(passwd)), modes.CBC(token[:16])).decryptor()
    data = decryptor.update(token[16:]) + decryptor.finalize()

    return data[:24] == nonce and data[24:32] == timestamp.to_bytes(8, 'little')
