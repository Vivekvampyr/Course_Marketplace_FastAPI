# Replace this:
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add these imports at the top:
import os
import sys
sys.path.append(os.getcwd())

from app.database import Base
from app.config import settings

# ── Import all models so Alembic detects them ─────────
from app.models import user, course, lecture, enrollment, cart, order, review, chat

# Replace target_metadata line:
target_metadata = Base.metadata