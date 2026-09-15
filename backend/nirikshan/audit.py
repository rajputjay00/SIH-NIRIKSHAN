import os
import json
import sqlite3
import hashlib
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple

_LOCK = threading.Lock()
GENESIS_PREV_HASH = "0" * 64
IST_TZ = timezone(timedelta(hours=5, minutes=30))


def get_db_path() -> str:
    """Returns DB path from environment variable NIRIKSHAN_AUDIT_DB or default path."""
    db_env = os.getenv("NIRIKSHAN_AUDIT_DB")
    if db_env and db_env.strip():
        return db_env.strip()
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(backend_dir, "data", "audit.db")


def get_connection() -> sqlite3.Connection:
    """Creates a connection to SQLite database, creating parent directories if needed."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes audit_ledger table if it does not exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                payload TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL
            )
            """
        )
        conn.commit()


def canonical_json_str(payload: Dict[str, Any]) -> str:
    """Serializes dictionary payload to canonical JSON string."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Computes SHA256 hex digest of canonical JSON payload."""
    canonical = canonical_json_str(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_entry_hash(ts: str, actor: str, action: str, payload_hash: str, prev_hash: str) -> str:
    """Computes SHA256 hex digest for an audit entry."""
    data_str = f"{ts}|{actor}|{action}|{payload_hash}|{prev_hash}"
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def append(actor: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Appends a new audit record to the hash-chained ledger. Thread-safe."""
    with _LOCK:
        init_db()
        ts = datetime.now(IST_TZ).isoformat()
        payload_hash_val = compute_payload_hash(payload)
        payload_str = canonical_json_str(payload)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT hash FROM audit_ledger ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row and row["hash"]:
                prev_hash_val = row["hash"]
            else:
                prev_hash_val = GENESIS_PREV_HASH

            entry_hash_val = compute_entry_hash(ts, actor, action, payload_hash_val, prev_hash_val)

            cursor.execute(
                """
                INSERT INTO audit_ledger (ts, actor, action, payload, payload_hash, prev_hash, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, actor, action, payload_str, payload_hash_val, prev_hash_val, entry_hash_val),
            )
            entry_id = cursor.lastrowid
            conn.commit()

        return {
            "id": entry_id,
            "ts": ts,
            "actor": actor,
            "action": action,
            "payload": payload,
            "payload_hash": payload_hash_val,
            "prev_hash": prev_hash_val,
            "hash": entry_hash_val,
        }


def get_by_image_hash(image_sha256: str) -> Optional[Dict[str, Any]]:
    """Finds the latest audit entry matching image_sha256."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, ts, actor, action, payload, payload_hash, prev_hash, hash
            FROM audit_ledger
            ORDER BY id DESC
            """
        )
        rows = cursor.fetchall()
        for row in rows:
            try:
                p_dict = json.loads(row["payload"])
                if isinstance(p_dict, dict) and p_dict.get("image_sha256") == image_sha256:
                    return {
                        "id": row["id"],
                        "ts": row["ts"],
                        "actor": row["actor"],
                        "action": row["action"],
                        "payload": p_dict,
                        "payload_hash": row["payload_hash"],
                        "prev_hash": row["prev_hash"],
                        "hash": row["hash"],
                    }
            except Exception:
                continue
    return None


def verify_chain() -> Tuple[bool, Optional[int]]:
    """Verifies integrity of the entire audit chain. Returns (ok, first_broken_id)."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, ts, actor, action, payload, payload_hash, prev_hash, hash
            FROM audit_ledger
            ORDER BY id ASC
            """
        )
        rows = cursor.fetchall()
        if not rows:
            return True, None

        expected_prev_hash = GENESIS_PREV_HASH

        for row in rows:
            row_id = row["id"]
            ts = row["ts"]
            actor = row["actor"]
            action = row["action"]
            payload_str = row["payload"]
            payload_hash_val = row["payload_hash"]
            prev_hash_val = row["prev_hash"]
            row_hash_val = row["hash"]

            # 1. Check prev_hash links properly
            if prev_hash_val != expected_prev_hash:
                return False, row_id

            # 2. Check payload_hash validity
            try:
                p_dict = json.loads(payload_str)
                recomputed_payload_hash = compute_payload_hash(p_dict)
                if recomputed_payload_hash != payload_hash_val:
                    return False, row_id
            except Exception:
                return False, row_id

            # 3. Check entry hash calculation
            recomputed_hash = compute_entry_hash(ts, actor, action, payload_hash_val, prev_hash_val)
            if recomputed_hash != row_hash_val:
                return False, row_id

            expected_prev_hash = row_hash_val

    return True, None


def get_entry_count() -> int:
    """Returns the total number of entries in the audit ledger."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM audit_ledger")
        row = cursor.fetchone()
        return row[0] if row else 0
