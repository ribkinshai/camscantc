"""
מודול מסד נתונים - SQLite
Database module for camera scan tracking
"""
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from zoneinfo import ZoneInfo


def _now_il():
    """שעה נוכחית לפי שעון ישראל (Asia/Jerusalem)"""
    return datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None)

DB_PATH = Path("data/cameras.db")


def init_db():
    """אתחול מסד הנתונים - יצירת טבלאות והגדרות ברירת מחדל"""
    DB_PATH.parent.mkdir(exist_ok=True, parents=True)
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                is_central INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                area TEXT DEFAULT '',
                scan_policy TEXT DEFAULT '',
                latitude REAL,
                longitude REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS faults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER NOT NULL,
                fault_datetime TEXT NOT NULL,
                description TEXT NOT NULL,
                resolved INTEGER DEFAULT 0,
                resolved_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (camera_id) REFERENCES cameras(id)
            );

            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER NOT NULL,
                scheduled_hour TEXT NOT NULL,
                scanned_at TEXT,
                scanned_by TEXT,
                status TEXT DEFAULT 'ok',
                event_details TEXT,
                FOREIGN KEY (camera_id) REFERENCES cameras(id),
                UNIQUE(camera_id, scheduled_hour)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_scans_hour ON scans(scheduled_hour);
            CREATE INDEX IF NOT EXISTS idx_faults_camera ON faults(camera_id, resolved);
        """)

        # Migration - add columns to existing DBs if missing (must run before status index)
        cursor.execute("PRAGMA table_info(scans)")
        existing_cols = {row['name'] for row in cursor.fetchall()}
        if 'status' not in existing_cols:
            cursor.execute("ALTER TABLE scans ADD COLUMN status TEXT DEFAULT 'ok'")
        if 'event_details' not in existing_cols:
            cursor.execute("ALTER TABLE scans ADD COLUMN event_details TEXT")
# Migration for faults - add reporter/resolver name columns
        cursor.execute("PRAGMA table_info(faults)")
        existing_fault_cols = {row['name'] for row in cursor.fetchall()}
        if 'reported_by' not in existing_fault_cols:
            cursor.execute("ALTER TABLE faults ADD COLUMN reported_by TEXT")
        if 'resolved_by' not in existing_fault_cols:
            cursor.execute("ALTER TABLE faults ADD COLUMN resolved_by TEXT")
        # Now safe to create status index
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status)")
# Migration for cameras - add area column
        cursor.execute("PRAGMA table_info(cameras)")
        existing_cam_cols = {row['name'] for row in cursor.fetchall()}
        if 'area' not in existing_cam_cols:
            cursor.execute("ALTER TABLE cameras ADD COLUMN area TEXT DEFAULT ''")
        if 'scan_policy' not in existing_cam_cols:
            cursor.execute("ALTER TABLE cameras ADD COLUMN scan_policy TEXT DEFAULT ''")
        if 'latitude' not in existing_cam_cols:
            cursor.execute("ALTER TABLE cameras ADD COLUMN latitude REAL")
        if 'longitude' not in existing_cam_cols:
            cursor.execute("ALTER TABLE cameras ADD COLUMN longitude REAL")
        defaults = {
            'central_count': '10',
            'rotating_count': '30',
            'shift_morning_start': '07',
            'shift_evening_start': '15',
            'shift_night_start': '23',
            'alert_grace_minutes': '15',
        }
        for k, v in defaults.items():
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (k, v),
            )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ========= ניהול מצלמות =========
def add_camera(name: str, is_central: bool = False, area: str = '') -> bool:
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO cameras (name, is_central, area) VALUES (?, ?, ?)",
                (name, 1 if is_central else 0, area),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def bulk_add_cameras_structured(camera_data, is_central: bool = False) -> int:
    """camera_data: list of (name, area) or (name, area, scan_policy) tuples"""
    added = 0
    with get_conn() as conn:
        for item in camera_data:
            if len(item) == 3:
                name, area, scan_policy = item
            else:
                name, area = item
                scan_policy = ''
            name = name.strip() if name else ''
            if not name:
                continue
            try:
                conn.execute(
                    "INSERT INTO cameras (name, is_central, area, scan_policy) VALUES (?, ?, ?, ?)",
                    (name, 1 if is_central else 0, area or '', scan_policy or ''),
                )
                added += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
    return added


def get_all_areas():
    """Return sorted list of unique non-empty areas"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT area FROM cameras WHERE is_active = 1 "
            "AND area IS NOT NULL AND area != '' ORDER BY area"
        ).fetchall()
        return [r['area'] for r in rows]


def bulk_add_cameras(names, is_central: bool = False) -> int:
    added = 0
    with get_conn() as conn:
        for name in names:
            name = name.strip()
            if not name:
                continue
            try:
                conn.execute(
                    "INSERT INTO cameras (name, is_central) VALUES (?, ?)",
                    (name, 1 if is_central else 0),
                )
                added += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
    return added


def get_all_cameras():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cameras WHERE is_active = 1 ORDER BY is_central DESC, id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_central_cameras():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cameras WHERE is_central = 1 AND is_active = 1 ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_rotating_cameras():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cameras WHERE is_central = 0 AND is_active = 1 ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_camera(camera_id: int, name=None, is_central=None, area=None, scan_policy=None):
    with get_conn() as conn:
        if name is not None:
            conn.execute("UPDATE cameras SET name = ? WHERE id = ?", (name, camera_id))
        if is_central is not None:
            conn.execute(
                "UPDATE cameras SET is_central = ? WHERE id = ?",
                (1 if is_central else 0, camera_id),
            )
        if area is not None:
            conn.execute("UPDATE cameras SET area = ? WHERE id = ?", (area, camera_id))
        if scan_policy is not None:
            conn.execute("UPDATE cameras SET scan_policy = ? WHERE id = ?", (scan_policy, camera_id))
        conn.commit()


def delete_camera(camera_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE cameras SET is_active = 0 WHERE id = ?", (camera_id,))
        conn.commit()


# ========= תקלות =========
def add_fault(camera_id: int, fault_datetime: str, description: str, reported_by: str = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO faults (camera_id, fault_datetime, description, reported_by) VALUES (?, ?, ?, ?)",
            (camera_id, fault_datetime, description, reported_by),
        )
        conn.commit()


def get_active_faults():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT f.*, c.name as camera_name
            FROM faults f
            JOIN cameras c ON f.camera_id = c.id
            WHERE f.resolved = 0
            ORDER BY f.fault_datetime DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_all_faults():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT f.*, c.name as camera_name
            FROM faults f
            JOIN cameras c ON f.camera_id = c.id
            ORDER BY f.fault_datetime DESC
        """).fetchall()
        return [dict(r) for r in rows]


def resolve_fault(fault_id: int, resolved_by: str = None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE faults SET resolved = 1, resolved_at = ?, resolved_by = ? WHERE id = ?",
            (_now_il().isoformat(sep=' ', timespec='seconds'), resolved_by, fault_id),
        )
        conn.commit()


def delete_fault(fault_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM faults WHERE id = ?", (fault_id,))
        conn.commit()


def is_camera_faulty(camera_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM faults WHERE camera_id = ? AND resolved = 0",
            (camera_id,),
        ).fetchone()
        return row['c'] > 0


def get_faulty_camera_ids():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT camera_id FROM faults WHERE resolved = 0"
        ).fetchall()
        return {r['camera_id'] for r in rows}


# ========= סריקות =========
def mark_scan(
    camera_id: int,
    scheduled_hour: str,
    scanned_by: str = "",
    status: str = "ok",
    event_details: str = None,
):
    """
    סימון סריקה כבוצעה.
    status: 'ok' = תקין, 'issue' = תקלה בסריקה
    event_details: פירוט האירוע (רק כשstatus='issue')
    """
    with get_conn() as conn:
        now = _now_il().isoformat(sep=' ', timespec='seconds')
        conn.execute("""
            INSERT INTO scans (camera_id, scheduled_hour, scanned_at, scanned_by, status, event_details)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(camera_id, scheduled_hour) DO UPDATE
                SET scanned_at = excluded.scanned_at,
                    scanned_by = excluded.scanned_by,
                    status = excluded.status,
                    event_details = excluded.event_details
        """, (camera_id, scheduled_hour, now, scanned_by, status, event_details))
        conn.commit()


def unmark_scan(camera_id: int, scheduled_hour: str):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM scans WHERE camera_id = ? AND scheduled_hour = ?",
            (camera_id, scheduled_hour),
        )
        conn.commit()


def get_scans_for_hour(scheduled_hour: str) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT camera_id, scanned_at, scanned_by, status, event_details "
            "FROM scans WHERE scheduled_hour = ?",
            (scheduled_hour,),
        ).fetchall()
        return {r['camera_id']: dict(r) for r in rows}


def get_issue_scans_in_range(start_hour: str, end_hour: str):
    """סריקות שסומנו כתקלה בטווח זמן"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.*, c.name as camera_name
            FROM scans s
            JOIN cameras c ON s.camera_id = c.id
            WHERE s.scheduled_hour BETWEEN ? AND ?
              AND s.status = 'issue'
            ORDER BY s.scheduled_hour DESC, c.name ASC
        """, (start_hour, end_hour)).fetchall()
        return [dict(r) for r in rows]


def get_scans_in_range(start_hour: str, end_hour: str):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.*, c.name as camera_name
            FROM scans s
            JOIN cameras c ON s.camera_id = c.id
            WHERE s.scheduled_hour BETWEEN ? AND ?
            ORDER BY s.scheduled_hour DESC, c.name ASC
        """, (start_hour, end_hour)).fetchall()
        return [dict(r) for r in rows]


# ========= הגדרות =========
def get_setting(key: str, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row['value'] if row else default


def set_setting(key: str, value):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, str(value)))
        conn.commit()
def reset_scans_and_faults():
    """מוחק את כל הסריקות והתקלות. המצלמות וההגדרות נשמרות."""
    with get_conn() as conn:
        conn.execute("DELETE FROM scans")
        conn.execute("DELETE FROM faults")
        conn.commit()


def reset_all_data():
    """מוחק הכל - סריקות, תקלות ומצלמות. ההגדרות נשמרות."""
    with get_conn() as conn:
        conn.execute("DELETE FROM scans")
        conn.execute("DELETE FROM faults")
        conn.execute("DELETE FROM cameras")
        conn.commit()
# ========= מיקומים =========
def update_camera_location(camera_id: int, latitude, longitude):
    """עדכון מיקום גיאוגרפי של מצלמה. שולח None כדי למחוק."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE cameras SET latitude = ?, longitude = ? WHERE id = ?",
            (latitude, longitude, camera_id),
        )
        conn.commit()


def get_mapped_cameras():
    """מצלמות עם קואורדינטות בלבד"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cameras WHERE is_active = 1 "
            "AND latitude IS NOT NULL AND longitude IS NOT NULL "
            "ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_unmapped_cameras():
    """מצלמות בלי קואורדינטות"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cameras WHERE is_active = 1 "
            "AND (latitude IS NULL OR longitude IS NULL) "
            "ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]
