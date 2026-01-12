# Database module initialization

# Import all models to ensure they are registered with SQLAlchemy
from . import models

from db.database import init_database

__all__ = ["init_database"]
