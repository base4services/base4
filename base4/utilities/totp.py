# auth/totp.py

import pyotp
import base64
import os

def generate_totp_secret() -> str:
    """
    Kreira random tajnu za TOTP koju treba čuvati vezanu uz korisnika u bazi.
    """
    # Najčešće se čuva u bazi za konkretnog korisnika
    secret = base64.b32encode(os.urandom(10)).decode("utf-8")
    return secret

def get_totp_uri(secret: str, email: str, issuer_name="MyFastAPIApp") -> str:
    """
    Generiše URI koji se može skenirati QR kodom u Google Authenticatoru.
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer_name)

def verify_totp_token(secret: str, token: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(token)
