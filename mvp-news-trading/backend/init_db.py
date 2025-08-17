#!/usr/bin/env python3
"""
Initialize database tables
"""
from database import engine, Base
from models import Signal, Trade, Portfolio
from loguru import logger

def init_database():
    """Create all database tables"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.success("Database tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        return False

if __name__ == "__main__":
    init_database()