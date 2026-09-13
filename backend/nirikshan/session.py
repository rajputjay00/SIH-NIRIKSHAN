import random
import time
import base64
import io
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import OrderedDict
from PIL import Image

CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
SESSION_TTL_SECONDS = 7200 # 2 hours
MAX_SCANS_PER_SESSION = 50
MAX_SESSIONS = 1000


class SessionStore:
    def __init__(self):
        # code -> { created_at: float, scans: List[Dict], subscribers: List[asyncio.Queue] }
        self._sessions: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def generate_code(self) -> str:
        for _ in range(100):
            code = "".join(random.choices(CODE_CHARS, k=6))
            if code not in self._sessions:
                return code
        raise RuntimeError("Failed to generate unique session code")

    def create_session(self) -> Dict[str, Any]:
        self.cleanup_expired()
        if len(self._sessions) >= MAX_SESSIONS:
            self._sessions.popitem(last=False) # Evict oldest

        code = self.generate_code()
        now = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()

        session_data = {
            "code": code,
            "created_at_ts": now,
            "created_at": now_iso,
            "scans": [],
            "subscribers": [],
        }
        self._sessions[code] = session_data
        return {"code": code, "created_at": now_iso}

    def get_session(self, code: str) -> Optional[Dict[str, Any]]:
        self.cleanup_expired()
        code_upper = code.upper()
        if code_upper in self._sessions:
            self._sessions.move_to_end(code_upper)
            return self._sessions[code_upper]
        return None

    def add_scan_result(self, code: str, result_data: Dict[str, Any], image_bytes: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
        sess = self.get_session(code)
        if not sess:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        scan_id = f"scan_{int(time.time()*1000)}"

        thumb_b64 = None
        if image_bytes:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                img.thumbnail((320, 320))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=80)
                thumb_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            except Exception:
                thumb_b64 = None

        record = {
            "id": scan_id,
            "result": result_data,
            "thumbnail_jpeg_b64": thumb_b64,
            "created_at": now_iso,
        }

        # Keep max 50 per session
        sess["scans"].insert(0, record)
        if len(sess["scans"]) > MAX_SCANS_PER_SESSION:
            sess["scans"] = sess["scans"][:MAX_SCANS_PER_SESSION]

        # Notify SSE subscribers asynchronously
        for queue in list(sess["subscribers"]):
            try:
                queue.put_nowait(record)
            except Exception:
                pass

        return record

    def get_results(self, code: str) -> Optional[List[Dict[str, Any]]]:
        sess = self.get_session(code)
        if not sess:
            return None
        return sess["scans"]

    def subscribe(self, code: str) -> Optional[asyncio.Queue]:
        sess = self.get_session(code)
        if not sess:
            return None
        queue = asyncio.Queue()
        sess["subscribers"].append(queue)
        return queue

    def unsubscribe(self, code: str, queue: asyncio.Queue):
        sess = self.get_session(code)
        if sess and queue in sess["subscribers"]:
            sess["subscribers"].remove(queue)

    def cleanup_expired(self):
        now = time.time()
        expired = [code for code, data in self._sessions.items() if (now - data["created_at_ts"]) > SESSION_TTL_SECONDS]
        for code in expired:
            del self._sessions[code]


session_store = SessionStore()
