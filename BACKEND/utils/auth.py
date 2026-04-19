import bcrypt
import jwt
from datetime import datetime, timedelta


SECRET = "SECRET_KEY"


def hash_password(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw, hashed):
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def create_token(email):
    payload = {
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def decode_token(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])
