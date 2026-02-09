# План реализации ролевой модели и аутентификации для KubeEye

## Содержание

1. [Анализ текущей архитектуры проекта](#1-анализ-текущей-архитектуры-проекта)
2. [Модель данных (Backend)](#2-модель-данных-backend)
3. [Система аутентификации (Backend)](#3-система-аутентификации-backend)
4. [Система авторизации (Backend)](#4-система-авторизации-backend)
5. [Инициализация admin пользователя](#5-инициализация-admin-пользователя)
6. [Система аудита (Backend)](#6-система-аудита-backend)
7. [Frontend интеграция](#7-frontend-интеграция)
8. [Конфигурация](#8-конфигурация)
9. [Документация](#9-документация)
10. [Будущее расширение](#10-будущее-расширение)
11. [Порядок реализации (6 этапов)](#11-порядок-реализации-6-этапов)
12. [Безопасность](#12-безопасность)

---

## 1. Анализ текущей архитектуры проекта

### 1.1 Обзор архитектуры

KubeEye - это система инспекции Kubernetes кластеров с архитектурой на основе микросервисов:

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| **Backend** | FastAPI + Python 3.14 | REST API, бизнес-логика |
| **Frontend** | React 19 + TypeScript + Vite | Пользовательский интерфейс |
| **Database** | PostgreSQL 18 | Хранение данных |
| **Container** | Docker + Docker Compose | Контейнеризация |

### 1.2 Текущие слои архитектуры

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                          │
│  React 19 + TypeScript + Zustand + Axios + Ant Design      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                              │
│              FastAPI + Pydantic V2                          │
│  - Controllers                                             │
│  - Middleware (Validation, Logging, CORS)                   │
│  - Routes                                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│  - ClusterService                                          │
│  - InspectionEngine                                        │
│  - GitOpsManager                                           │
│  - ReportCleanupService                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                Infrastructure Layer                         │
│  - K8s Clients                                             │
│  - SSH Service                                             │
│  - Task Manager (APScheduler)                               │
│  - WebSocket Manager                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
│  - SQLAlchemy 2.0 + AsyncPG                                 │
│  - PostgreSQL                                              │
│  - Repositories (BaseRepository)                           │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Текущие модели данных

| Модель | Таблица | Описание |
|--------|---------|----------|
| `Cluster` | `clusters` | Конфигурации Kubernetes кластеров |
| `InspectionResult` | `inspection_results` | Результаты инспекций |
| `ScheduledTask` | `scheduled_tasks` | Запланированные задачи |
| `Secret` | `secrets` | Зашифрованные секреты |
| `EncryptionKey` | `encryption_keys` | Ключи шифрования |

### 1.4 Текущие API endpoints

| Категория | Endpoints | Защита |
|-----------|-----------|--------|
| **Clusters** | `/api/clusters/*` | ❌ Нет |
| **Inspections** | `/api/inspection/*` | ❌ Нет |
| **Reports** | `/api/reports/*` | ❌ Нет |
| **Rules** | `/api/rules/*` | ❌ Нет |
| **GitOps** | `/api/gitops/*` | ❌ Нет |
| **Network** | `/api/network/*` | ❌ Нет |
| **Secrets** | `/api/secrets/*` | ❌ Нет |
| **Scheduled Tasks** | `/api/scheduled-tasks/*` | ❌ Нет |
| **Popeye** | `/api/popeye/*` | ❌ Нет |
| **Queue** | `/api/queue/*` | ❌ Нет |
| **Cleanup** | `/api/cleanup/*` | ❌ Нет |
| **Health** | `/health/*` | ❌ Нет |

### 1.5 Текущие зависимости

#### Backend (Python)
```python
# Основные
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Безопасность
cryptography>=46.0.3
asyncssh>=2.22.0

# Другие
kubernetes>=28.1.0
APScheduler>=3.11.2
alembic>=1.12.0
```

#### Frontend (TypeScript/React)
```json
{
  "dependencies": {
    "react": "^19.2.4",
    "react-dom": "^19.2.4",
    "react-router-dom": "^7.13.0",
    "axios": "^1.13.4",
    "zustand": "^5.0.11",
    "antd": "^6.2.3",
    "@tanstack/react-query": "^5.90.20"
  }
}
```

### 1.6 Проблемы текущей архитектуры

| Проблема | Описание | Решение |
|----------|----------|---------|
| **Отсутствие аутентификации** | Любой пользователь может получить доступ к API | JWT токены |
| **Отсутствие авторизации** | Нет контроля доступа на основе ролей | RBAC |
| **Отсутствие аудита** | Не отслеживаются действия пользователей | Audit логи |
| **Отсутствие управления пользователями** | Нет возможности создания пользователей | User management |
| **Небезопасное хранение паролей** | Пароли не хешируются | bcrypt |

---

## 2. Модель данных (Backend)

### 2.1 Новые таблицы в PostgreSQL

#### 2.1.1 Таблица `users`

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'operator',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
```

### 2.2 SQLAlchemy модели

#### 2.2.1 Модель `User`

```python
# backend/app/db/models/user.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User model for authentication and authorization
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from db.models.base import BaseModel


class UserRole:
    """User roles enum"""
    ADMIN = "admin"
    OPERATOR = "operator"

    @classmethod
    def all(cls):
        return [cls.ADMIN, cls.OPERATOR]

    @classmethod
    def is_valid(cls, role: str) -> bool:
        return role in cls.all()


class User(BaseModel):
    """User model for authentication"""

    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.OPERATOR, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == UserRole.ADMIN

    def is_operator(self) -> bool:
        """Check if user has operator role"""
        return self.role == UserRole.OPERATOR

    def is_locked(self) -> bool:
        """Check if user account is locked"""
        if self.locked_until is None:
            return False
        from datetime import datetime, timezone
        return self.locked_until > datetime.now(timezone.utc)

    def can_login(self) -> bool:
        """Check if user can login"""
        return self.is_active and not self.is_locked()

    def increment_failed_attempts(self):
        """Increment failed login attempts"""
        self.failed_login_attempts += 1

    def reset_failed_attempts(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0

    def lock_account(self, lock_duration_minutes: int = 30):
        """Lock account for specified duration"""
        from datetime import datetime, timezone, timedelta
        self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_duration_minutes)

    def unlock_account(self):
        """Unlock account"""
        self.locked_until = None
        self.failed_login_attempts = 0
```

### 2.3 Обновление `__init__.py` для моделей

```python
# backend/app/db/models/__init__.py
# Models package initialization

from db.models.base import Base
from db.models.inspection_result import InspectionResult
from db.models.cluster import Cluster
from db.models.schedule import ScheduledTask
from db.models.secrets import Secret, EncryptionKey
from db.models.user import User, UserRole

__all__ = [
    "Base",
    "InspectionResult",
    "Cluster",
    "ScheduledTask",
    "Secret",
    "EncryptionKey",
    "User",
    "UserRole",
]
```

### 2.4 Репозитории

#### 2.4.1 UserRepository

```python
# backend/app/db/repositories/user_repository.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User repository for user management
"""

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.base_repository import BaseRepository
from db.models.user import User, UserRole
from core.logging import get_logger

logger = get_logger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for User model"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            stmt = select(User).where(User.username == username)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            raise

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            stmt = select(User).where(User.email == email)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise

    async def get_active_users(self, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """Get all active users"""
        try:
            stmt = select(User).where(User.is_active == True).offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get active users: {e}")
            raise

    async def get_users_by_role(self, role: str, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """Get users by role"""
        try:
            stmt = select(User).where(User.role == role).offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get users by role {role}: {e}")
            raise

    async def username_exists(self, username: str) -> bool:
        """Check if username exists"""
        try:
            stmt = select(User).where(User.username == username)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Failed to check username existence {username}: {e}")
            raise

    async def email_exists(self, email: str) -> bool:
        """Check if email exists"""
        try:
            stmt = select(User).where(User.email == email)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Failed to check email existence {email}: {e}")
            raise

    async def update_last_login(self, user_id: int):
        """Update last login timestamp"""
        try:
            from datetime import datetime, timezone
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.last_login_at = datetime.now(timezone.utc)
                    user.failed_login_attempts = 0
                    user.locked_until = None
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            raise

    async def increment_failed_attempts(self, user_id: int):
        """Increment failed login attempts"""
        try:
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.increment_failed_attempts()
                    # Lock account after 5 failed attempts
                    if user.failed_login_attempts >= 5:
                        user.lock_account(lock_duration_minutes=30)
        except Exception as e:
            logger.error(f"Failed to increment failed attempts for user {user_id}: {e}")
            raise

    async def lock_user(self, user_id: int, lock_duration_minutes: int = 30):
        """Lock user account"""
        try:
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.lock_account(lock_duration_minutes)
        except Exception as e:
            logger.error(f"Failed to lock user {user_id}: {e}")
            raise

    async def unlock_user(self, user_id: int):
        """Unlock user account"""
        try:
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.unlock_account()
        except Exception as e:
            logger.error(f"Failed to unlock user {user_id}: {e}")
            raise

    async def deactivate_user(self, user_id: int):
        """Deactivate user account"""
        try:
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.is_active = False
        except Exception as e:
            logger.error(f"Failed to deactivate user {user_id}: {e}")
            raise

    async def activate_user(self, user_id: int):
        """Activate user account"""
        try:
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.is_active = True
        except Exception as e:
            logger.error(f"Failed to activate user {user_id}: {e}")
            raise
```

### 2.5 Обновление `__init__.py` для репозиториев

```python
# backend/app/db/repositories/__init__.py
# Repositories package initialization

from db.repositories.base_repository import BaseRepository, create_repository
from db.repositories.cluster_repository import ClusterRepository
from db.repositories.inspection_result_repository import InspectionResultRepository
from db.repositories.schedule_repository import ScheduleRepository
from db.repositories.secret_repository import SecretRepository
from db.repositories.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "create_repository",
    "ClusterRepository",
    "InspectionResultRepository",
    "ScheduleRepository",
    "SecretRepository",
    "UserRepository",
]
```

---

## 3. Система аутентификации (Backend)

### 3.1 JWT токены (access token only)

#### 3.1.1 Конфигурация JWT

```python
# backend/app/core/config/settings.py (дополнение)
class Settings(BaseSettings):
    # ... existing settings ...

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT secret key for token signing"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_hours: int = Field(
        default=24, description="JWT access token expiration time in hours"
    )

    # Admin user initialization
    admin_username: str = Field(default="admin", description="Admin username")
    admin_email: str = Field(default="admin@kubeeye.local", description="Admin email")
    admin_password: str = Field(
        default="admin123", description="Admin password (change in production)"
    )
```

#### 3.1.2 JWT утилиты

```python
# backend/app/core/security/jwt_utils.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWT utilities for token generation and validation
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from core.config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


class JWTUtils:
    """JWT utilities for token management"""

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token

        Args:
            data: Payload data to encode in token
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        try:
            to_encode = data.copy()

            if expires_delta:
                expire = datetime.now(timezone.utc) + expires_delta
            else:
                expire = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.jwt_access_token_expire_minutes
                )

            to_encode.update({"exp": expire, "type": "access"})

            encoded_jwt = jwt.encode(
                to_encode,
                settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm
            )

            logger.debug(f"Created access token for user: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            logger.warning(f"Failed to decode token: {e}")
            return None

    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify access token

        Args:
            token: JWT access token string

        Returns:
            Decoded token payload or None if invalid
        """
        payload = JWTUtils.decode_token(token)
        if payload and payload.get("type") == "access":
            return payload
        return None

    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[int]:
        """
        Extract user ID from token

        Args:
            token: JWT token string

        Returns:
            User ID or None if invalid
        """
        payload = JWTUtils.decode_token(token)
        if payload:
            return payload.get("sub")
        return None

    @staticmethod
    def get_username_from_token(token: str) -> Optional[str]:
        """
        Extract username from token

        Args:
            token: JWT token string

        Returns:
            Username or None if invalid
        """
        payload = JWTUtils.decode_token(token)
        if payload:
            return payload.get("username")
        return None

    @staticmethod
    def get_role_from_token(token: str) -> Optional[str]:
        """
        Extract role from token

        Args:
            token: JWT token string

        Returns:
            Role or None if invalid
        """
        payload = JWTUtils.decode_token(token)
        if payload:
            return payload.get("role")
        return None
```

### 3.2 PasswordService

```python
# backend/app/core/security/password_service.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Password service for password hashing and verification
"""

from pwdlib import PasswordHasher
from core.logging import get_logger

logger = get_logger(__name__)


class PasswordService:
    """Service for password hashing and verification"""

    def __init__(self):
        self.hasher = PasswordHasher()

    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        try:
            hashed = self.hasher.hash(password)
            logger.debug("Password hashed successfully")
            return hashed
        except Exception as e:
            logger.error(f"Failed to hash password: {e}")
            raise

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches, False otherwise
        """
        try:
            is_valid = self.hasher.verify(plain_password, hashed_password)
            if is_valid:
                logger.debug("Password verified successfully")
            else:
                logger.warning("Password verification failed")
            return is_valid
        except Exception as e:
            logger.error(f"Failed to verify password: {e}")
            raise


# Global password service instance
password_service = PasswordService()
```

### 3.3 AuthService

```python
# backend/app/services/auth_service.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication service for user authentication and token management
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.user_repository import UserRepository
from db.models.user import User
from core.security.password_service import password_service
from core.security.jwt_utils import JWTUtils
from core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for authentication operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[User]:
        """
        Authenticate user with username and password

        Args:
            username: Username
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            user = await self.user_repo.get_by_username(username)

            if not user:
                logger.warning(f"Authentication failed: user '{username}' not found")
                return None

            if not user.can_login():
                logger.warning(f"Authentication failed: user '{username}' is locked or inactive")
                return None

            if not password_service.verify_password(password, user.password_hash):
                logger.warning(f"Authentication failed: invalid password for user '{username}'")
                await self.user_repo.increment_failed_attempts(user.id)
                return None

            # Update last login and reset failed attempts
            await self.user_repo.update_last_login(user.id)
            logger.info(f"User '{username}' authenticated successfully")

            return user
        except Exception as e:
            logger.error(f"Authentication error for user '{username}': {e}")
            raise

    async def create_tokens(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create access token for user

        Args:
            user: User object
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Dictionary with access_token
        """
        try:
            # Create access token
            access_token = JWTUtils.create_access_token(
                data={
                    "sub": str(user.id),
                    "username": user.username,
                    "role": user.role
                }
            )

            logger.info(f"Access token created for user '{user.username}'")

            return {
                "access_token": access_token,
                "token_type": "bearer"
            }
        except Exception as e:
            logger.error(f"Failed to create access token for user '{user.username}': {e}")
            raise

    async def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully, False otherwise
        """
        try:
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return False

            if not password_service.verify_password(old_password, user.password_hash):
                logger.warning(f"Invalid old password for user {user_id}")
                return False

            # Hash new password
            new_password_hash = password_service.hash_password(new_password)

            # Update password
            await self.user_repo.update(user_id, {"password_hash": new_password_hash})

            logger.info(f"Password changed for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to change password for user {user_id}: {e}")
            raise
```

### 3.4 API эндпоинты аутентификации

#### 3.4.1 Pydantic модели для аутентификации

```python
# backend/app/api/models.py (дополнение)
from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class ChangePasswordRequest(BaseModel):
    """Change password request model"""
    old_password: str
    new_password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    """User response model"""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    """User create request model (admin only)"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(default="operator")
    is_active: bool = True

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        from db.models.user import UserRole
        if not UserRole.is_valid(v):
            raise ValueError(f"Invalid role. Must be one of: {UserRole.all()}")
        return v


class UserUpdateRequest(BaseModel):
    """User update request model (admin only)"""
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v is not None:
            from db.models.user import UserRole
            if not UserRole.is_valid(v):
                raise ValueError(f"Invalid role. Must be one of: {UserRole.all()}")
        return v
```

#### 3.4.2 Auth роутер

```python
# backend/app/api/auth.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication API endpoints
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.repositories.user_repository import UserRepository
from db.models.user import User, UserRole
from services.auth_service import AuthService
from core.security.password_service import password_service
from api.models import (
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    UserResponse,
    UserCreateRequest,
    UserUpdateRequest
)
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login user with username and password

    Returns access and refresh tokens
    """
    try:
        auth_service = AuthService(db)

        # Get client info
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")

        # Authenticate user
        user = await auth_service.authenticate_user(
            username=request.username,
            password=request.password,
            ip_address=ip_address,
            user_agent=user_agent
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Create tokens
        tokens = await auth_service.create_tokens(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Add user info to response
        tokens["user"] = UserResponse.model_validate(user)

        return tokens
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user (clears access token from client)
    """
    try:
        # Access token will be cleared by client
        logger.info("User logged out successfully")
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change current user password

    Requires authentication
    """
    try:
        auth_service = AuthService(db)
        success = await auth_service.change_password(
            user_id=current_user.id,
            old_password=request.old_password,
            new_password=request.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid old password"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information

    Requires authentication
    """
    return UserResponse.model_validate(current_user)


# Admin-only endpoints
@router.get("/users", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users

    Requires admin role
    """
    try:
        user_repo = UserRepository(db)
        users = await user_repo.get_all(limit=limit, offset=skip)
        return [UserResponse.model_validate(user) for user in users]
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create new user

    Requires admin role
    """
    try:
        user_repo = UserRepository(db)

        # Check if username exists
        if await user_repo.username_exists(request.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )

        # Check if email exists
        if await user_repo.email_exists(request.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )

        # Hash password
        password_hash = password_service.hash_password(request.password)

        # Create user
        user = await user_repo.create({
            "username": request.username,
            "email": request.email,
            "password_hash": password_hash,
            "role": request.role,
            "is_active": request.is_active
        })

        logger.info(f"User created by admin: {request.username}")

        return UserResponse.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user

    Requires admin role
    """
    try:
        user_repo = UserRepository(db)

        # Check if user exists
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prepare update data
        update_data = {}
        if request.email is not None:
            # Check if email exists for another user
            existing_user = await user_repo.get_by_email(request.email)
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
            update_data["email"] = request.email

        if request.role is not None:
            update_data["role"] = request.role

        if request.is_active is not None:
            update_data["is_active"] = request.is_active

        # Update user
        updated_user = await user_repo.update(user_id, update_data)

        logger.info(f"User {user_id} updated by admin")

        return UserResponse.model_validate(updated_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user

    Requires admin role
    """
    try:
        user_repo = UserRepository(db)

        # Check if user exists
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prevent deleting self
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete yourself"
            )

        # Delete user
        await user_repo.delete(user_id)

        logger.info(f"User {user_id} deleted by admin")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Audit endpoints (admin only)
@router.get("/audit/logs", response_model=dict, status_code=status.HTTP_200_OK)
async def get_audit_logs(
    offset: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit logs with filtering and pagination

    Requires admin role
    """
    try:
        from services.audit_service import AuditService
        audit_service = AuditService(db)

        logs, total = await audit_service.get_audit_logs(
            limit=limit,
            offset=offset,
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            status=status,
            date_from=date_from,
            date_to=date_to
        )

        return {
            "logs": logs,
            "total": total,
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Get audit logs error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/audit/logs/{log_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_audit_log(
    log_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit log by ID

    Requires admin role
    """
    try:
        from services.audit_service import AuditService
        audit_service = AuditService(db)

        log = await audit_service.get_audit_log_by_id(log_id)

        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit log not found"
            )

        return log
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get audit log error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/audit/stats", response_model=dict, status_code=status.HTTP_200_OK)
async def get_audit_stats(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit statistics

    Requires admin role
    """
    try:
        from services.audit_service import AuditService
        audit_service = AuditService(db)

        stats = await audit_service.get_audit_stats(date_from, date_to)

        return stats
    except Exception as e:
        logger.error(f"Get audit stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/audit/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_audit_logs(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Clean up old audit logs based on retention policy

    Requires admin role
    """
    try:
        from services.audit_service import AuditService
        audit_service = AuditService(db)

        deleted_count = await audit_service.cleanup_old_logs()

        return {
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} old audit logs"
        }
    except Exception as e:
        logger.error(f"Cleanup audit logs error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
```

#### 3.4.3 Зависимости для аутентификации

```python
# backend/app/api/dependencies.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication dependencies for FastAPI
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.repositories.user_repository import UserRepository
from db.models.user import User, UserRole
from core.security.jwt_utils import JWTUtils
from core.logging import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        token = credentials.credentials

        # Verify access token
        payload = JWTUtils.verify_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(int(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None

    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session

    Returns:
        User object or None
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials

        # Verify access token
        payload = JWTUtils.verify_access_token(token)
        if not payload:
            return None

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            return None

        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(int(user_id))

        if not user or not user.is_active:
            return None

        return user
    except Exception as e:
        logger.warning(f"Get optional user error: {e}")
        return None


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require admin role

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return current_user


async def require_operator(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require operator or admin role

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user is not operator or admin
    """
    if not (current_user.is_admin() or current_user.is_operator()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin privileges required"
        )

    return current_user
```

---

## 4. Система авторизации (Backend)

### 4.1 RBAC (Role-Based Access Control)

#### 4.1.1 Определение ролей и прав

| Роль | Описание | Права |
|------|----------|-------|
| **admin** | Администратор системы | Полный доступ ко всем функциям |
| **operator** | Оператор | Чтение и выполнение инспекций, ограниченное управление |

#### 4.1.2 Матрица прав доступа

| Функция | Admin | Operator |
|---------|-------|----------|
| **Просмотр дашборда** | ✅ | ✅ |
| **Управление кластерами** | ✅ | ✅ |
| **Запуск инспекций** | ✅ | ✅ |
| **Просмотр отчетов** | ✅ | ✅ |
| **Управление правилами** | ✅ | ❌ |
| **Управление секретами** | ✅ | ❌ |
| **Управление пользователями** | ✅ | ❌ |
| **Управление GitOps** | ✅ | ❌ |
| **Управление расписаниями** | ✅ | ✅ |
| **Сетевые проверки** | ✅ | ✅ |
| **Popeye сканирование** | ✅ | ✅ |
| **Очистка отчетов** | ✅ | ❌ |
| **Управление очередью** | ✅ | ❌ |

### 4.2 Декораторы авторизации

```python
# backend/app/core/security/authorization.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authorization decorators for role-based access control
"""

from functools import wraps
from typing import Callable, List
from fastapi import HTTPException, status
from db.models.user import User, UserRole
from core.logging import get_logger

logger = get_logger(__name__)


def require_roles(allowed_roles: List[str]):
    """
    Decorator to require specific roles

    Args:
        allowed_roles: List of allowed roles

    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs
            current_user = kwargs.get('current_user')

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            if current_user.role not in allowed_roles:
                logger.warning(
                    f"Access denied for user '{current_user.username}' "
                    f"with role '{current_user.role}' to function '{func.__name__}'"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(func: Callable):
    """
    Decorator to require admin role

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    return require_roles([UserRole.ADMIN])(func)


def require_operator(func: Callable):
    """
    Decorator to require operator or admin role

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    return require_roles([UserRole.ADMIN, UserRole.OPERATOR])(func)
```

### 4.3 Middleware для защиты API

```python
# backend/app/api/auth_middleware.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication middleware for API protection
"""

from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from core.logging import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authentication and authorization

    This middleware checks for valid JWT tokens on protected routes
    """

    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: List[str] = None,
        excluded_prefixes: List[str] = None
    ):
        """
        Initialize auth middleware

        Args:
            app: ASGI application
            excluded_paths: List of exact paths to exclude from auth
            excluded_prefixes: List of path prefixes to exclude from auth
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or []
        self.excluded_prefixes = excluded_prefixes or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/auth/login",
            "/api/auth/refresh"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and check authentication

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response
        """
        path = request.url.path

        # Skip authentication for excluded paths
        if self._is_excluded_path(path):
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"Missing or invalid Authorization header for path: {path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header"}
            )

        # Token validation will be done by route dependencies
        # This middleware just ensures the header is present
        return await call_next(request)

    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if path is excluded from authentication

        Args:
            path: Request path

        Returns:
            True if excluded, False otherwise
        """
        # Check exact paths
        if path in self.excluded_paths:
            return True

        # Check path prefixes
        for prefix in self.excluded_prefixes:
            if path.startswith(prefix):
                return True

        return False


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic audit logging

    This middleware logs all user actions to the audit log
    """

    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: List[str] = None,
        excluded_prefixes: List[str] = None
    ):
        """
        Initialize audit middleware

        Args:
            app: ASGI application
            excluded_paths: List of exact paths to exclude from audit
            excluded_prefixes: List of path prefixes to exclude from audit
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or []
        self.excluded_prefixes = excluded_prefixes or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/auth/login",
            "/api/auth/me",
            "/api/audit/logs",
            "/api/audit/stats"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log to audit

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response
        """
        path = request.url.path
        method = request.method

        # Skip audit for excluded paths
        if self._is_excluded_path(path):
            return await call_next(request)

        # Get user info from request state (set by auth dependencies)
        user_id = getattr(request.state, "user_id", None)
        username = getattr(request.state, "username", None)

        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Process request
        response = await call_next(request)

        # Log action if user is authenticated
        if user_id and username:
            try:
                # Extract action and resource info from path
                action, resource_type, resource_id = self._extract_action_info(method, path)

                # Get audit service from request state
                audit_service = getattr(request.state, "audit_service", None)

                if audit_service:
                    # Determine status based on response status code
                    status = "success" if response.status_code < 400 else "failure"
                    error_message = None

                    if status == "failure":
                        # Try to get error message from response
                        try:
                            if hasattr(response, "body"):
                                import json
                                body = json.loads(response.body)
                                error_message = body.get("detail", "Unknown error")
                        except:
                            error_message = f"HTTP {response.status_code}"

                    # Log action
                    await audit_service.log_action(
                        user_id=user_id,
                        username=username,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        status=status,
                        error_message=error_message
                    )
            except Exception as e:
                # Don't break the request if audit logging fails
                logger.error(f"Failed to log audit action: {e}")

        return response

    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if path is excluded from audit

        Args:
            path: Request path

        Returns:
            True if excluded, False otherwise
        """
        # Check exact paths
        if path in self.excluded_paths:
            return True

        # Check path prefixes
        for prefix in self.excluded_prefixes:
            if path.startswith(prefix):
                return True

        return False

    def _extract_action_info(self, method: str, path: str) -> tuple[str, str, str]:
        """
        Extract action, resource type and resource ID from request

        Args:
            method: HTTP method
            path: Request path

        Returns:
            Tuple of (action, resource_type, resource_id)
        """
        # Parse path
        parts = path.strip("/").split("/")

        # Default values
        action = "unknown"
        resource_type = None
        resource_id = None

        # Map HTTP methods to actions
        method_to_action = {
            "GET": "view",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete"
        }

        # Extract resource type and ID
        if len(parts) >= 2:
            # Remove 'api' prefix if present
            if parts[0] == "api":
                parts = parts[1:]

            if len(parts) >= 1:
                resource_type = parts[0].rstrip("s")  # Remove plural 's'

                # Extract resource ID if present
                if len(parts) >= 2:
                    resource_id = parts[1]

        # Determine action based on method and resource
        if method in method_to_action:
            base_action = method_to_action[method]

            # Special cases
            if resource_type == "auth":
                if "login" in path:
                    action = "login"
                elif "logout" in path:
                    action = "logout"
                elif "change-password" in path:
                    action = "password_change"
                else:
                    action = base_action
            elif resource_type == "inspection":
                if "async" in path:
                    action = "inspection_run"
                else:
                    action = f"inspection_{base_action}"
            elif resource_type == "report":
                if "export" in path:
                    action = "report_export"
                else:
                    action = f"report_{base_action}"
            elif resource_type == "secret":
                action = f"secret_{base_action}"
            elif resource_type == "cluster":
                action = f"cluster_{base_action}"
            elif resource_type == "user":
                action = f"user_{base_action}"
            elif resource_type == "task":
                if "run" in path:
                    action = "task_run"
                else:
                    action = f"task_{base_action}"
            elif resource_type == "gitop":
                action = "gitops_sync"
            elif resource_type == "network-check":
                action = "network_check"
            elif resource_type == "popeye":
                action = "popeye_scan"
            elif resource_type == "cleanup":
                action = "cleanup_run"
            elif resource_type == "queue":
                action = "queue_clear"
            else:
                action = f"{resource_type}_{base_action}" if resource_type else base_action

        return action, resource_type, resource_id
```

### 4.4 Защита существующих эндпоинтов

#### 4.4.1 Обновление роутеров с авторизацией

```python
# backend/app/api/clusters.py (пример обновления)
from api.dependencies import get_current_user, require_operator
from db.models.user import User

# Добавить зависимости к защищенным эндпоинтам
@router.get("/clusters")
async def get_clusters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all clusters (requires authentication)"""
    # ... existing code ...


@router.post("/clusters")
async def create_cluster(
    cluster_data: ClusterCreate,
    current_user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Create new cluster (requires operator or admin)"""
    # ... existing code ...


@router.delete("/clusters/{cluster_name}")
async def delete_cluster(
    cluster_name: str,
    current_user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Delete cluster (requires operator or admin)"""
    # ... existing code ...
```

#### 4.4.2 Таблица защиты эндпоинтов

| Эндпоинт | Метод | Требуемая роль | Статус |
|----------|-------|----------------|--------|
| `/api/auth/login` | POST | None | ✅ Публичный |
| `/api/auth/logout` | POST | Authenticated | ✅ Защищен |
| `/api/auth/me` | GET | Authenticated | ✅ Защищен |
| `/api/auth/change-password` | POST | Authenticated | ✅ Защищен |
| `/api/auth/users` | GET | Admin | ✅ Защищен |
| `/api/auth/users` | POST | Admin | ✅ Защищен |
| `/api/auth/users/{id}` | PUT | Admin | ✅ Защищен |
| `/api/auth/users/{id}` | DELETE | Admin | ✅ Защищен |
| `/api/clusters` | GET | Authenticated | ⏳ Требуется защита |
| `/api/clusters` | POST | Operator | ⏳ Требуется защита |
| `/api/clusters/{name}` | GET | Authenticated | ⏳ Требуется защита |
| `/api/clusters/{name}` | PUT | Operator | ⏳ Требуется защита |
| `/api/clusters/{name}` | DELETE | Operator | ⏳ Требуется защита |
| `/api/inspection` | POST | Operator | ⏳ Требуется защита |
| `/api/inspection/async` | POST | Operator | ⏳ Требуется защита |
| `/api/reports` | GET | Authenticated | ⏳ Требуется защита |
| `/api/reports/{id}` | GET | Authenticated | ⏳ Требуется защита |
| `/api/reports/{id}` | DELETE | Operator | ⏳ Требуется защита |
| `/api/rules` | GET | Authenticated | ⏳ Требуется защита |
| `/api/rules` | PUT | Admin | ⏳ Требуется защита |
| `/api/secrets` | GET | Admin | ⏳ Требуется защита |
| `/api/secrets` | POST | Admin | ⏳ Требуется защита |
| `/api/secrets/{id}` | PUT | Admin | ⏳ Требуется защита |
| `/api/secrets/{id}` | DELETE | Admin | ⏳ Требуется защита |
| `/api/gitops` | GET | Admin | ⏳ Требуется защита |
| `/api/gitops` | PUT | Admin | ⏳ Требуется защита |
| `/api/scheduled-tasks` | GET | Authenticated | ⏳ Требуется защита |
| `/api/scheduled-tasks` | POST | Operator | ⏳ Требуется защита |
| `/api/scheduled-tasks/{id}` | PUT | Operator | ⏳ Требуется защита |
| `/api/scheduled-tasks/{id}` | DELETE | Operator | ⏳ Требуется защита |
| `/api/network-check` | POST | Operator | ⏳ Требуется защита |
| `/api/popeye/scan` | POST | Operator | ⏳ Требуется защита |
| `/api/cleanup` | POST | Admin | ⏳ Требуется защита |
| `/api/queue` | GET | Admin | ⏳ Требуется защита |
| `/health` | GET | None | ✅ Публичный |

---

## 5. Инициализация admin пользователя

### 5.1 Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `KUBEEYE_ADMIN_USERNAME` | `admin` | Имя пользователя admin |
| `KUBEEYE_ADMIN_EMAIL` | `admin@kubeeye.local` | Email admin |
| `KUBEEYE_ADMIN_PASSWORD` | `admin123` | Пароль admin (изменить в production) |

### 5.2 Скрипт инициализации

```python
# backend/app/scripts/init_admin.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to initialize admin user
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_async_session
from db.repositories.user_repository import UserRepository
from db.models.user import User, UserRole
from core.security.password_service import password_service
from core.config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


async def init_admin_user():
    """
    Initialize admin user if not exists
    """
    async with get_async_session() as session:
        user_repo = UserRepository(session)

        # Check if admin user exists
        admin_user = await user_repo.get_by_username(settings.admin_username)

        if admin_user:
            logger.info(f"Admin user '{settings.admin_username}' already exists")
            return admin_user

        # Create admin user
        password_hash = password_service.hash_password(settings.admin_password)

        admin_user = await user_repo.create({
            "username": settings.admin_username,
            "email": settings.admin_email,
            "password_hash": password_hash,
            "role": UserRole.ADMIN,
            "is_active": True
        })

        logger.info(f"Admin user '{settings.admin_username}' created successfully")
        logger.warning(f"Default admin password: {settings.admin_password}")
        logger.warning("Please change the default admin password in production!")

        return admin_user


async def main():
    """Main function"""
    logger.info("Initializing admin user...")
    await init_admin_user()
    logger.info("Admin user initialization completed")


if __name__ == "__main__":
    asyncio.run(main())
```

### 5.3 Интеграция в startup

```python
# backend/app/api/startup.py (дополнение)
async def _init_admin_user():
    """Initialize admin user"""
    try:
        from scripts.init_admin import init_admin_user
        await init_admin_user()
        logger.info("Admin user initialization completed")
    except Exception as e:
        logger.error(f"Failed to initialize admin user: {e}")
        raise


# Обновить lifespan функцию
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events - Async Only"""
    # Startup
    await _init_database()
    await _start_database_monitoring()
    await _init_encryption_key()
    await _init_websocket_subscriptions()
    await _start_task_queue()
    await _start_cleanup_worker()
    await _start_task_manager()
    await _init_admin_user()  # Добавить эту строку

    yield

    # Shutdown
    await _stop_database_monitoring()
    await _close_database_connections()
    await _shutdown_task_queue()
    await _close_ssh_pool()
    await _cleanup_services()
```

---

## 6. Система аудита (Backend)

### 6.1 Таблица `audit_log` в PostgreSQL

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_username ON audit_log(username);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_resource_type ON audit_log(resource_type);
CREATE INDEX idx_audit_log_status ON audit_log(status);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX idx_audit_log_user_action ON audit_log(user_id, action);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
```

### 6.2 SQLAlchemy модель `AuditLog`

```python
# backend/app/db/models/audit_log.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit log model for tracking user actions
"""

from sqlalchemy import Column, String, DateTime, Text, Index, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from db.models.base import BaseModel
import uuid


class AuditAction:
    """Audit action types"""
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    CLUSTER_CREATE = "cluster_create"
    CLUSTER_UPDATE = "cluster_update"
    CLUSTER_DELETE = "cluster_delete"
    INSPECTION_RUN = "inspection_run"
    INSPECTION_DELETE = "inspection_delete"
    REPORT_VIEW = "report_view"
    REPORT_EXPORT = "report_export"
    REPORT_DELETE = "report_delete"
    SECRET_CREATE = "secret_create"
    SECRET_UPDATE = "secret_update"
    SECRET_DELETE = "secret_delete"
    RULE_UPDATE = "rule_update"
    GITOPS_SYNC = "gitops_sync"
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_DELETE = "task_delete"
    TASK_RUN = "task_run"
    NETWORK_CHECK = "network_check"
    POPEYE_SCAN = "popeye_scan"
    CLEANUP_RUN = "cleanup_run"
    QUEUE_CLEAR = "queue_clear"

    @classmethod
    def all(cls):
        return [
            cls.LOGIN, cls.LOGOUT, cls.PASSWORD_CHANGE,
            cls.USER_CREATE, cls.USER_UPDATE, cls.USER_DELETE,
            cls.CLUSTER_CREATE, cls.CLUSTER_UPDATE, cls.CLUSTER_DELETE,
            cls.INSPECTION_RUN, cls.INSPECTION_DELETE,
            cls.REPORT_VIEW, cls.REPORT_EXPORT, cls.REPORT_DELETE,
            cls.SECRET_CREATE, cls.SECRET_UPDATE, cls.SECRET_DELETE,
            cls.RULE_UPDATE, cls.GITOPS_SYNC,
            cls.TASK_CREATE, cls.TASK_UPDATE, cls.TASK_DELETE, cls.TASK_RUN,
            cls.NETWORK_CHECK, cls.POPEYE_SCAN,
            cls.CLEANUP_RUN, cls.QUEUE_CLEAR
        ]


class AuditStatus:
    """Audit status types"""
    SUCCESS = "success"
    FAILURE = "failure"

    @classmethod
    def all(cls):
        return [cls.SUCCESS, cls.FAILURE]


class AuditLog(BaseModel):
    """Audit log model for tracking user actions"""

    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default=AuditStatus.SUCCESS, index=True)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', status='{self.status}')>"

    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "username": self.username,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
```

### 6.3 Репозиторий `AuditLogRepository`

```python
# backend/app/db/repositories/audit_log_repository.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit log repository for audit log management
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.base_repository import BaseRepository
from db.models.audit_log import AuditLog, AuditAction, AuditStatus
from core.logging import get_logger

logger = get_logger(__name__)


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog model"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)

    async def get_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> tuple[List[AuditLog], int]:
        """
        Get audit logs with filtering and pagination

        Args:
            limit: Maximum number of records
            offset: Offset for pagination
            user_id: Filter by user ID
            username: Filter by username
            action: Filter by action type
            resource_type: Filter by resource type
            status: Filter by status
            date_from: Filter by date from
            date_to: Filter by date to

        Returns:
            Tuple of (audit logs list, total count)
        """
        try:
            # Build query
            stmt = select(AuditLog)

            # Apply filters
            conditions = []
            if user_id:
                conditions.append(AuditLog.user_id == user_id)
            if username:
                conditions.append(AuditLog.username.ilike(f"%{username}%"))
            if action:
                conditions.append(AuditLog.action == action)
            if resource_type:
                conditions.append(AuditLog.resource_type == resource_type)
            if status:
                conditions.append(AuditLog.status == status)
            if date_from:
                conditions.append(AuditLog.created_at >= date_from)
            if date_to:
                conditions.append(AuditLog.created_at <= date_to)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Get total count
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_result = await self.session.execute(count_stmt)
            total = total_result.scalar()

            # Apply pagination and ordering
            stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)

            # Execute query
            result = await self.session.execute(stmt)
            audit_logs = result.scalars().all()

            return audit_logs, total
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            raise

    async def get_audit_log_by_id(self, log_id: str) -> Optional[AuditLog]:
        """
        Get audit log by ID

        Args:
            log_id: Audit log ID

        Returns:
            Audit log or None
        """
        try:
            stmt = select(AuditLog).where(AuditLog.id == log_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get audit log by ID {log_id}: {e}")
            raise

    async def get_user_audit_logs(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Get audit logs for specific user

        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Offset for pagination

        Returns:
            List of audit logs
        """
        try:
            stmt = select(AuditLog).where(
                AuditLog.user_id == user_id
            ).order_by(
                AuditLog.created_at.desc()
            ).offset(offset).limit(limit)

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get audit logs for user {user_id}: {e}")
            raise

    async def get_resource_audit_logs(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Get audit logs for specific resource

        Args:
            resource_type: Type of resource
            resource_id: ID of resource
            limit: Maximum number of records
            offset: Offset for pagination

        Returns:
            List of audit logs
        """
        try:
            stmt = select(AuditLog).where(
                and_(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id
                )
            ).order_by(
                AuditLog.created_at.desc()
            ).offset(offset).limit(limit)

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get audit logs for resource {resource_type}:{resource_id}: {e}")
            raise

    async def delete_old_logs(self, days: int = 14) -> int:
        """
        Delete audit logs older than specified days

        Args:
            days: Number of days to retain logs

        Returns:
            Number of deleted records
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            async with self.transaction():
                stmt = select(AuditLog).where(
                    AuditLog.created_at < cutoff_date
                )
                result = await self.session.execute(stmt)
                old_logs = result.scalars().all()

                for log in old_logs:
                    await self.session.delete(log)

                deleted_count = len(old_logs)
                logger.info(f"Deleted {deleted_count} audit logs older than {days} days")

                return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete old audit logs: {e}")
            raise

    async def get_audit_stats(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit statistics

        Args:
            date_from: Filter by date from
            date_to: Filter by date to

        Returns:
            Dictionary with statistics
        """
        try:
            # Build base query
            stmt = select(AuditLog)
            conditions = []
            if date_from:
                conditions.append(AuditLog.created_at >= date_from)
            if date_to:
                conditions.append(AuditLog.created_at <= date_to)
            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Total logs
            total_stmt = select(func.count()).select_from(stmt.subquery())
            total_result = await self.session.execute(total_stmt)
            total = total_result.scalar()

            # Logs by action
            action_stmt = select(
                AuditLog.action,
                func.count().label('count')
            ).select_from(stmt.subquery()).group_by(AuditLog.action)
            action_result = await self.session.execute(action_stmt)
            by_action = {row.action: row.count for row in action_result}

            # Logs by user
            user_stmt = select(
                AuditLog.username,
                func.count().label('count')
            ).select_from(stmt.subquery()).group_by(AuditLog.username).order_by(func.count().desc()).limit(10)
            user_result = await self.session.execute(user_stmt)
            by_user = {row.username: row.count for row in user_result}

            # Logs by status
            status_stmt = select(
                AuditLog.status,
                func.count().label('count')
            ).select_from(stmt.subquery()).group_by(AuditLog.status)
            status_result = await self.session.execute(status_stmt)
            by_status = {row.status: row.count for row in status_result}

            # Logs by resource type
            resource_stmt = select(
                AuditLog.resource_type,
                func.count().label('count')
            ).select_from(stmt.subquery()).group_by(AuditLog.resource_type)
            resource_result = await self.session.execute(resource_stmt)
            by_resource = {row.resource_type: row.count for row in resource_result if row.resource_type}

            return {
                "total": total,
                "by_action": by_action,
                "by_user": by_user,
                "by_status": by_status,
                "by_resource": by_resource
            }
        except Exception as e:
            logger.error(f"Failed to get audit stats: {e}")
            raise
```

### 6.4 Сервис `AuditService`

```python
# backend/app/services/audit_service.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit service for tracking user actions
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.audit_log_repository import AuditLogRepository
from db.models.audit_log import AuditLog, AuditAction, AuditStatus
from core.config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """Service for audit logging"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_log_repo = AuditLogRepository(session)

    async def log_action(
        self,
        user_id: str,
        username: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = AuditStatus.SUCCESS,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log user action

        Args:
            user_id: User ID
            username: Username
            action: Action type
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional details
            ip_address: Client IP address
            user_agent: Client user agent
            status: Status of action (success/failure)
            error_message: Error message if action failed

        Returns:
            Created audit log
        """
        try:
            # Check if audit is enabled
            if not settings.audit_enabled:
                logger.debug("Audit logging is disabled")
                return None

            audit_log = await self.audit_log_repo.create({
                "user_id": user_id,
                "username": username,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "status": status,
                "error_message": error_message
            })

            logger.debug(
                f"Audit log created: user={username}, action={action}, "
                f"resource={resource_type}:{resource_id}, status={status}"
            )

            return audit_log
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
            # Don't raise exception to avoid breaking main flow
            return None

    async def get_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get audit logs with filtering and pagination

        Args:
            limit: Maximum number of records
            offset: Offset for pagination
            user_id: Filter by user ID
            username: Filter by username
            action: Filter by action type
            resource_type: Filter by resource type
            status: Filter by status
            date_from: Filter by date from
            date_to: Filter by date to

        Returns:
            Tuple of (audit logs list, total count)
        """
        try:
            audit_logs, total = await self.audit_log_repo.get_audit_logs(
                limit=limit,
                offset=offset,
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                status=status,
                date_from=date_from,
                date_to=date_to
            )

            return [log.to_dict() for log in audit_logs], total
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            raise

    async def get_audit_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """
        Get audit log by ID

        Args:
            log_id: Audit log ID

        Returns:
            Audit log details or None
        """
        try:
            audit_log = await self.audit_log_repo.get_audit_log_by_id(log_id)
            return audit_log.to_dict() if audit_log else None
        except Exception as e:
            logger.error(f"Failed to get audit log by ID {log_id}: {e}")
            raise

    async def get_audit_stats(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit statistics

        Args:
            date_from: Filter by date from
            date_to: Filter by date to

        Returns:
            Dictionary with statistics
        """
        try:
            return await self.audit_log_repo.get_audit_stats(date_from, date_to)
        except Exception as e:
            logger.error(f"Failed to get audit stats: {e}")
            raise

    async def cleanup_old_logs(self) -> int:
        """
        Clean up old audit logs based on retention policy

        Returns:
            Number of deleted records
        """
        try:
            retention_days = settings.audit_retention_days
            deleted_count = await self.audit_log_repo.delete_old_logs(days=retention_days)
            logger.info(f"Cleaned up {deleted_count} old audit logs (retention: {retention_days} days)")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old audit logs: {e}")
            raise

    async def log_login(
        self,
        user_id: str,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        Log login action

        Args:
            user_id: User ID
            username: Username
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether login was successful
            error_message: Error message if login failed

        Returns:
            Created audit log
        """
        return await self.log_action(
            user_id=user_id,
            username=username,
            action=AuditAction.LOGIN,
            ip_address=ip_address,
            user_agent=user_agent,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            error_message=error_message
        )

    async def log_logout(
        self,
        user_id: str,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        Log logout action

        Args:
            user_id: User ID
            username: Username
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created audit log
        """
        return await self.log_action(
            user_id=user_id,
            username=username,
            action=AuditAction.LOGOUT,
            ip_address=ip_address,
            user_agent=user_agent
        )

    async def log_password_change(
        self,
        user_id: str,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        Log password change action

        Args:
            user_id: User ID
            username: Username
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created audit log
        """
        return await self.log_action(
            user_id=user_id,
            username=username,
            action=AuditAction.PASSWORD_CHANGE,
            ip_address=ip_address,
            user_agent=user_agent
        )

    async def log_cluster_action(
        self,
        user_id: str,
        username: str,
        action: str,
        cluster_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[AuditLog]:
        """
        Log cluster action

        Args:
            user_id: User ID
            username: Username
            action: Action type (create, update, delete)
            cluster_name: Cluster name
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional details

        Returns:
            Created audit log
        """
        return await self.log_action(
            user_id=user_id,
            username=username,
            action=action,
            resource_type="cluster",
            resource_id=cluster_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

    async def log_inspection_action(
        self,
        user_id: str,
        username: str,
        action: str,
        inspection_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[AuditLog]:
        """
        Log inspection action

        Args:
            user_id: User ID
            username: Username
            action: Action type (run, delete)
            inspection_id: Inspection ID
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional details

        Returns:
            Created audit log
        """
        return await self.log_action(
            user_id=user_id,
            username=username,
            action=action,
            resource_type="inspection",
            resource_id=inspection_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
```

### 6.5 Обновление `__init__.py` для моделей

```python
# backend/app/db/models/__init__.py (обновление)
# Models package initialization

from db.models.base import Base
from db.models.inspection_result import InspectionResult
from db.models.cluster import Cluster
from db.models.schedule import ScheduledTask
from db.models.secrets import Secret, EncryptionKey
from db.models.user import User, UserRole
from db.models.refresh_token import RefreshToken
from db.models.audit_log import AuditLog, AuditAction, AuditStatus

__all__ = [
    "Base",
    "InspectionResult",
    "Cluster",
    "ScheduledTask",
    "Secret",
    "EncryptionKey",
    "User",
    "UserRole",
    "RefreshToken",
    "AuditLog",
    "AuditAction",
    "AuditStatus",
]
```

### 6.6 Обновление `__init__.py` для репозиториев

```python
# backend/app/db/repositories/__init__.py (обновление)
# Repositories package initialization

from db.repositories.base_repository import BaseRepository, create_repository
from db.repositories.cluster_repository import ClusterRepository
from db.repositories.inspection_result_repository import InspectionResultRepository
from db.repositories.schedule_repository import ScheduleRepository
from db.repositories.secret_repository import SecretRepository
from db.repositories.user_repository import UserRepository
from db.repositories.refresh_token_repository import RefreshTokenRepository
from db.repositories.audit_log_repository import AuditLogRepository

__all__ = [
    "BaseRepository",
    "create_repository",
    "ClusterRepository",
    "InspectionResultRepository",
    "ScheduleRepository",
    "SecretRepository",
    "UserRepository",
    "RefreshTokenRepository",
    "AuditLogRepository",
]
```

---

## 7. Frontend интеграция

### 6.1 Страница входа

```typescript
// frontend/src/pages/Login.tsx
import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import './Login.css';

const { Title } = Typography;

interface LoginFormData {
  username: string;
  password: string;
}

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuthStore();

  const onFinish = async (values: LoginFormData) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('Login successful');
      navigate('/dashboard');
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-card">
        <Title level={2} className="login-title">
          KubeEye Login
        </Title>
        <Form
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: 'Please input your username!' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="Username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Please input your password!' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Password"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
            >
              Log in
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
```

### 6.2 Хранение токенов

```typescript
// frontend/src/utils/tokenStorage.ts
/**
 * Token storage utilities
 */

const ACCESS_TOKEN_KEY = 'access_token';

export const tokenStorage = {
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  setAccessToken(token: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  },

  clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  },

  hasToken(): boolean {
    return !!this.getAccessToken();
  }
};
```

### 6.3 Zustand store для аутентификации

```typescript
// frontend/src/stores/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '../services/api';
import { tokenStorage } from '../utils/tokenStorage';

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  getCurrentUser: () => Promise<void>;
  checkAuth: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (username: string, password: string) => {
        set({ isLoading: true });
        try {
          const response = await api.post('/api/auth/login', {
            username,
            password
          });

          const { access_token, user } = response.data;

          // Store access token
          tokenStorage.setAccessToken(access_token);

          // Update state
          set({
            user,
            isAuthenticated: true,
            isLoading: false
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: async () => {
        try {
          await api.post('/api/auth/logout');
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          // Clear token and state
          tokenStorage.clearTokens();
          set({
            user: null,
            isAuthenticated: false
          });
        }
      },

      getCurrentUser: async () => {
        try {
          const response = await api.get('/api/auth/me');
          set({
            user: response.data,
            isAuthenticated: true
          });
        } catch (error) {
          tokenStorage.clearTokens();
          set({
            user: null,
            isAuthenticated: false
          });
          throw error;
        }
      },

      checkAuth: () => {
        return tokenStorage.hasToken() && get().isAuthenticated;
      }
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);
```

### 6.4 Axios interceptor

```typescript
// frontend/src/services/api.ts (обновление)
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { tokenStorage } from '../utils/tokenStorage';
import { useAuthStore } from '../stores/authStore';

const baseConfig = {
  baseURL: '',
  timeout: 15000,
};

const api = axios.create(baseConfig);

// Request interceptor - add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    // If error is 401, logout user
    if (error.response?.status === 401) {
      const authStore = useAuthStore.getState();
      await authStore.logout();
      window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);

// ... existing API functions ...
```

### 6.5 Защита роутов

```typescript
// frontend/src/components/ProtectedRoute.tsx
import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { LoadingScreen } from './ui/LoadingScreen';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'operator';
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole
}) => {
  const { isAuthenticated, user, isLoading, checkAuth } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    // Check auth on mount
    if (!checkAuth()) {
      // Redirect to login if not authenticated
      return;
    }
  }, []);

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role if required
  if (requiredRole && user) {
    const hasRequiredRole =
      requiredRole === 'admin' ? user.role === 'admin' :
      requiredRole === 'operator' ? (user.role === 'admin' || user.role === 'operator') :
      true;

    if (!hasRequiredRole) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  return <>{children}</>;
};

export default ProtectedRoute;
```

### 6.6 UI компоненты

#### 6.6.1 UserMenu компонент

```typescript
// frontend/src/components/UserMenu.tsx
import React from 'react';
import { Dropdown, Avatar, Space, Typography, Button } from 'antd';
import {
  UserOutlined,
  LogoutOutlined,
  LockOutlined,
  SettingOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

const { Text } = Typography;

const UserMenu: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleChangePassword = () => {
    navigate('/change-password');
  };

  const menuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: (
        <Space direction="vertical" size={0}>
          <Text strong>{user?.username}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {user?.role}
          </Text>
        </Space>
      ),
      disabled: true
    },
    {
      type: 'divider'
    },
    {
      key: 'change-password',
      icon: <LockOutlined />,
      label: 'Change Password',
      onClick: handleChangePassword
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      onClick: handleLogout,
      danger: true
    }
  ];

  return (
    <Dropdown menu={{ items: menuItems }} placement="bottomRight">
      <Button type="text" icon={<Avatar icon={<UserOutlined />} />}>
        {user?.username}
      </Button>
    </Dropdown>
  );
};

export default UserMenu;
```

#### 6.6.2 ChangePassword компонент

```typescript
// frontend/src/pages/ChangePassword.tsx
import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Typography } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

const { Title } = Typography;

interface ChangePasswordFormData {
  old_password: string;
  new_password: string;
  confirm_password: string;
}

const ChangePassword: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const onFinish = async (values: ChangePasswordFormData) => {
    if (values.new_password !== values.confirm_password) {
      message.error('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await api.post('/api/auth/change-password', {
        old_password: values.old_password,
        new_password: values.new_password
      });
      message.success('Password changed successfully');
      navigate('/dashboard');
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: '50px auto' }}>
      <Card>
        <Title level={3}>Change Password</Title>
        <Form
          form={form}
          onFinish={onFinish}
          autoComplete="off"
          layout="vertical"
        >
          <Form.Item
            name="old_password"
            label="Old Password"
            rules={[{ required: true, message: 'Please input your old password!' }]}
          >
            <Input.Password prefix={<LockOutlined />} />
          </Form.Item>

          <Form.Item
            name="new_password"
            label="New Password"
            rules={[
              { required: true, message: 'Please input your new password!' },
              { min: 6, message: 'Password must be at least 6 characters!' }
            ]}
          >
            <Input.Password prefix={<LockOutlined />} />
          </Form.Item>

          <Form.Item
            name="confirm_password"
            label="Confirm New Password"
            dependencies={['new_password']}
            rules={[
              { required: true, message: 'Please confirm your new password!' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('Passwords do not match!'));
                }
              })
            ]}
          >
            <Input.Password prefix={<LockOutlined />} />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              Change Password
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default ChangePassword;
```

### 6.7 Скрытие элементов на основе роли

```typescript
// frontend/src/components/RoleBasedAccess.tsx
import React from 'react';
import { useAuthStore } from '../stores/authStore';

interface RoleBasedAccessProps {
  children: React.ReactNode;
  allowedRoles?: ('admin' | 'operator')[];
  fallback?: React.ReactNode;
}

const RoleBasedAccess: React.FC<RoleBasedAccessProps> = ({
  children,
  allowedRoles = ['admin', 'operator'],
  fallback = null
}) => {
  const { user } = useAuthStore();

  if (!user) {
    return <>{fallback}</>;
  }

  const hasAccess = allowedRoles.includes(user.role as 'admin' | 'operator');

  return hasAccess ? <>{children}</> : <>{fallback}</>;
};

export default RoleBasedAccess;

// Пример использования:
// <RoleBasedAccess allowedRoles={['admin']}>
//   <Button danger>Delete User</Button>
// </RoleBasedAccess>
```

#### 6.8 AuditLogs страница

```typescript
// frontend/src/pages/AuditLogs.tsx
import React, { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Space,
  Tag,
  Modal,
  Descriptions,
  Statistic,
  Row,
  Col,
  message,
  Spin
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  DeleteOutlined,
  EyeOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { api } from '../services/api';
import { useAuthStore } from '../stores/authStore';
import RoleBasedAccess from '../components/RoleBasedAccess';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

interface AuditLog {
  id: string;
  user_id: string;
  username: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, any> | null;
  ip_address: string | null;
  user_agent: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

interface AuditStats {
  total: number;
  by_action: Record<string, number>;
  by_user: Record<string, number>;
  by_status: Record<string, number>;
  by_resource: Record<string, number>;
}

const AuditLogs: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 });
  const [filters, setFilters] = useState({
    username: '',
    action: '',
    resource_type: '',
    status: '',
    date_from: null as dayjs.Dayjs | null,
    date_to: null as dayjs.Dayjs | null
  });

  const { user } = useAuthStore();

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params: any = {
        offset: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize
      };

      if (filters.username) params.username = filters.username;
      if (filters.action) params.action = filters.action;
      if (filters.resource_type) params.resource_type = filters.resource_type;
      if (filters.status) params.status = filters.status;
      if (filters.date_from) params.date_from = filters.date_from.toISOString();
      if (filters.date_to) params.date_to = filters.date_to.toISOString();

      const response = await api.get('/api/auth/audit/logs', { params });
      setLogs(response.data.logs);
      setTotal(response.data.total);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to fetch audit logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const params: any = {};
      if (filters.date_from) params.date_from = filters.date_from.toISOString();
      if (filters.date_to) params.date_to = filters.date_to.toISOString();

      const response = await api.get('/api/auth/audit/stats', { params });
      setStats(response.data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to fetch audit stats');
    }
  };

  const handleSearch = () => {
    setPagination({ ...pagination, current: 1 });
    fetchLogs();
    fetchStats();
  };

  const handleReset = () => {
    setFilters({
      username: '',
      action: '',
      resource_type: '',
      status: '',
      date_from: null,
      date_to: null
    });
    setPagination({ ...pagination, current: 1 });
    fetchLogs();
    fetchStats();
  };

  const handleViewDetails = (log: AuditLog) => {
    setSelectedLog(log);
    setDetailModalVisible(true);
  };

  const handleCleanup = async () => {
    Modal.confirm({
      title: 'Clean up old audit logs',
      content: 'This will delete all audit logs older than the retention period. Are you sure?',
      okText: 'Yes',
      okType: 'danger',
      cancelText: 'No',
      onOk: async () => {
        try {
          await api.post('/api/auth/audit/cleanup');
          message.success('Old audit logs cleaned up successfully');
          fetchLogs();
          fetchStats();
        } catch (error: any) {
          message.error(error.response?.data?.detail || 'Failed to clean up audit logs');
        }
      }
    });
  };

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [pagination.current, pagination.pageSize]);

  const columns: ColumnsType<AuditLog> = [
    {
      title: 'Timestamp',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
      sorter: true
    },
    {
      title: 'User',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      render: (username: string) => <Tag color="blue">{username}</Tag>
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      width: 150,
      render: (action: string) => {
        const colorMap: Record<string, string> = {
          login: 'green',
          logout: 'orange',
          password_change: 'purple',
          user_create: 'cyan',
          user_update: 'blue',
          user_delete: 'red',
          cluster_create: 'cyan',
          cluster_update: 'blue',
          cluster_delete: 'red',
          inspection_run: 'green',
          inspection_delete: 'red',
          report_view: 'blue',
          report_export: 'purple',
          report_delete: 'red',
          secret_create: 'cyan',
          secret_update: 'blue',
          secret_delete: 'red',
          rule_update: 'orange',
          gitops_sync: 'green',
          task_create: 'cyan',
          task_update: 'blue',
          task_delete: 'red',
          task_run: 'green',
          network_check: 'purple',
          popeye_scan: 'green',
          cleanup_run: 'orange',
          queue_clear: 'red'
        };
        return <Tag color={colorMap[action] || 'default'}>{action}</Tag>;
      }
    },
    {
      title: 'Resource',
      key: 'resource',
      width: 200,
      render: (_, record) => {
        if (record.resource_type && record.resource_id) {
          return (
            <Space direction="vertical" size={0}>
              <Tag color="geekblue">{record.resource_type}</Tag>
              <span style={{ fontSize: '12px', color: '#999' }}>{record.resource_id}</span>
            </Space>
          );
        }
        return '-';
      }
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === 'success' ? 'green' : 'red'}>
          {status}
        </Tag>
      )
    },
    {
      title: 'IP Address',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      render: (ip: string | null) => ip || '-'
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetails(record)}
        >
          View
        </Button>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card title="Audit Logs" extra={
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              fetchLogs();
              fetchStats();
            }}
          >
            Refresh
          </Button>
          <RoleBasedAccess allowedRoles={['admin']}>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleCleanup}
            >
              Cleanup
            </Button>
          </RoleBasedAccess>
        </Space>
      }>
        {/* Statistics */}
        {stats && (
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Statistic
                title="Total Logs"
                value={stats.total}
                valueStyle={{ color: '#3f8600' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Successful Actions"
                value={stats.by_status?.success || 0}
                valueStyle={{ color: '#3f8600' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Failed Actions"
                value={stats.by_status?.failure || 0}
                valueStyle={{ color: '#cf1322' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Unique Users"
                value={Object.keys(stats.by_user || {}).length}
              />
            </Col>
          </Row>
        )}

        {/* Filters */}
        <Form layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item label="Username">
            <Input
              placeholder="Search by username"
              value={filters.username}
              onChange={(e) => setFilters({ ...filters, username: e.target.value })}
              allowClear
            />
          </Form.Item>
          <Form.Item label="Action">
            <Select
              placeholder="Select action"
              value={filters.action || undefined}
              onChange={(value) => setFilters({ ...filters, action: value || '' })}
              allowClear
              style={{ width: 150 }}
            >
              <Select.Option value="login">Login</Select.Option>
              <Select.Option value="logout">Logout</Select.Option>
              <Select.Option value="password_change">Password Change</Select.Option>
              <Select.Option value="user_create">User Create</Select.Option>
              <Select.Option value="user_update">User Update</Select.Option>
              <Select.Option value="user_delete">User Delete</Select.Option>
              <Select.Option value="cluster_create">Cluster Create</Select.Option>
              <Select.Option value="cluster_update">Cluster Update</Select.Option>
              <Select.Option value="cluster_delete">Cluster Delete</Select.Option>
              <Select.Option value="inspection_run">Inspection Run</Select.Option>
              <Select.Option value="report_view">Report View</Select.Option>
              <Select.Option value="report_export">Report Export</Select.Option>
              <Select.Option value="secret_create">Secret Create</Select.Option>
              <Select.Option value="secret_update">Secret Update</Select.Option>
              <Select.Option value="secret_delete">Secret Delete</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="Resource Type">
            <Select
              placeholder="Select resource type"
              value={filters.resource_type || undefined}
              onChange={(value) => setFilters({ ...filters, resource_type: value || '' })}
              allowClear
              style={{ width: 150 }}
            >
              <Select.Option value="cluster">Cluster</Select.Option>
              <Select.Option value="inspection">Inspection</Select.Option>
              <Select.Option value="report">Report</Select.Option>
              <Select.Option value="secret">Secret</Select.Option>
              <Select.Option value="user">User</Select.Option>
              <Select.Option value="task">Task</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="Status">
            <Select
              placeholder="Select status"
              value={filters.status || undefined}
              onChange={(value) => setFilters({ ...filters, status: value || '' })}
              allowClear
              style={{ width: 120 }}
            >
              <Select.Option value="success">Success</Select.Option>
              <Select.Option value="failure">Failure</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="Date Range">
            <RangePicker
              value={filters.date_from && filters.date_to ? [filters.date_from, filters.date_to] : null}
              onChange={(dates) => setFilters({
                ...filters,
                date_from: dates?.[0] || null,
                date_to: dates?.[1] || null
              })}
            />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleSearch}
              >
                Search
              </Button>
              <Button onClick={handleReset}>
                Reset
              </Button>
            </Space>
          </Form.Item>
        </Form>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} logs`,
            onChange: (page, pageSize) => setPagination({ current: page, pageSize })
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* Detail Modal */}
      <Modal
        title="Audit Log Details"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Close
          </Button>
        ]}
        width={800}
      >
        {selectedLog && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="ID" span={2}>
              {selectedLog.id}
            </Descriptions.Item>
            <Descriptions.Item label="Timestamp" span={2}>
              {dayjs(selectedLog.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="User ID">
              {selectedLog.user_id}
            </Descriptions.Item>
            <Descriptions.Item label="Username">
              {selectedLog.username}
            </Descriptions.Item>
            <Descriptions.Item label="Action">
              <Tag color="blue">{selectedLog.action}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={selectedLog.status === 'success' ? 'green' : 'red'}>
                {selectedLog.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Resource Type">
              {selectedLog.resource_type || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Resource ID">
              {selectedLog.resource_id || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="IP Address">
              {selectedLog.ip_address || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="User Agent" span={2}>
              {selectedLog.user_agent || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Error Message" span={2}>
              {selectedLog.error_message || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Details" span={2}>
              {selectedLog.details ? (
                <pre style={{ maxHeight: '200px', overflow: 'auto' }}>
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              ) : '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default AuditLogs;
```

#### 6.9 Обновление роутинга для страницы аудита

```typescript
// frontend/src/App.tsx (дополнение)
import AuditLogs from './pages/AuditLogs';

// В компоненте App:
<Route
  path="/audit-logs"
  element={
    <ProtectedRoute requiredRole="admin">
      <AuditLogs />
    </ProtectedRoute>
  }
/>
```

#### 6.10 Добавление ссылки на страницу аудита в меню

```typescript
// frontend/src/components/Layout.tsx (дополнение)
import RoleBasedAccess from './RoleBasedAccess';

// В меню добавить:
<RoleBasedAccess allowedRoles={['admin']}>
  <Menu.Item key="/audit-logs" icon={<AuditOutlined />}>
    <Link to="/audit-logs">Audit Logs</Link>
  </Menu.Item>
</RoleBasedAccess>
```
```

---

## 7. Конфигурация

### 7.1 Backend конфигурация

```python
# backend/app/core/config/settings.py (полное обновление)
class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application paths
    kubeeye_data_dir: str = Field(
        default=str(Path(__file__).parent.parent.parent),
        description="Base directory for KubeEye data",
    )

    # Logging
    kubeeye_log_level: str = Field(default="INFO", description="Logging level", validation_alias="KUBEEYE_LOG_LEVEL")

    # Database configuration
    db_host: str = Field(default="localhost", description="Database host")
    db_port: str = Field(default="5432", description="Database port")
    db_user: str = Field(default="kubeeye", description="Database username")
    db_pass: str = Field(default="kubeeye", description="Database password")
    db_name: str = Field(default="kubeeye", description="Database name")
    sql_debug: bool = Field(default=False, description="Enable SQL debug logging")

    # Report cleanup
    kubeeye_report_retention_days: int = Field(default=7, description="Number of days to retain reports")

    # SSH configuration
    kubeeye_ssh_connection_timeout: int = Field(default=10, description="SSH connection timeout in seconds")
    kubeeye_ssh_max_concurrent_checks: int = Field(default=20, description="Max concurrent SSH checks")

    # SSH connection pool configuration
    kubeeye_ssh_pool_size: int = Field(default=10, description="SSH connection pool size")
    kubeeye_ssh_pool_connection_timeout: int = Field(
        default=300, description="SSH connection pool timeout in seconds (5 minutes)"
    )
    kubeeye_ssh_pool_keepalive_interval: int = Field(
        default=60, description="SSH connection pool keepalive interval in seconds (1 minute)"
    )

    # Popeye configuration
    kubeeye_popeye_path: str = Field(default="/usr/local/bin/popeye", description="Path to Popeye binary")
    kubeeye_popeye_timeout: int = Field(default=300, description="Popeye execution timeout")
    kubeeye_popeye_default_format: str = Field(default="html", description="Default Popeye output format")

    # Node inspector configuration
    node_inspector_max_workers: int = Field(default=5, description="Max workers for node inspector")
    node_inspector_timeout: int = Field(default=30, description="Timeout for node inspector")
    node_inspector_connection_timeout: int = Field(default=10, description="Connection timeout for node inspector")
    node_inspector_retry_attempts: int = Field(default=2, description="Retry attempts for node inspector")
    node_inspector_retry_delay: int = Field(default=1, description="Retry delay for node inspector")
    node_inspector_connection_pool: bool = Field(default=True, description="Enable connection pool for node inspector")
    node_inspector_pool_size: int = Field(default=10, description="Pool size for node inspector")
    node_inspector_keep_alive: bool = Field(default=True, description="Keep alive for node inspector")
    node_inspector_verbose: bool = Field(default=False, description="Verbose logging for node inspector")
    node_inspector_log_output: bool = Field(default=False, description="Log command output for node inspector")

    # GitOps configuration
    kubeeye_gitops_repo_url: Optional[str] = Field(default=None, description="GitOps repository URL")
    kubeeye_gitops_repo_name: Optional[str] = Field(default=None, description="GitOps repository name")
    kubeeye_gitops_repo_branch: str = Field(default="main", description="GitOps repository branch")
    kubeeye_gitops_repo_username: Optional[str] = Field(default=None, description="GitOps repository username")
    kubeeye_gitops_repo_token: Optional[str] = Field(default=None, description="GitOps repository token")
    kubeeye_gitops_repo_description: str = Field(default="", description="GitOps repository description")
    kubeeye_gitops_sync_interval: int = Field(
        default=300, description="GitOps sync interval in seconds (default: 5 minutes)"
    )
    git_ssl_no_verify: Optional[str] = Field(default=None, description="Disable SSL verification for Git operations")

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT secret key for token signing"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_hours: int = Field(
        default=24, description="JWT access token expiration time in hours"
    )

    # Admin user initialization
    admin_username: str = Field(default="admin", description="Admin username")
    admin_email: str = Field(default="admin@kubeeye.local", description="Admin email")
    admin_password: str = Field(
        default="admin123", description="Admin password (change in production)"
    )

    # Security settings
    max_failed_login_attempts: int = Field(default=5, description="Max failed login attempts before lock")
    account_lock_duration_minutes: int = Field(default=30, description="Account lock duration in minutes")

    # Audit configuration
    audit_enabled: bool = Field(default=True, description="Enable/disable audit logging")
    audit_retention_days: int = Field(default=14, description="Number of days to retain audit logs")


# Global settings instance
settings = Settings()
```

### 7.2 Docker Compose

```yaml
# docker-compose.yaml (обновление)
services:
  postgres:
    image: postgres:18-alpine
    environment:
      POSTGRES_USER: kubeeye
      POSTGRES_PASSWORD: kubeeye
      POSTGRES_DB: kubeeye-db
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kubeeye -d kubeeye-db"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  backend:
    build:
      context: ./backend
    ports:
      - "8000:8000"
    environment:
      # GitOps configuration
      - KUBEEYE_GITOPS_REPO_NAME=kubeeye_rules
      - KUBEEYE_GITOPS_REPO_URL=https://github.com/optical4eye/kubeeye-rules.git
      - KUBEEYE_GITOPS_REPO_BRANCH=main
      - KUBEEYE_GITOPS_REPO_USERNAME=optical4eye
      - KUBEEYE_GITOPS_REPO_TOKEN=""
      - KUBEEYE_GITOPS_REPO_DESCRIPTION=kubeeye repo rules
      - KUBEEYE_REPORT_RETENTION_DAYS=1
      - GIT_SSL_NO_VERIFY=1

      # Database configuration
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_USER=kubeeye
      - DB_PASS=kubeeye
      - DB_NAME=kubeeye-db

      # JWT configuration
      - JWT_SECRET_KEY=your-secret-key-change-in-production
      - JWT_ALGORITHM=HS256
      - JWT_ACCESS_TOKEN_EXPIRE_HOURS=24

      # Admin user configuration
      - KUBEEYE_ADMIN_USERNAME=admin
      - KUBEEYE_ADMIN_EMAIL=admin@kubeeye.local
      - KUBEEYE_ADMIN_PASSWORD=admin123

      # Security settings
      - MAX_FAILED_LOGIN_ATTEMPTS=5
      - ACCOUNT_LOCK_DURATION_MINUTES=30

      # Audit configuration
      - AUDIT_ENABLED=true
      - AUDIT_RETENTION_DAYS=14
    restart: unless-stopped
    volumes:
      - ./data:/app/data
    depends_on:
      - postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://backend:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped

networks:
  default:
    name: kubeeye-network
```

---

## 8. Документация

### 8.1 Backend README

```markdown
# Authentication and Authorization

## Overview

KubeEye implements JWT-based authentication and Role-Based Access Control (RBAC) for securing the API.

## Authentication

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@kubeeye.local",
    "role": "admin",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-01-01T12:00:00Z"
  }
}
```

### Using Access Token

```bash
curl -X GET http://localhost:8000/api/clusters \
  -H "Authorization: Bearer <access_token>"
```

### Logout

```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

## Authorization

### Roles

| Role | Description |
|------|-------------|
| `admin` | Full access to all features |
| `operator` | Read and execute inspections, limited management |

### Protected Endpoints

Most endpoints require authentication. Some endpoints require specific roles:

- **Admin only**: `/api/auth/users`, `/api/secrets`, `/api/gitops`, `/api/cleanup`
- **Operator or Admin**: `/api/clusters`, `/api/inspection`, `/api/reports`, `/api/scheduled-tasks`

## Security Features

- **Password Hashing**: bcrypt with salt
- **JWT Tokens**: Access tokens (24 hours)
- **Account Lockout**: After 5 failed login attempts (30 min lock)
- **HTTPS**: Recommended for production

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | `your-secret-key-change-in-production` | JWT signing key |
| `JWT_ACCESS_TOKEN_EXPIRE_HOURS` | `24` | Access token lifetime in hours |
| `KUBEEYE_ADMIN_USERNAME` | `admin` | Admin username |
| `KUBEEYE_ADMIN_EMAIL` | `admin@kubeeye.local` | Admin email |
| `KUBEEYE_ADMIN_PASSWORD` | `admin123` | Admin password |
| `MAX_FAILED_LOGIN_ATTEMPTS` | `5` | Max failed attempts |
| `ACCOUNT_LOCK_DURATION_MINUTES` | `30` | Lock duration |
```

### 8.2 Frontend README

```markdown
# Authentication and Authorization

## Overview

The KubeEye frontend implements JWT-based authentication with automatic token refresh and role-based access control.

## Authentication Flow

1. User enters credentials on login page
2. Frontend sends credentials to `/api/auth/login`
3. Backend returns access token
4. Token is stored in localStorage
5. Access token is included in all API requests
6. When access token expires (after 24 hours), user must re-login

## Using the Auth Store

```typescript
import { useAuthStore } from '../stores/authStore';

function MyComponent() {
  const { user, isAuthenticated, login, logout } = useAuthStore();

  const handleLogin = async () => {
    try {
      await login('username', 'password');
      // Navigate to dashboard
    } catch (error) {
      // Handle error
    }
  };

  const handleLogout = async () => {
    await logout();
    // Navigate to login
  };

  return (
    <div>
      {isAuthenticated ? (
        <p>Welcome, {user?.username}!</p>
      ) : (
        <button onClick={handleLogin}>Login</button>
      )}
    </div>
  );
}
```

## Protected Routes

Use the `ProtectedRoute` component to protect routes:

```typescript
import ProtectedRoute from '../components/ProtectedRoute';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute requiredRole="admin">
            <AdminPanel />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
```

## Role-Based Access Control

Use the `RoleBasedAccess` component to conditionally render elements:

```typescript
import RoleBasedAccess from '../components/RoleBasedAccess';

function UserList() {
  return (
    <div>
      <h1>Users</h1>

      {/* Only visible to admins */}
      <RoleBasedAccess allowedRoles={['admin']}>
        <Button type="primary">Create User</Button>
      </RoleBasedAccess>

      {/* Visible to admins and operators */}
      <RoleBasedAccess allowedRoles={['admin', 'operator']}>
        <Table dataSource={users} />
      </RoleBasedAccess>
    </div>
  );
}
```

## API Interceptor

The axios interceptor automatically:

1. Adds the access token to all requests
2. Handles 401 errors by logging out the user
3. Redirects to login page on 401 errors

## Token Storage

Access token is stored in localStorage:

```typescript
import { tokenStorage } from '../utils/tokenStorage';

// Get access token
const accessToken = tokenStorage.getAccessToken();

// Check if token exists
const hasToken = tokenStorage.hasToken();

// Clear token
tokenStorage.clearTokens();
```

## Security Best Practices

1. **Change default admin password** in production
2. **Use HTTPS** in production
3. **Set secure JWT secret key**
4. **Implement proper logout** on browser close
5. **Use appropriate access token lifetime** (default: 24 hours)
6. **Implement CSRF protection** if needed
```

---

## 9. Будущее расширение

### 9.1 LDAP интеграция (заготовки)

```python
# backend/app/services/ldap_service.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LDAP authentication service (placeholder for future implementation)
"""

from typing import Optional, Dict, Any
from core.logging import get_logger

logger = get_logger(__name__)


class LDAPService:
    """LDAP authentication service"""

    def __init__(self):
        self.enabled = False
        self.ldap_server = None
        self.ldap_port = None
        self.ldap_base_dn = None
        self.ldap_user_dn = None

    async def authenticate(
        self,
        username: str,
        password: str
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate user via LDAP

        Args:
            username: Username
            password: Password

        Returns:
            User data if authentication successful, None otherwise
        """
        # TODO: Implement LDAP authentication
        logger.warning("LDAP authentication not implemented yet")
        return None

    async def get_user_groups(self, username: str) -> list[str]:
        """
        Get user groups from LDAP

        Args:
            username: Username

        Returns:
            List of group names
        """
        # TODO: Implement LDAP group lookup
        logger.warning("LDAP group lookup not implemented yet")
        return []

    async def sync_user_from_ldap(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Sync user data from LDAP

        Args:
            username: Username

        Returns:
            User data
        """
        # TODO: Implement LDAP user sync
        logger.warning("LDAP user sync not implemented yet")
        return None


# Global LDAP service instance
ldap_service = LDAPService()
```

### 9.2 Разрешения (permissions)

```python
# backend/app/core/security/permissions.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Permission system for fine-grained access control (placeholder for future implementation)
"""

from typing import List, Dict, Set
from enum import Enum
from core.logging import get_logger

logger = get_logger(__name__)


class Permission(Enum):
    """Permission enum"""
    # Cluster permissions
    CLUSTER_READ = "cluster:read"
    CLUSTER_CREATE = "cluster:create"
    CLUSTER_UPDATE = "cluster:update"
    CLUSTER_DELETE = "cluster:delete"

    # Inspection permissions
    INSPECTION_READ = "inspection:read"
    INSPECTION_RUN = "inspection:run"
    INSPECTION_DELETE = "inspection:delete"

    # Report permissions
    REPORT_READ = "report:read"
    REPORT_DELETE = "report:delete"
    REPORT_EXPORT = "report:export"

    # Secret permissions
    SECRET_READ = "secret:read"
    SECRET_CREATE = "secret:create"
    SECRET_UPDATE = "secret:update"
    SECRET_DELETE = "secret:delete"

    # User permissions
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Rule permissions
    RULE_READ = "rule:read"
    RULE_UPDATE = "rule:update"

    # GitOps permissions
    GITOPS_READ = "gitops:read"
    GITOPS_UPDATE = "gitops:update"
    GITOPS_SYNC = "gitops:sync"

    # Scheduled task permissions
    TASK_READ = "task:read"
    TASK_CREATE = "task:create"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_RUN = "task:run"

    # Network check permissions
    NETWORK_READ = "network:read"
    NETWORK_RUN = "network:run"

    # Cleanup permissions
    CLEANUP_RUN = "cleanup:run"
    CLEANUP_CONFIG = "cleanup:config"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    "admin": {
        # All permissions
        Permission.CLUSTER_READ,
        Permission.CLUSTER_CREATE,
        Permission.CLUSTER_UPDATE,
        Permission.CLUSTER_DELETE,
        Permission.INSPECTION_READ,
        Permission.INSPECTION_RUN,
        Permission.INSPECTION_DELETE,
        Permission.REPORT_READ,
        Permission.REPORT_DELETE,
        Permission.REPORT_EXPORT,
        Permission.SECRET_READ,
        Permission.SECRET_CREATE,
        Permission.SECRET_UPDATE,
        Permission.SECRET_DELETE,
        Permission.USER_READ,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.RULE_READ,
        Permission.RULE_UPDATE,
        Permission.GITOPS_READ,
        Permission.GITOPS_UPDATE,
        Permission.GITOPS_SYNC,
        Permission.TASK_READ,
        Permission.TASK_CREATE,
        Permission.TASK_UPDATE,
        Permission.TASK_DELETE,
        Permission.TASK_RUN,
        Permission.NETWORK_READ,
        Permission.NETWORK_RUN,
        Permission.CLEANUP_RUN,
        Permission.CLEANUP_CONFIG,
    },
    "operator": {
        # Limited permissions
        Permission.CLUSTER_READ,
        Permission.CLUSTER_CREATE,
        Permission.CLUSTER_UPDATE,
        Permission.CLUSTER_DELETE,
        Permission.INSPECTION_READ,
        Permission.INSPECTION_RUN,
        Permission.REPORT_READ,
        Permission.REPORT_EXPORT,
        Permission.TASK_READ,
        Permission.TASK_CREATE,
        Permission.TASK_UPDATE,
        Permission.TASK_DELETE,
        Permission.TASK_RUN,
        Permission.NETWORK_READ,
        Permission.NETWORK_RUN,
    }
}


class PermissionService:
    """Service for permission checking"""

    @staticmethod
    def has_permission(role: str, permission: Permission) -> bool:
        """
        Check if role has permission

        Args:
            role: User role
            permission: Permission to check

        Returns:
            True if role has permission, False otherwise
        """
        permissions = ROLE_PERMISSIONS.get(role, set())
        return permission in permissions

    @staticmethod
    def has_any_permission(role: str, permissions: List[Permission]) -> bool:
        """
        Check if role has any of the specified permissions

        Args:
            role: User role
            permissions: List of permissions to check

        Returns:
            True if role has any permission, False otherwise
        """
        role_permissions = ROLE_PERMISSIONS.get(role, set())
        return any(perm in role_permissions for perm in permissions)

    @staticmethod
    def has_all_permissions(role: str, permissions: List[Permission]) -> bool:
        """
        Check if role has all of the specified permissions

        Args:
            role: User role
            permissions: List of permissions to check

        Returns:
            True if role has all permissions, False otherwise
        """
        role_permissions = ROLE_PERMISSIONS.get(role, set())
        return all(perm in role_permissions for perm in permissions)


# Global permission service instance
permission_service = PermissionService()
```

### 9.3 Аудит действий

```python
# backend/app/services/audit_service.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit service for tracking user actions (placeholder for future implementation)
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from core.logging import get_logger

logger = get_logger(__name__)


class AuditAction:
    """Audit action types"""
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    CLUSTER_CREATE = "cluster_create"
    CLUSTER_UPDATE = "cluster_update"
    CLUSTER_DELETE = "cluster_delete"
    INSPECTION_RUN = "inspection_run"
    REPORT_EXPORT = "report_export"
    SECRET_CREATE = "secret_create"
    SECRET_UPDATE = "secret_update"
    SECRET_DELETE = "secret_delete"


class AuditService:
    """Service for audit logging"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_action(
        self,
        user_id: int,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log user action

        Args:
            user_id: User ID
            action: Action type
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional details
            ip_address: Client IP address
            user_agent: Client user agent
        """
        # TODO: Implement audit logging to database
        logger.info(
            f"Audit: user_id={user_id}, action={action}, "
            f"resource_type={resource_type}, resource_id={resource_id}"
        )

    async def get_user_audit_log(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> list[Dict[str, Any]]:
        """
        Get audit log for user

        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Offset for pagination

        Returns:
            List of audit records
        """
        # TODO: Implement audit log retrieval
        logger.warning("Audit log retrieval not implemented yet")
        return []

    async def get_resource_audit_log(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[Dict[str, Any]]:
        """
        Get audit log for resource

        Args:
            resource_type: Type of resource
            resource_id: ID of resource
            limit: Maximum number of records
            offset: Offset for pagination

        Returns:
            List of audit records
        """
        # TODO: Implement audit log retrieval
        logger.warning("Audit log retrieval not implemented yet")
        return []
```

---

## 10. Порядок реализации (6 этапов)

### Этап 1: Базовая инфраструктура (Backend)

**Задачи:**
1. Создать модель данных (`User`)
2. Создать репозиторий (`UserRepository`)
4. Добавить зависимости в `requirements.txt`
5. Обновить конфигурацию (`settings.py`)

**Файлы:**
- `backend/app/db/models/user.py`
- `backend/app/db/repositories/user_repository.py`
- `backend/app/db/migrations/002_add_auth_tables.py`
- `backend/requirements.txt` (дополнение)
- `backend/app/core/config/settings.py` (дополнение)

**Зависимости:**
```txt
python-jose[cryptography]>=3.5.0
pwdlib>=0.3.0
python-multipart>=0.0.22
```

**Время:** ~3 часа

---

### Этап 2: Сервисы аутентификации (Backend)

**Задачи:**
1. Создать `PasswordService`
2. Создать `JWTUtils`
3. Создать `AuthService`
4. Создать Pydantic модели для аутентификации
5. Создать зависимости для FastAPI (`get_current_user`, `require_admin`, `require_operator`)

**Файлы:**
- `backend/app/core/security/password_service.py`
- `backend/app/core/security/jwt_utils.py`
- `backend/app/services/auth_service.py`
- `backend/app/api/models.py` (дополнение)
- `backend/app/api/dependencies.py`

**Время:** ~3 часа

---

### Этап 3: API эндпоинты аутентификации (Backend)

**Задачи:**
1. Создать роутер `/api/auth`
2. Реализовать эндпоинты: login, logout, change-password, me
3. Реализовать admin-only эндпоинты: users (CRUD)
4. Добавить роутер в `main.py`
5. Создать скрипт инициализации admin пользователя
6. Интегрировать инициализацию в startup

**Файлы:**
- `backend/app/api/auth.py`
- `backend/app/api/main.py` (дополнение)
- `backend/app/scripts/init_admin.py`
- `backend/app/api/startup.py` (дополнение)

**Время:** ~3 часа

---

### Этап 4: Защита существующих эндпоинтов (Backend)

**Задачи:**
1. Создать middleware для аутентификации
2. Добавить зависимости к защищенным эндпоинтам
3. Обновить все роутеры с авторизацией
4. Тестирование защиты эндпоинтов

**Файлы:**
- `backend/app/api/auth_middleware.py`
- `backend/app/api/clusters.py` (обновление)
- `backend/app/api/inspection.py` (обновление)
- `backend/app/api/reports.py` (обновление)
- `backend/app/api/rules.py` (обновление)
- `backend/app/api/secrets.py` (обновление)
- `backend/app/api/gitops.py` (обновление)
- `backend/app/api/scheduled_tasks.py` (обновление)
- `backend/app/api/network.py` (обновление)
- `backend/app/api/popeye.py` (обновление)
- `backend/app/api/report_cleanup.py` (обновление)
- `backend/app/api/queue_endpoints.py` (обновление)

**Время:** ~6 часов

---

### Этап 5: Frontend интеграция

**Задачи:**
1. Создать утилиты для хранения токенов
2. Создать Zustand store для аутентификации
3. Создать axios interceptor
4. Создать страницу входа
5. Создать компонент `ProtectedRoute`
6. Создать компонент `UserMenu`
7. Создать страницу смены пароля
8. Создать компонент `RoleBasedAccess`
9. Обновить роутинг с защитой
10. Добавить UserMenu в layout

**Файлы:**
- `frontend/src/utils/tokenStorage.ts`
- `frontend/src/stores/authStore.ts`
- `frontend/src/services/api.ts` (обновление)
- `frontend/src/pages/Login.tsx`
- `frontend/src/components/ProtectedRoute.tsx`
- `frontend/src/components/UserMenu.tsx`
- `frontend/src/pages/ChangePassword.tsx`
- `frontend/src/components/RoleBasedAccess.tsx`
- `frontend/src/App.tsx` (обновление)
- `frontend/src/pages/Dashboard.tsx` (обновление)

**Время:** ~6 часов

---

### Этап 6: Система аудита (Backend + Frontend)

**Задачи:**
1. Создать модель данных `AuditLog`
2. Создать репозиторий `AuditLogRepository`
3. Создать сервис `AuditService`
4. Создать API эндпоинты для аудита
5. Создать `AuditMiddleware`
7. Создать Frontend страницу `AuditLogs`
8. Добавить ссылку на страницу аудита в меню
9. Интегрировать AuditMiddleware в приложение
10. Настроить автоматическую очистку старых логов
11. Тестирование системы аудита

**Файлы:**
- `backend/app/db/models/audit_log.py`
- `backend/app/db/repositories/audit_log_repository.py`
- `backend/app/services/audit_service.py`
- `backend/app/api/auth.py` (дополнение - audit endpoints)
- `backend/app/api/auth_middleware.py` (дополнение - AuditMiddleware)
- `backend/app/db/migrations/003_add_audit_log_table.py`
- `backend/app/core/config/settings.py` (дополнение - audit config)
- `frontend/src/pages/AuditLogs.tsx`
- `frontend/src/App.tsx` (дополнение - audit route)
- `frontend/src/components/Layout.tsx` (дополнение - audit menu item)

**Время:** ~6 часов

---

### Итого: ~26 часов (3.25 рабочих дня)

---

## 11. Безопасность

### 11.1 Аудит

| Функция | Описание |
|----------|----------|
| **Логирование действий** | Все действия пользователей логируются в audit_log |
| **Автоматическая очистка** | Старые логи удаляются автоматически (по умолчанию 14 дней) |
| **Доступ к логам** | Только администраторы могут просматривать audit логи |
| **Фильтрация и поиск** | Возможность фильтрации по пользователю, действию, ресурсу, статусу, дате |
| **Статистика** | Агрегированная статистика по действиям, пользователям, ресурсам |
| **Детали лога** | Полная информация о каждом действии в модальном окне |

#### 11.1.1 Типы действий для аудита

| Категория | Действия |
|-----------|----------|
| **Аутентификация** | login, logout, password_change |
| **Пользователи** | user_create, user_update, user_delete |
| **Кластеры** | cluster_create, cluster_update, cluster_delete |
| **Инспекции** | inspection_run, inspection_delete |
| **Отчеты** | report_view, report_export, report_delete |
| **Секреты** | secret_create, secret_update, secret_delete |
| **Правила** | rule_update |
| **GitOps** | gitops_sync |
| **Задачи** | task_create, task_update, task_delete, task_run |
| **Сеть** | network_check |
| **Popeye** | popeye_scan |
| **Очистка** | cleanup_run, queue_clear |

#### 11.1.2 Поля audit лога

| Поле | Тип | Описание |
|-------|------|----------|
| `id` | UUID | Уникальный идентификатор лога |
| `user_id` | UUID | ID пользователя |
| `username` | VARCHAR(50) | Имя пользователя |
| `action` | VARCHAR(50) | Тип действия |
| `resource_type` | VARCHAR(50) | Тип ресурса |
| `resource_id` | VARCHAR(255) | ID ресурса |
| `details` | JSONB | Дополнительные детали |
| `ip_address` | VARCHAR(45) | IP адрес пользователя |
| `user_agent` | VARCHAR(500) | User Agent браузера |
| `status` | VARCHAR(20) | Статус действия (success/failure) |
| `error_message` | TEXT | Сообщение об ошибке |
| `created_at` | TIMESTAMP | Время создания записи |

#### 11.1.3 API эндпоинты аудита

| Эндпоинт | Метод | Роль | Описание |
|-----------|-------|------|----------|
| `/api/auth/audit/logs` | GET | Admin | Получение списка audit логов с фильтрацией и пагинацией |
| `/api/auth/audit/logs/{id}` | GET | Admin | Получение audit лога по ID |
| `/api/auth/audit/stats` | GET | Admin | Получение статистики аудита |
| `/api/auth/audit/cleanup` | POST | Admin | Очистка старых audit логов |

#### 11.1.4 Переменные окружения для аудита

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `AUDIT_ENABLED` | `true` | Включение/выключение аудита |
| `AUDIT_RETENTION_DAYS` | `14` | Период хранения audit логов в днях |

### 11.2 Пароли

| Мера | Реализация |
|------|------------|
| **Хеширование** | bcrypt через pwdlib с автоматической генерацией соли |
| **Сложность** | Минимум 6 символов (настраивается) |
| **Валидация** | Проверка сложности на frontend и backend |
| **Смена пароля** | Требует старый пароль |
| **История паролей** | Не хранится (можно добавить в будущем) |

### 11.3 JWT токены

| Параметр | Значение | Описание |
|----------|----------|----------|
| **Алгоритм** | HS256 | HMAC SHA-256 |
| **Secret Key** | Настраивается через `JWT_SECRET_KEY` | Должен быть уникальным для production |
| **Access Token TTL** | 24 часа | Долгое время жизни для удобства |
| **Хранение** | localStorage (access token) | Клиентское хранение |
| **Автоматическое обновление** | Не требуется | Пользователь должен перезайти после истечения токена |

### 11.4 HTTPS

| Рекомендация | Статус |
|-------------|--------|
| **Использование HTTPS** | Обязательно для production |
| **TLS сертификаты** | Let's Encrypt или собственные |
| **HSTS** | Рекомендуется включить |
| **Secure cookies** | Если используются cookies вместо localStorage |

### 11.5 Rate limiting

| Эндпоинт | Лимит | Период |
|----------|-------|--------|
| `/api/auth/login` | 5 запросов | 15 минут |
| `/api/auth/register` | 3 запроса | 1 час |
| `/api/auth/change-password` | 3 запроса | 1 час |
| **Остальные API** | 100 запросов | 1 минута |

### 11.6 Дополнительные меры безопасности

| Действие | Логирование |
|----------|-------------|
| **Успешный вход** | ✅ Да |
| **Неудачный вход** | ✅ Да |
| **Выход** | ✅ Да |
| **Смена пароля** | ✅ Да |
| **Создание пользователя** | ✅ Да |
| **Удаление пользователя** | ✅ Да |
| **Запуск инспекции** | ✅ Да |
| **Экспорт отчета** | ✅ Да |
| **Управление секретами** | ✅ Да |

### 11.6 Дополнительные меры безопасности

| Мера | Описание |
|------|----------|
| **Блокировка аккаунта** | После 5 неудачных попыток входа (30 минут) |
| **IP-логирование** | Запись IP адресов при входе |
| **User-Agent логирование** | Запись User-Agent при входе |
| **CORS** | Настройка CORS для production |
| **CSRF защита** | Рекомендуется добавить в будущем |
| **XSS защита** | Автоматическая в React |
| **SQL Injection** | Защита через SQLAlchemy |
| **Валидация входных данных** | Pydantic модели |

---

## Заключение

Этот документ предоставляет полный план реализации ролевой модели и аутентификации для проекта KubeEye. План включает:

1. ✅ Полный анализ текущей архитектуры
2. ✅ Детальную модель данных с SQLAlchemy
3. ✅ JWT-базированную систему аутентификации
4. ✅ RBAC систему авторизации
5. ✅ Инициализацию admin пользователя
6. ✅ Полную интеграцию с Frontend
7. ✅ Конфигурацию для Docker
8. ✅ Документацию
9. ✅ Заготовки для будущего расширения (LDAP, permissions, audit)
10. ✅ Порядок реализации в 6 этапов
11. ✅ Комплексные меры безопасности

Следуя этому плану, можно реализовать надежную систему аутентификации и авторизации для KubeEye за ~32 часа (4 рабочих дня).
