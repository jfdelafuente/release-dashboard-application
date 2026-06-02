"""
API Routes Package
Contains all route handlers for the CSV Upload API
"""

from .upload import router as upload_router

__all__ = ['upload_router']
