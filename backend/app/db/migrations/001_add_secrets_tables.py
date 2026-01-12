#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database migration for adding secrets management tables

This migration adds:
1. encryption_keys table - for storing encryption keys
2. secrets table - for storing encrypted secrets
3. Updates clusters table - adds secret reference fields
"""

from sqlalchemy import text
from db.database import get_db
from core.logging import get_logger

logger = get_logger(__name__)


def upgrade():
    """Apply the migration"""
    db = next(get_db())

    try:
        # Create encryption_keys table
        create_encryption_keys_table = """
        CREATE TABLE IF NOT EXISTS encryption_keys (
            id SERIAL PRIMARY KEY,
            key_name VARCHAR(255) UNIQUE NOT NULL,
            encryption_key TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_encryption_keys_key_name ON encryption_keys(key_name);
        CREATE INDEX IF NOT EXISTS idx_encryption_keys_is_active ON encryption_keys(is_active);
        """

        db.execute(text(create_encryption_keys_table))
        logger.info("Created encryption_keys table")

        # Create secrets table
        create_secrets_table = """
        CREATE TABLE IF NOT EXISTS secrets (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            description TEXT,
            secret_type VARCHAR(50) NOT NULL,
            encrypted_data TEXT NOT NULL,
            metadata JSONB,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_secrets_name ON secrets(name);
        CREATE INDEX IF NOT EXISTS idx_secrets_secret_type ON secrets(secret_type);
        CREATE INDEX IF NOT EXISTS idx_secrets_is_active ON secrets(is_active);
        CREATE INDEX IF NOT EXISTS idx_secrets_created_at ON secrets(created_at);
        CREATE INDEX IF NOT EXISTS idx_secrets_name_type ON secrets(name, secret_type);
        """

        db.execute(text(create_secrets_table))
        logger.info("Created secrets table")

        # Add secret reference columns to clusters table
        add_cluster_columns = """
        ALTER TABLE clusters
        ADD COLUMN IF NOT EXISTS password_secret_id INTEGER REFERENCES secrets(id),
        ADD COLUMN IF NOT EXISTS ssh_key_secret_id INTEGER REFERENCES secrets(id),
        ADD COLUMN IF NOT EXISTS kubeconfig_secret_id INTEGER REFERENCES secrets(id);

        CREATE INDEX IF NOT EXISTS idx_clusters_password_secret ON clusters(password_secret_id);
        CREATE INDEX IF NOT EXISTS idx_clusters_ssh_key_secret ON clusters(ssh_key_secret_id);
        CREATE INDEX IF NOT EXISTS idx_clusters_kubeconfig_secret ON clusters(kubeconfig_secret_id);
        """

        db.execute(text(add_cluster_columns))
        logger.info("Added secret reference columns to clusters table")

        # Create audit log table for secret operations
        create_audit_log_table = """
        CREATE TABLE IF NOT EXISTS secret_audit_log (
            id SERIAL PRIMARY KEY,
            secret_id INTEGER REFERENCES secrets(id),
            action VARCHAR(50) NOT NULL,
            user_id VARCHAR(255),
            ip_address VARCHAR(45),
            details JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_secret_audit_log_secret_id ON secret_audit_log(secret_id);
        CREATE INDEX IF NOT EXISTS idx_secret_audit_log_action ON secret_audit_log(action);
        CREATE INDEX IF NOT EXISTS idx_secret_audit_log_created_at ON secret_audit_log(created_at);
        """

        db.execute(text(create_audit_log_table))
        logger.info("Created secret_audit_log table")

        db.commit()
        logger.info("Migration completed successfully")

    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        db.close()


def downgrade():
    """Rollback the migration"""
    db = next(get_db())

    try:
        # Drop audit log table
        db.execute(text("DROP TABLE IF EXISTS secret_audit_log CASCADE;"))
        logger.info("Dropped secret_audit_log table")

        # Remove secret reference columns from clusters table
        db.execute(text("""
            ALTER TABLE clusters
            DROP COLUMN IF EXISTS password_secret_id,
            DROP COLUMN IF EXISTS ssh_key_secret_id,
            DROP COLUMN IF EXISTS kubeconfig_secret_id;
        """))
        logger.info("Removed secret reference columns from clusters table")

        # Drop secrets table
        db.execute(text("DROP TABLE IF EXISTS secrets CASCADE;"))
        logger.info("Dropped secrets table")

        # Drop encryption_keys table
        db.execute(text("DROP TABLE IF EXISTS encryption_keys CASCADE;"))
        logger.info("Dropped encryption_keys table")

        db.commit()
        logger.info("Rollback completed successfully")

    except Exception as e:
        db.rollback()
        logger.error(f"Rollback failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
