#!/usr/bin/env python3
"""
Run database migration script

Usage:
    python run_migrations.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.migrations import run_migrations

if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration Tool")
    print("=" * 60)
    run_migrations()

