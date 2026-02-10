#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to initialize admin user
"""

import asyncio
from db.database import get_db
from db.repositories.user_repository import UserRepository
from db.models.user import UserRole
from core.security.password_service import password_service
from core.config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


async def init_admin_user():
    """
    Initialize admin user if not exists
    """
    async for session in get_db():
        user_repo = UserRepository(session)

        # Check if admin user exists
        admin_user = await user_repo.get_by_username(settings.kubeeye_admin_username)

        if admin_user:
            logger.info(f"Admin user '{settings.kubeeye_admin_username}' already exists")
            return admin_user

        # Create admin user
        password_hash = password_service.hash_password(settings.kubeeye_admin_password)

        admin_user = await user_repo.create(
            {
                "username": settings.kubeeye_admin_username,
                "email": settings.kubeeye_admin_email,
                "password_hash": password_hash,
                "role": UserRole.ADMIN,
                "is_active": True,
            }
        )

        logger.info(f"Admin user '{settings.kubeeye_admin_username}' created successfully")
        logger.warning(f"Default admin password: {settings.kubeeye_admin_password}")
        logger.warning("Please change the default admin password in production!")

        return admin_user


async def main():
    """Main function"""
    logger.info("Initializing admin user...")
    await init_admin_user()
    logger.info("Admin user initialization completed")


if __name__ == "__main__":
    asyncio.run(main())
