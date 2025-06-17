import string
from hashlib import md5
from Crypto.Hash import Poly1305
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

import os

def sign_token(token):
    try:
        key = os.environ.get('TOKEN_KEY', 'AAAAAAAAAAAAAAAA')
        auth_nonce = os.urandom(16)

        if isinstance(key, str):
            key = key.encode()
        
        if isinstance(token, str):
            token = token.encode()
        
        if len(key) != 16:
            return None

        cipher = AES.new(key, AES.MODE_CBC)
        enc_token = cipher.encrypt(pad(token, 16))
        tag = Poly1305.Poly1305_MAC(key, auth_nonce, md5(enc_token).digest()).hexdigest()

        return cipher.iv.hex() + enc_token.hex() + auth_nonce.hex() + tag
    except:
        return None
    
def verify_token(enc_token):
    try:
        key = os.environ.get('TOKEN_KEY', 'AAAAAAAAAAAAAAAA')

        if isinstance(key, str):
            key = key.encode()
        
        if len(key) != 16:
            return None

        iv = bytes.fromhex(enc_token[:32])
        token = bytes.fromhex(enc_token[32:-64])
        auth_nonce = bytes.fromhex(enc_token[-64:-32])
        tag = enc_token[-32:]

        new_tag = Poly1305.Poly1305_MAC(key, auth_nonce, md5(token).digest()).hexdigest()

        if tag != new_tag:
            return False
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        dec_token = cipher.decrypt(token)

        return unpad(dec_token,16).decode()
    except:
        return False