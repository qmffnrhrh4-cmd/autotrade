"""
Security Module v6.0
API 키 암호화, 환경변수 검증
"""

import os
from pathlib import Path
import base64
import logging

logger = logging.getLogger(__name__)

# Cryptography 사용 가능 여부
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography not installed - encryption disabled")


class SecureKeyManager:
    """
    보안 키 관리자

    Features:
    - API 키 암호화 저장
    - 환경변수 검증
    - 안전한 키 로드/저장
    """

    def __init__(self, master_password: str = None):
        """
        초기화

        Args:
            master_password: 마스터 비밀번호 (암호화 키 생성용)
        """
        self.cipher = None

        if CRYPTO_AVAILABLE and master_password:
            # 마스터 비밀번호로부터 암호화 키 생성
            # Security: Use environment variable or generate secure random salt
            import hashlib
            salt_source = os.environ.get('ENCRYPTION_SALT', 'autotrade_default_salt_change_in_production')
            salt = hashlib.sha256(salt_source.encode()).digest()[:16]
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            self.cipher = Fernet(key)

    def encrypt_api_key(self, api_key: str) -> str:
        """
        API 키 암호화

        Args:
            api_key: 평문 API 키

        Returns:
            암호화된 API 키 (base64)
        """
        if not self.cipher:
            logger.warning("Cipher not available - returning plain text")
            return api_key

        try:
            encrypted = self.cipher.encrypt(api_key.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"암호화 실패: {e}")
            return api_key

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        API 키 복호화

        Args:
            encrypted_key: 암호화된 API 키

        Returns:
            평문 API 키
        """
        if not self.cipher:
            logger.warning("Cipher not available - returning encrypted text")
            return encrypted_key

        try:
            decoded = base64.b64decode(encrypted_key.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"복호화 실패: {e}")
            return encrypted_key

    def save_encrypted_key(self, key_name: str, api_key: str, file_path: Path):
        """
        암호화된 키 파일 저장

        Args:
            key_name: 키 이름
            api_key: API 키
            file_path: 저장 경로
        """
        encrypted = self.encrypt_api_key(api_key)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w') as f:
            f.write(f"{key_name}={encrypted}\n")

        # 파일 권한 제한 (Unix only)
        try:
            os.chmod(file_path, 0o600)
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to set file permissions: {e}")

        logger.info(f"✓ Encrypted key saved: {file_path}")

    def load_encrypted_key(self, key_name: str, file_path: Path) -> str:
        """
        암호화된 키 파일 로드

        Args:
            key_name: 키 이름
            file_path: 파일 경로

        Returns:
            복호화된 API 키
        """
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith(f"{key_name}="):
                        encrypted = line.strip().split('=', 1)[1]
                        return self.decrypt_api_key(encrypted)

            logger.error(f"Key not found: {key_name}")
            return ""

        except FileNotFoundError:
            logger.error(f"Key file not found: {file_path}")
            return ""


class EnvironmentValidator:
    """환경변수 검증기"""

    @staticmethod
    def validate_required_vars(required_vars: list) -> bool:
        """
        필수 환경변수 검증

        Args:
            required_vars: 필수 환경변수 리스트

        Returns:
            모두 존재하면 True
        """
        missing = []

        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            logger.error(f"Missing required environment variables: {missing}")
            return False

        return True

    @staticmethod
    def sanitize_input(user_input: str, max_length: int = 100) -> str:
        """
        사용자 입력 검증 및 정제

        Args:
            user_input: 사용자 입력
            max_length: 최대 길이

        Returns:
            정제된 입력
        """
        # 길이 제한
        sanitized = user_input[:max_length]

        # 위험한 문자 제거
        dangerous_chars = ['<', '>', '&', '"', "'", '`', '$', '|', ';']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')

        return sanitized.strip()


def load_env_file(env_file: Path = Path('.env')):
    """
    .env 파일 로드

    Args:
        env_file: .env 파일 경로
    """
    if not env_file.exists():
        logger.warning(f".env file not found: {env_file}")
        return

    from dotenv import load_dotenv
    load_dotenv(env_file)

    logger.info(f"✓ Environment variables loaded from {env_file}")
