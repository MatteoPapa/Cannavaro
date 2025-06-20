import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.kbkdf import (CounterLocation, KBKDFHMAC, Mode)

from models import Worksheet


def derive_key(worksheet: Worksheet) -> bytes:
    kdf = KBKDFHMAC(
        algorithm=hashes.MD5(),
        mode=Mode.CounterMode,
        length=32, rlen=4, llen=4,
        location=CounterLocation.BeforeFixed,
        label=None, context=None, fixed=None
    )
    return kdf.derive(bytes.fromhex(worksheet.private_id))


def verify_invite_token(worksheet: Worksheet, token: str) -> bool:
    f = Fernet(base64.urlsafe_b64encode(derive_key(worksheet)))

    try:
        return f.decrypt(token.encode()).hex() == worksheet.public_id
    except:
        return False


def generate_invite_token(worksheet: Worksheet) -> str:
    f = Fernet(base64.urlsafe_b64encode(derive_key(worksheet)))
    return f.encrypt(bytes.fromhex(worksheet.public_id)).decode()
