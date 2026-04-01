"""
Storage Abstraction Layer for AdFlow Studio
============================================
Provides a unified interface for data persistence with graceful fallback:

- Neon Postgres  → Users & Brands (set DATABASE_URL env var)
- Upstash Redis  → Auth sessions/tokens (auto-detected from Vercel integration or manual env vars)
- Vercel Blob    → Report files (set BLOB_READ_WRITE_TOKEN)

If env vars are not configured, falls back to the original /tmp file-based storage.
"""

import json
import os
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Feature Flags ──────────────────────────────────────────────────────
# Neon Postgres: Vercel integration creates DATABASE_POSTGRES_URL (with prefix "DATABASE")
# but manual setup might use DATABASE_URL — support both patterns
_DATABASE_URL = os.environ.get("DATABASE_POSTGRES_URL") or os.environ.get("DATABASE_URL") or ""
USE_POSTGRES = bool(_DATABASE_URL)
# Upstash Redis: Vercel integration creates vars like UPSTASH_REDIS_REST_KV_REST_API_URL
# but manual setup might use UPSTASH_REDIS_REST_URL — support both patterns
_REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL") or ""
_REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN") or ""
USE_REDIS = bool(_REDIS_URL) and bool(_REDIS_TOKEN)
USE_BLOB = bool(os.environ.get("BLOB_READ_WRITE_TOKEN"))

logger.info(f"Storage backends: Postgres={USE_POSTGRES}, Redis={USE_REDIS}, Blob={USE_BLOB}")


# ══════════════════════════════════════════════════════════════════════
# POSTGRES — Users & Brands
# ══════════════════════════════════════════════════════════════════════

_pg_pool = None

def _get_pg():
    """Get a psycopg2 connection (pooled)."""
    global _pg_pool
    if _pg_pool is None:
        import psycopg2
        import psycopg2.pool
        # Use a small pool — serverless functions are short-lived
        _pg_pool = psycopg2.pool.SimpleConnectionPool(1, 5, _DATABASE_URL)
    return _pg_pool.getconn()


def _put_pg(conn):
    """Return a connection to the pool."""
    if _pg_pool:
        _pg_pool.putconn(conn)


def init_postgres():
    """Create tables if they don't exist."""
    if not USE_POSTGRES:
        return
    conn = _get_pg()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'viewer',
                assigned_brands JSONB DEFAULT '[]',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS brands (
                slug TEXT PRIMARY KEY,
                data JSONB NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports_meta (
                id SERIAL PRIMARY KEY,
                brand_slug TEXT NOT NULL,
                report_type TEXT NOT NULL,
                format TEXT NOT NULL,
                blob_url TEXT,
                filename TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
        logger.info("Postgres tables initialized")
    except Exception as e:
        conn.rollback()
        logger.error(f"Postgres init error: {e}")
    finally:
        _put_pg(conn)


# ── User CRUD (Postgres) ──────────────────────────────────────────────

def pg_load_users():
    """Load all users from Postgres as {id: user_dict}."""
    conn = _get_pg()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, name, password_hash, role, assigned_brands, created_at FROM users")
        rows = cur.fetchall()
        users = {}
        for r in rows:
            users[r[0]] = {
                "id": r[0], "email": r[1], "name": r[2],
                "password_hash": r[3], "role": r[4],
                "assigned_brands": r[5] if r[5] else [],
                "created_at": r[6].isoformat() if r[6] else ""
            }
        return users
    except Exception as e:
        logger.error(f"pg_load_users error: {e}")
        return {}
    finally:
        _put_pg(conn)


def pg_save_user(user_id, user):
    """Upsert a single user to Postgres."""
    conn = _get_pg()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (id, email, name, password_hash, role, assigned_brands, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                assigned_brands = EXCLUDED.assigned_brands
        """, (
            user_id, user["email"], user["name"], user["password_hash"],
            user.get("role", "viewer"),
            json.dumps(user.get("assigned_brands", [])),
            user.get("created_at", datetime.now().isoformat())
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"pg_save_user error: {e}")
    finally:
        _put_pg(conn)


def pg_get_user_by_email(email):
    """Get a single user by email from Postgres."""
    conn = _get_pg()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, name, password_hash, role, assigned_brands, created_at FROM users WHERE email = %s", (email,))
        r = cur.fetchone()
        if r:
            return {
                "id": r[0], "email": r[1], "name": r[2],
                "password_hash": r[3], "role": r[4],
                "assigned_brands": r[5] if r[5] else [],
                "created_at": r[6].isoformat() if r[6] else ""
            }
        return None
    except Exception as e:
        logger.error(f"pg_get_user_by_email error: {e}")
        return None
    finally:
        _put_pg(conn)


def pg_get_user_by_id(user_id):
    """Get a single user by ID from Postgres."""
    conn = _get_pg()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, name, password_hash, role, assigned_brands, created_at FROM users WHERE id = %s", (user_id,))
        r = cur.fetchone()
        if r:
            return {
                "id": r[0], "email": r[1], "name": r[2],
                "password_hash": r[3], "role": r[4],
                "assigned_brands": r[5] if r[5] else [],
                "created_at": r[6].isoformat() if r[6] else ""
            }
        return None
    except Exception as e:
        logger.error(f"pg_get_user_by_id error: {e}")
        return None
    finally:
        _put_pg(conn)


# ── Brands CRUD (Postgres) ────────────────────────────────────────────

def pg_load_brands():
    """Load all brands from Postgres as the brands.json format."""
    conn = _get_pg()
    try:
        cur = conn.cursor()
        cur.execute("SELECT slug, data FROM brands")
        rows = cur.fetchall()
        brands = {}
        for r in rows:
            brands[r[0]] = r[1]
        return {"brands": brands}
    except Exception as e:
        logger.error(f"pg_load_brands error: {e}")
        return {"brands": {}}
    finally:
        _put_pg(conn)


def pg_save_brand(slug, data):
    """Upsert a single brand to Postgres."""
    conn = _get_pg()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO brands (slug, data, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (slug) DO UPDATE SET
                data = EXCLUDED.data,
                updated_at = NOW()
        """, (slug, json.dumps(data)))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"pg_save_brand error: {e}")
    finally:
        _put_pg(conn)


def pg_delete_brand(slug):
    """Delete a brand from Postgres."""
    conn = _get_pg()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM brands WHERE slug = %s", (slug,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"pg_delete_brand error: {e}")
    finally:
        _put_pg(conn)


def pg_save_report_meta(brand_slug, report_type, fmt, blob_url, filename):
    """Save report metadata to Postgres."""
    conn = _get_pg()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO reports_meta (brand_slug, report_type, format, blob_url, filename)
            VALUES (%s, %s, %s, %s, %s)
        """, (brand_slug, report_type, fmt, blob_url, filename))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"pg_save_report_meta error: {e}")
    finally:
        _put_pg(conn)


def pg_list_reports(brand_slug=None, limit=50):
    """List recent reports from Postgres."""
    conn = _get_pg()
    try:
        cur = conn.cursor()
        if brand_slug:
            cur.execute(
                "SELECT id, brand_slug, report_type, format, blob_url, filename, created_at FROM reports_meta WHERE brand_slug = %s ORDER BY created_at DESC LIMIT %s",
                (brand_slug, limit)
            )
        else:
            cur.execute(
                "SELECT id, brand_slug, report_type, format, blob_url, filename, created_at FROM reports_meta ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )
        rows = cur.fetchall()
        return [{
            "id": r[0], "brand_slug": r[1], "report_type": r[2],
            "format": r[3], "blob_url": r[4], "filename": r[5],
            "created_at": r[6].isoformat() if r[6] else ""
        } for r in rows]
    except Exception as e:
        logger.error(f"pg_list_reports error: {e}")
        return []
    finally:
        _put_pg(conn)


# ══════════════════════════════════════════════════════════════════════
# REDIS — Auth Sessions
# ══════════════════════════════════════════════════════════════════════

_redis_client = None

def _get_redis():
    """Get Upstash Redis client (lazy init)."""
    global _redis_client
    if _redis_client is None:
        from upstash_redis import Redis
        _redis_client = Redis(url=_REDIS_URL, token=_REDIS_TOKEN)
    return _redis_client


def redis_set_session(token, session_data, ttl=86400):
    """Store auth session in Redis with TTL (default 24h)."""
    try:
        r = _get_redis()
        r.set(f"session:{token}", json.dumps(session_data), ex=ttl)
    except Exception as e:
        logger.error(f"redis_set_session error: {e}")


def redis_get_session(token):
    """Get auth session from Redis."""
    try:
        r = _get_redis()
        data = r.get(f"session:{token}")
        if data:
            return json.loads(data) if isinstance(data, str) else data
        return None
    except Exception as e:
        logger.error(f"redis_get_session error: {e}")
        return None


def redis_delete_session(token):
    """Delete auth session from Redis."""
    try:
        r = _get_redis()
        r.delete(f"session:{token}")
    except Exception as e:
        logger.error(f"redis_delete_session error: {e}")


# ══════════════════════════════════════════════════════════════════════
# BLOB — Report Files
# ══════════════════════════════════════════════════════════════════════

def blob_upload(filename, file_bytes, content_type="application/octet-stream"):
    """Upload a file to Vercel Blob. Returns the blob URL."""
    try:
        import vercel_blob
        resp = vercel_blob.put(
            f"reports/{filename}",
            file_bytes,
            options={"allowOverwrite": "true"},
            timeout=30
        )
        url = resp.get("url", "") if isinstance(resp, dict) else str(resp)
        logger.info(f"Blob uploaded: {filename} → {url}")
        return url
    except Exception as e:
        logger.error(f"blob_upload error: {e}")
        return None


def blob_download(blob_url):
    """Download a file from Vercel Blob. Returns bytes."""
    try:
        import requests
        resp = requests.get(blob_url)
        if resp.status_code == 200:
            return resp.content
        logger.error(f"blob_download failed: {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"blob_download error: {e}")
        return None


def blob_list(prefix="reports/"):
    """List files in Vercel Blob."""
    try:
        import vercel_blob
        resp = vercel_blob.list(options={"prefix": prefix})
        return resp.get("blobs", []) if isinstance(resp, dict) else []
    except Exception as e:
        logger.error(f"blob_list error: {e}")
        return []


def blob_delete(blob_url):
    """Delete a file from Vercel Blob."""
    try:
        import vercel_blob
        vercel_blob.delete(blob_url)
    except Exception as e:
        logger.error(f"blob_delete error: {e}")


# ══════════════════════════════════════════════════════════════════════
# UNIFIED INTERFACE — Auto-selects backend
# ══════════════════════════════════════════════════════════════════════

class UserStore:
    """Unified user storage — Postgres if available, else /tmp/users.json."""

    @staticmethod
    def load_all():
        if USE_POSTGRES:
            return pg_load_users()
        return _file_load_users()

    @staticmethod
    def save(user_id, user):
        if USE_POSTGRES:
            pg_save_user(user_id, user)
        else:
            users = _file_load_users()
            users[user_id] = user
            _file_save_users(users)

    @staticmethod
    def get_by_email(email):
        if USE_POSTGRES:
            return pg_get_user_by_email(email)
        users = _file_load_users()
        for uid, u in users.items():
            if u.get("email") == email:
                return u
        return None

    @staticmethod
    def get_by_id(user_id):
        if USE_POSTGRES:
            return pg_get_user_by_id(user_id)
        users = _file_load_users()
        return users.get(user_id)


class SessionStore:
    """Unified session storage — Redis if available, else in-memory dict."""

    _memory = {}

    @staticmethod
    def set(token, session_data, ttl=86400):
        if USE_REDIS:
            redis_set_session(token, session_data, ttl)
        else:
            SessionStore._memory[token] = session_data

    @staticmethod
    def get(token):
        if USE_REDIS:
            return redis_get_session(token)
        return SessionStore._memory.get(token)

    @staticmethod
    def delete(token):
        if USE_REDIS:
            redis_delete_session(token)
        else:
            SessionStore._memory.pop(token, None)


class BrandStore:
    """Unified brand storage — Postgres if available, else /tmp/brands.json."""

    @staticmethod
    def load_all():
        if USE_POSTGRES:
            return pg_load_brands()
        return _file_load_brands()

    @staticmethod
    def save(slug, data):
        if USE_POSTGRES:
            pg_save_brand(slug, data)
        else:
            all_data = _file_load_brands()
            all_data["brands"][slug] = data
            _file_save_brands(all_data)

    @staticmethod
    def delete(slug):
        if USE_POSTGRES:
            pg_delete_brand(slug)
        else:
            all_data = _file_load_brands()
            all_data["brands"].pop(slug, None)
            _file_save_brands(all_data)


class ReportStore:
    """Unified report file storage — Blob if available, else /tmp/reports/."""

    @staticmethod
    def upload(filename, file_path_or_bytes, content_type="application/octet-stream"):
        """Upload a report file. Returns URL (blob) or file path (local)."""
        if isinstance(file_path_or_bytes, str):
            # It's a file path
            with open(file_path_or_bytes, "rb") as f:
                file_bytes = f.read()
        else:
            file_bytes = file_path_or_bytes

        if USE_BLOB:
            url = blob_upload(filename, file_bytes, content_type)
            if url and USE_POSTGRES:
                # Parse brand_slug and report_type from filename
                parts = filename.replace(".", "_").split("_")
                pg_save_report_meta(
                    brand_slug=parts[0] if parts else "unknown",
                    report_type="report",
                    fmt=filename.rsplit(".", 1)[-1] if "." in filename else "unknown",
                    blob_url=url,
                    filename=filename
                )
            return url
        else:
            # Save locally
            local_path = os.path.join("/tmp/reports", filename)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(file_bytes)
            return local_path

    @staticmethod
    def download(url_or_path):
        """Download a report file. Returns bytes."""
        if url_or_path and url_or_path.startswith("http"):
            return blob_download(url_or_path)
        elif url_or_path and os.path.exists(url_or_path):
            with open(url_or_path, "rb") as f:
                return f.read()
        return None

    @staticmethod
    def list_recent(brand_slug=None, limit=50):
        """List recent reports."""
        if USE_POSTGRES:
            return pg_list_reports(brand_slug, limit)
        # Fallback: list /tmp/reports directory
        reports = []
        reports_dir = "/tmp/reports"
        if os.path.exists(reports_dir):
            for fname in sorted(os.listdir(reports_dir), reverse=True)[:limit]:
                fpath = os.path.join(reports_dir, fname)
                reports.append({
                    "filename": fname,
                    "format": fname.rsplit(".", 1)[-1] if "." in fname else "",
                    "created_at": datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat(),
                    "blob_url": None
                })
        return reports


# ── File-based fallbacks (original /tmp storage) ──────────────────────

USERS_FILE = "/tmp/users.json"
BRANDS_FILE = "/tmp/brands.json"

def _file_load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _file_save_users(users):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving users file: {e}")

def _file_load_brands():
    if os.path.exists(BRANDS_FILE):
        try:
            with open(BRANDS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Copy bundled brands.json on first load
    bundled = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brands.json")
    if os.path.exists(bundled):
        import shutil
        os.makedirs(os.path.dirname(BRANDS_FILE), exist_ok=True)
        shutil.copy2(bundled, BRANDS_FILE)
        with open(BRANDS_FILE, "r") as f:
            return json.load(f)
    return {"brands": {}}

def _file_save_brands(data):
    try:
        with open(BRANDS_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving brands file: {e}")


# ── Storage Status (for System Health panel) ──────────────────────────

def get_storage_status():
    """Return dict describing which storage backends are active."""
    status = {
        "postgres": {"configured": USE_POSTGRES, "status": "unknown"},
        "redis": {"configured": USE_REDIS, "status": "unknown"},
        "blob": {"configured": USE_BLOB, "status": "unknown"},
    }

    if USE_POSTGRES:
        try:
            conn = _get_pg()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            _put_pg(conn)
            status["postgres"]["status"] = "connected"
        except Exception as e:
            status["postgres"]["status"] = f"error: {str(e)[:80]}"

    if USE_REDIS:
        try:
            r = _get_redis()
            r.ping()
            status["redis"]["status"] = "connected"
        except Exception as e:
            status["redis"]["status"] = f"error: {str(e)[:80]}"

    if USE_BLOB:
        try:
            blobs = blob_list()
            status["blob"]["status"] = f"connected ({len(blobs)} files)"
        except Exception as e:
            status["blob"]["status"] = f"error: {str(e)[:80]}"

    return status
