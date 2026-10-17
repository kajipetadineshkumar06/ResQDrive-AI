# ==========================================
# MODEL COMPATIBILITY IMPORT
# ==========================================

"""
This module does NOT define database models.

The User model is defined only once in:
    models/user.py

This file re-exports User so existing code such as:

    from models.models import User

continues to work.
"""

from models.user import User


__all__ = [
    "User"
]