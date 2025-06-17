from hashlib import md5
from Crypto.Hash import Poly1305
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

import os

# DO NOT TOUCH IF YOU LIKE SLA
p = 0x80000000000001cda6f403d8a752a4e7976173ebfcd2acf69a29f4bada1ca3178b56131c2c1f00cf7875a2e7c497b10fea66b26436e40b7b73952081319e26603810a558f871d6d256fddbec5933b77fa7d1d0d75267dcae1f24ea7cc57b3a30f8ea09310772440f016c13e08b56b1196a687d6a5e5de864068f3fd936a361c5

def verify_pow(prefix, target, value):
    if isinstance(value, str):
        value = value.encode()

    if isinstance(prefix, str):
        prefix = prefix.encode()

    h = md5(value).hexdigest()
    return value.startswith(prefix) and h.startswith(target)

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