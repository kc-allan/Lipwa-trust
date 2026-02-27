from datetime import datetime, timedelta
from typing import Optional
import hashlib

from passlib.context import CryptContext
from jose import jwt, JWTError, ExpiredSignatureError

from core.config import settings
import bcrypt


# ----------------------------
# Password Hashing
# ----------------------------

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def _pre_hash_password(password: str) -> str:
    """
    Pre-hash password using SHA256 to avoid bcrypt's 72-byte limit.
    Ensures consistent fixed-length input to bcrypt.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ----------------------------
# JWT Configuration
# ----------------------------

ALGORITHM = "HS256"  # Correct JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except ExpiredSignatureError:
        return None
    except JWTError:
        return None
