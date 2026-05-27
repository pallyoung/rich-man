"""SQLite-based caching service for API responses."""

import json
import sqlite3
import time
import logging
import os

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache.db')


def _get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the cache table if it doesn't exist."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at REAL NOT NULL,
                ttl_seconds REAL NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_created_at
            ON cache(created_at)
        ''')
        conn.commit()
        conn.close()
        logger.info("Cache database initialized at %s", DB_PATH)
    except Exception as e:
        logger.error("Failed to initialize cache database: %s", e)
        raise


def get_cached(key: str, max_age_seconds: float = None):
    """Retrieve cached data if it exists and hasn't expired.

    Args:
        key: Cache key.
        max_age_seconds: Maximum age in seconds. If None, uses the TTL
                         stored with the cached entry.

    Returns:
        Cached data (deserialized JSON), or None if not found or expired.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT data, created_at, ttl_seconds FROM cache WHERE key = ?',
            (key,)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        created_at = row['created_at']
        ttl_seconds = row['ttl_seconds']
        data_str = row['data']

        # Check expiration
        effective_ttl = max_age_seconds if max_age_seconds is not None else ttl_seconds
        if time.time() - created_at > effective_ttl:
            # Expired, remove it
            _delete_cached(key)
            return None

        return json.loads(data_str)
    except json.JSONDecodeError as e:
        logger.error("Failed to decode cached data for key '%s': %s", key, e)
        return None
    except Exception as e:
        logger.error("Cache read error for key '%s': %s", key, e)
        return None


def set_cached(key: str, data, ttl_seconds: float = 300):
    """Store data in the cache with a TTL.

    Args:
        key: Cache key.
        data: Data to cache (must be JSON-serializable).
        ttl_seconds: Time to live in seconds (default 5 minutes).
    """
    try:
        data_str = json.dumps(data, ensure_ascii=False, default=str)
        created_at = time.time()

        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT OR REPLACE INTO cache (key, data, created_at, ttl_seconds)
               VALUES (?, ?, ?, ?)''',
            (key, data_str, created_at, ttl_seconds)
        )
        conn.commit()
        conn.close()
        logger.debug("Cached data for key '%s' with TTL %ds", key, ttl_seconds)
    except Exception as e:
        logger.error("Cache write error for key '%s': %s", key, e)


def _delete_cached(key: str):
    """Delete a cached entry."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Cache delete error for key '%s': %s", key, e)


def clear_expired():
    """Remove all expired cache entries."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM cache WHERE (? - created_at) > ttl_seconds',
            (time.time(),)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            logger.info("Cleared %d expired cache entries", deleted)
    except Exception as e:
        logger.error("Failed to clear expired cache: %s", e)


def clear_all():
    """Clear all cache entries."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cache')
        conn.commit()
        conn.close()
        logger.info("All cache entries cleared")
    except Exception as e:
        logger.error("Failed to clear cache: %s", e)
