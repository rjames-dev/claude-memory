#!/usr/bin/env python3
"""
Claude Memory - Database Utilities

Standardized database connection functions for all Python scripts.
Ensures consistent password retrieval and connection handling.

Usage:
    from db_utils import get_db_connection

    conn = get_db_connection()
    cur = conn.cursor()
    # ... use connection
    conn.close()
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_password():
    """
    Get database password from environment or .env file.

    Priority:
    1. CONTEXT_DB_PASSWORD environment variable
    2. .env file in script directory
    3. Fallback to 'memory_secure_2024'

    Returns:
        str: Database password
    """
    # Try environment variable first
    password = os.environ.get('CONTEXT_DB_PASSWORD')
    if password:
        return password

    # Try reading from .env file
    # Look in current directory and parent directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_file = os.path.join(current_dir, '.env')

    if os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('CONTEXT_DB_PASSWORD='):
                        # Handle both quoted and unquoted values
                        password = line.split('=', 1)[1]
                        # Remove quotes if present
                        password = password.strip('"').strip("'")
                        if password:
                            return password
        except Exception as e:
            print(f"Warning: Failed to read .env file: {e}", file=sys.stderr)

    # Fallback (should match default in .env.example)
    return 'memory_secure_2024'


def get_db_connection(cursor_factory=None):
    """
    Create a standardized database connection.

    Args:
        cursor_factory: Optional cursor factory (e.g., RealDictCursor)

    Returns:
        psycopg2.connection: Database connection

    Raises:
        SystemExit: If connection fails

    Environment Variables:
        DB_HOST: Database host (default: localhost)
        DB_PORT: Database port (default: 5435)
        CONTEXT_DB_PASSWORD: Database password (required)
    """
    db_config = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': int(os.environ.get('DB_PORT', '5435')),
        'database': 'claude_memory',
        'user': 'memory_admin',
        'password': get_db_password()
    }

    if cursor_factory:
        db_config['cursor_factory'] = cursor_factory

    try:
        return psycopg2.connect(**db_config)
    except psycopg2.Error as e:
        print(f"❌ Database connection failed: {e}", file=sys.stderr)
        print(f"   Host: {db_config['host']}:{db_config['port']}", file=sys.stderr)
        print(f"   Database: {db_config['database']}", file=sys.stderr)
        print(f"   User: {db_config['user']}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"   Check:", file=sys.stderr)
        print(f"   1. Docker containers running: docker-compose ps", file=sys.stderr)
        print(f"   2. Password in .env matches database", file=sys.stderr)
        print(f"   3. Database initialized: docker logs claude-context-db", file=sys.stderr)
        sys.exit(1)


def test_connection():
    """
    Test database connection and print status.

    Returns:
        bool: True if connection successful
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Test query
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]

        # Get table count
        cur.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        table_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        print("✅ Database connection successful")
        print(f"   Version: {version.split(',')[0]}")
        print(f"   Tables: {table_count}")
        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == '__main__':
    """Test database connection when run directly."""
    print("Testing database connection...")
    print()
    test_connection()
