from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings


class SecurityManager:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key using bcrypt"""
        salt = bcrypt.gensalt(rounds=settings.api_key_hash_rounds)
        return bcrypt.hashpw(api_key.encode('utf-8'), salt).decode('utf-8')
    
    def verify_api_key(self, plain_api_key: str, hashed_api_key: str) -> bool:
        """Verify API key against hash"""
        return bcrypt.checkpw(
            plain_api_key.encode('utf-8'),
            hashed_api_key.encode('utf-8')
        )
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[dict]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None


security_manager = SecurityManager()