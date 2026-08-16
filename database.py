"""
מסד נתונים - מוקד 106 טירת כרמל
מאחד את כל הטבלאות של v1 (מצלמות, סריקות ישנות, תקלות) עם המבנה המורחב של v2
(משתמשים, משמרות, סריקות מבוססות תוכנית, אירועים, בקרות קשר, נקודות חמות ועוד).
"""
import sqlite3
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path
from zoneinfo import ZoneInfo

DB_PATH = Path("data/cameras.db")


def _now_il():
    return datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None)


def _now_iso():
    return _now_il().isoformat(sep=' ', timespec='seconds')


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """אתחול/יצירת מסד. בטוח להרצה חוזרת."""
    DB_PATH.parent.mkdir(exist_ok=True, parents=True)
    with get_conn() as conn:
        cursor = conn.cursor()

        # ============ טבלאות מ-v1 (מצלמות, תקלות, סריקות ישנות, הגדרות) ============
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
                camera_number INTEGER,
                address TEXT,
                street TEXT,
                neighborhood TEXT,
                matrix TEXT,
                camera_type TEXT,
                direction TEXT,
                camera_status TEXT DEFAULT 'ok',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS faults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER NOT NULL,
                fault_datetime TEXT NOT NULL,
                description TEXT NOT NULL,
                resolved INTEGER DEFAULT 0,
                resolved_at TEXT,
                reported_by TEXT,
                resolved_by TEXT,
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
                event_category TEXT,
                FOREIGN KEY (camera_id) REFERENCES cameras(id),
                UNIQUE(camera_id, scheduled_hour)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

        # ============ טבלאות חדשות v2 ============
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                shift_type TEXT NOT NULL,
                is_roeh INTEGER DEFAULT 1,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT DEFAULT 'open',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS scan_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id INTEGER NOT NULL,
                slot_time TEXT NOT NULL,
                plan_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                not_done_reason TEXT,
                not_done_details TEXT,
                locations_checked TEXT,
                event_count INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shift_id) REFERENCES shifts(id),
                UNIQUE(shift_id, slot_time)
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_task_id INTEGER,
                shift_id INTEGER,
                reporter_user_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                location_area TEXT,
                location_camera_id INTEGER,
                description TEXT,
                moked_106_call_id TEXT,
                handling_body TEXT,
                status TEXT DEFAULT 'new',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                closed_at TEXT,
                closure_notes TEXT,
                FOREIGN KEY (scan_task_id) REFERENCES scan_tasks(id),
                FOREIGN KEY (shift_id) REFERENCES shifts(id),
                FOREIGN KEY (reporter_user_id) REFERENCES users(id),
                FOREIGN KEY (location_camera_id) REFERENCES cameras(id)
            );

            CREATE TABLE IF NOT EXISTS event_dumping_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER UNIQUE NOT NULL,
                dumper_identified INTEGER DEFAULT 0,
                vehicle_identified INTEGER DEFAULT 0,
                license_plate TEXT,
                forwarded_to_enforcement INTEGER DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (event_id) REFERENCES events(id)
            );

            CREATE TABLE IF NOT EXISTS comm_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id INTEGER NOT NULL,
                scheduled_time TEXT NOT NULL,
                actual_time TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shift_id) REFERENCES shifts(id),
                UNIQUE(shift_id, scheduled_time)
            );

            CREATE TABLE IF NOT EXISTS hotspots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                area TEXT,
                camera_ids_json TEXT,
                priority TEXT DEFAULT 'medium',
                active_hours_json TEXT,
                watching_for TEXT,
                notes TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS construction_sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                address TEXT,
                camera_ids_json TEXT,
                active INTEGER DEFAULT 1,
                start_date TEXT,
                end_date TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                phenomenon TEXT,
                area TEXT,
                start_date TEXT,
                end_date TEXT,
                active_hours_json TEXT,
                camera_ids_json TEXT,
                goal TEXT,
                notes TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS campaign_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
                FOREIGN KEY (event_id) REFERENCES events(id),
                UNIQUE(campaign_id, event_id)
            );

            CREATE TABLE IF NOT EXISTS drills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drill_date TEXT NOT NULL,
                drill_type TEXT NOT NULL,
                scenario TEXT,
                moked_user_id INTEGER,
                participants_json TEXT,
                start_time TEXT,
                detection_time TEXT,
                force_activation_time TEXT,
                event_opened_correctly INTEGER,
                guidance_done INTEGER,
                closure_done INTEGER,
                findings TEXT,
                lessons TEXT,
                improvements TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (moked_user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS scheduled_scan_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                days_of_week TEXT DEFAULT 'all',
                camera_ids_json TEXT DEFAULT '[]',
                priority TEXT DEFAULT 'medium',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                details_json TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        # ============ Indexes ============
        cursor.executescript("""
            CREATE INDEX IF NOT EXISTS idx_scans_hour ON scans(scheduled_hour);
            CREATE INDEX IF NOT EXISTS idx_faults_camera ON faults(camera_id, resolved);
            CREATE INDEX IF NOT EXISTS idx_shifts_user ON shifts(user_id, status);
            CREATE INDEX IF NOT EXISTS idx_shifts_start ON shifts(start_time);
            CREATE INDEX IF NOT EXISTS idx_scan_tasks_shift ON scan_tasks(shift_id, slot_time);
            CREATE INDEX IF NOT EXISTS idx_scan_tasks_status ON scan_tasks(status);
            CREATE INDEX IF NOT EXISTS idx_events_shift ON events(shift_id);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
            CREATE INDEX IF NOT EXISTS idx_comm_checks_shift ON comm_checks(shift_id);
        """)

        # ============ Migrations לטבלאות v1 קיימות ============
        cursor.execute("PRAGMA table_info(scans)")
        existing_cols = {row['name'] for row in cursor.fetchall()}
        if 'status' not in existing_cols:
            cursor.execute("ALTER TABLE scans ADD COLUMN status TEXT DEFAULT 'ok'")
        if 'event_details' not in existing_cols:
            cursor.execute("ALTER TABLE scans ADD COLUMN event_details TEXT")
        if 'event_category' not in existing_cols:
            cursor.execute("ALTER TABLE scans ADD COLUMN event_category TEXT")
        cursor.execute("PRAGMA table_info(faults)")
        existing_fault_cols = {row['name'] for row in cursor.fetchall()}
        if 'reported_by' not in existing_fault_cols:
            cursor.execute("ALTER TABLE faults ADD COLUMN reported_by TEXT")
        if 'resolved_by' not in existing_fault_cols:
            cursor.execute("ALTER TABLE faults ADD COLUMN resolved_by TEXT")

        cursor.execute("PRAGMA table_info(cameras)")
        existing_cam_cols = {row['name'] for row in cursor.fetchall()}
        for col_name, col_def in [
            ('area', "TEXT DEFAULT ''"),
            ('scan_policy', "TEXT DEFAULT ''"),
            ('latitude', 'REAL'),
            ('longitude', 'REAL'),
            ('camera_number', 'INTEGER'),
            ('address', 'TEXT'),
            ('street', 'TEXT'),
            ('neighborhood', 'TEXT'),
            ('matrix', 'TEXT'),
            ('camera_type', 'TEXT'),
            ('direction', 'TEXT'),
            ('camera_status', "TEXT DEFAULT 'ok'"),
            ('notes', 'TEXT'),
        ]:
            if col_name not in existing_cam_cols:
                cursor.execute(f"ALTER TABLE cameras ADD COLUMN {col_name} {col_def}")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status)")

        # ============ הגדרות ברירת מחדל ============
        defaults = {
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

        # ============ Seed משתמשי ברירת מחדל + החלפה חד-פעמית ============
        # מחיקת מוקדנים זמניים אם קיימים
        cursor.execute("DELETE FROM users WHERE role = 'operator' AND username LIKE 'operator%'")

        # הוספת משתמשים אמיתיים - קפוץ על כפולים בשקט
        default_users = [
            ('admin', 'מנהלת המוקד', 'manager'),
            ('shai', 'שי כהן', 'manager'),
            ('riki', 'ריקי', 'operator'),
            ('sarit', 'שרית', 'operator'),
            ('itai', 'איתי', 'operator'),
            ('mai', 'מאי', 'operator'),
            ('elinor', 'אלינור', 'operator'),
            ('tali', 'טלי', 'operator'),
            ('sima', 'סימה', 'operator'),
            ('guy', 'גיא', 'operator'),
            ('lev', 'לב', 'operator'),
            ('shani', 'שני', 'operator'),
            ('liron', 'לירון', 'operator'),
            ('ronit', 'רונית', 'operator'),
        ]
        for username, name, role in default_users:
            try:
                cursor.execute(
                    "INSERT INTO users (username, name, role) VALUES (?, ?, ?)",
                    (username, name, role),
                )
            except sqlite3.IntegrityError:
                pass  # כבר קיים - דלג

        # ============ Seed מצלמות אמיתיות אוטומטית ============
        cursor.execute("SELECT COUNT(*) as c FROM cameras")
        if cursor.fetchone()['c'] == 0:
            try:
                import real_cameras
                camera_data = real_cameras.get_camera_data_for_import()
                for item in camera_data:
                    if len(item) == 3:
                        name, area, scan_policy = item
                    else:
                        name, area = item
                        scan_policy = ''
                    name = (name or '').strip()
                    if not name:
                        continue
                    try:
                        cursor.execute(
                            "INSERT INTO cameras (name, is_central, area, scan_policy) "
                            "VALUES (?, 0, ?, ?)",
                            (name, area or '', scan_policy or ''),
                        )
                    except sqlite3.IntegrityError:
                        pass
            except ImportError:
                pass  # real_cameras.py לא זמין - לא נטען

        conn.commit()
# ============ Seed נקודות חמות ברירת מחדל ============
        cursor.execute("SELECT COUNT(*) as c FROM hotspots")
        if cursor.fetchone()['c'] == 0:
            default_hotspots = [
                ('סקייטפארק', 'סקייטפארק', 'high',
                 '["09:00-11:00","20:00-23:00","23:00-05:00"]',
                 'ונדליזם, שוטטות, קטטות, רעש',
                 'נקודה חמה לכל שעות היום, במיוחד בערב ובלילה'),
                ('גן נחום', 'גן נחום', 'high',
                 '["09:00-11:00","16:00-20:00","23:00-05:00"]',
                 'ונדליזם, התקהלות, פעילות חריגה',
                 'גן פעיל - דגש על שעות עומס וערב'),
                ('גן יצחק שמיר', 'גן יצחק שמיר', 'high',
                 '["09:00-11:00","16:00-20:00"]',
                 'ונדליזם, פגיעה במתקנים, התנהגות מסכנת',
                 ''),
                ('כיכר החותרים', 'נוף ים', 'high',
                 '["09:00-11:00","20:00-23:00"]',
                 'התקהלות, שוטטות, אירועים כלליים',
                 ''),
                ('בניין העירייה', 'בניין העירייה', 'high',
                 '["09:00-11:00","13:00-16:00","23:00-05:00"]',
                 'פעילות חשודה, פריצות, ונדליזם',
                 'בדגש על שעות סגירה ולילה'),
            ]
            cursor.executemany(
                "INSERT INTO hotspots (name, area, priority, active_hours_json, watching_for, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                default_hotspots,
            )

        # ============ Seed אתרי בנייה ברירת מחדל ============
        cursor.execute("SELECT COUNT(*) as c FROM construction_sites")
        if cursor.fetchone()['c'] == 0:
            default_sites = [
                ('בית הספר החדש בנוף ים', 'שכונת נוף ים', 'active',
                 'בנייה של בית ספר חדש - יש לעקוב אחר פעילות אחרי שעות עבודה, פריצות, גניבת ציוד'),
            ]
            cursor.executemany(
                "INSERT INTO construction_sites (name, address, notes) VALUES (?, ?, ?)",
                [(name, addr, notes) for name, addr, _, notes in default_sites],
            )
        conn.commit()


# ==================== משתמשים ====================
def get_all_users(active_only=True):
    with get_conn() as conn:
        q = "SELECT * FROM users"
        if active_only:
            q += " WHERE active = 1"
        q += " ORDER BY role DESC, name ASC"
        return [dict(r) for r in conn.execute(q).fetchall()]


def get_user(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_username(username):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def add_user(username, name, role):
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (username, name, role) VALUES (?, ?, ?)",
                (username, name, role),
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def update_user(user_id, name=None, role=None, active=None):
    with get_conn() as conn:
        if name is not None:
            conn.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
        if role is not None:
            conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        if active is not None:
            conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))
        conn.commit()


# ==================== משמרות ====================
def open_shift(user_id, shift_type, is_roeh=True):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO shifts (user_id, shift_type, is_roeh, start_time, status) "
            "VALUES (?, ?, ?, ?, 'open')",
            (user_id, shift_type, 1 if is_roeh else 0, _now_iso()),
        )
        conn.commit()
        return cur.lastrowid


def close_shift(shift_id, notes=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE shifts SET status = 'closed', end_time = ?, notes = ? WHERE id = ?",
            (_now_iso(), notes, shift_id),
        )
        conn.commit()


def get_open_shift(user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND status = 'open' "
            "ORDER BY start_time DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def get_shift(shift_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        return dict(row) if row else None


def get_shifts_in_range(start_date, end_date, user_id=None):
    with get_conn() as conn:
        q = ("SELECT s.*, u.name as user_name, u.role as user_role "
             "FROM shifts s JOIN users u ON s.user_id = u.id "
             "WHERE date(s.start_time) BETWEEN ? AND ?")
        params = [start_date, end_date]
        if user_id:
            q += " AND s.user_id = ?"
            params.append(user_id)
        q += " ORDER BY s.start_time DESC"
        return [dict(r) for r in conn.execute(q, params).fetchall()]


# ==================== משימות סריקה ====================
def create_scan_task(shift_id, slot_time, plan_type):
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO scan_tasks (shift_id, slot_time, plan_type) VALUES (?, ?, ?)",
                (shift_id, slot_time, plan_type),
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def get_scan_task(task_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM scan_tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None


def get_shift_scan_tasks(shift_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM scan_tasks WHERE shift_id = ? ORDER BY slot_time ASC",
            (shift_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def start_scan_task(task_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE scan_tasks SET started_at = ? WHERE id = ? AND started_at IS NULL",
            (_now_iso(), task_id),
        )
        conn.commit()


def complete_scan_task(task_id, status, locations_checked=None, notes=None, event_count=0):
    """status: 'no_findings' | 'has_event' | 'not_done'"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE scan_tasks SET completed_at = ?, status = ?, "
            "locations_checked = ?, notes = ?, event_count = ? WHERE id = ?",
            (_now_iso(), status,
             json.dumps(locations_checked, ensure_ascii=False) if locations_checked else None,
             notes, event_count, task_id),
        )
        conn.commit()


def mark_scan_task_not_done(task_id, reason, details=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE scan_tasks SET status = 'not_done', completed_at = ?, "
            "not_done_reason = ?, not_done_details = ? WHERE id = ?",
            (_now_iso(), reason, details, task_id),
        )
        conn.commit()


# ==================== אירועים ====================
def create_event(reporter_user_id, event_type, source,
                 shift_id=None, scan_task_id=None,
                 location_area=None, location_camera_id=None,
                 description=None, moked_106_call_id=None, handling_body=None,
                 status='new'):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO events (reporter_user_id, event_type, source, shift_id, "
            "scan_task_id, location_area, location_camera_id, description, "
            "moked_106_call_id, handling_body, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (reporter_user_id, event_type, source, shift_id, scan_task_id,
             location_area, location_camera_id, description,
             moked_106_call_id, handling_body, status),
        )
        conn.commit()
        return cur.lastrowid


def add_dumping_details(event_id, dumper_identified=False, vehicle_identified=False,
                        license_plate=None, forwarded_to_enforcement=False, notes=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO event_dumping_details "
            "(event_id, dumper_identified, vehicle_identified, license_plate, "
            "forwarded_to_enforcement, notes) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(event_id) DO UPDATE SET "
            "dumper_identified=excluded.dumper_identified, "
            "vehicle_identified=excluded.vehicle_identified, "
            "license_plate=excluded.license_plate, "
            "forwarded_to_enforcement=excluded.forwarded_to_enforcement, "
            "notes=excluded.notes",
            (event_id, 1 if dumper_identified else 0, 1 if vehicle_identified else 0,
             license_plate, 1 if forwarded_to_enforcement else 0, notes),
        )
        conn.commit()


def update_event_status(event_id, status, closure_notes=None):
    with get_conn() as conn:
        now = _now_iso()
        if status == 'closed':
            conn.execute(
                "UPDATE events SET status = ?, closed_at = ?, closure_notes = ?, updated_at = ? WHERE id = ?",
                (status, now, closure_notes, now, event_id),
            )
        else:
            conn.execute(
                "UPDATE events SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, event_id),
            )
        conn.commit()


def get_event(event_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT e.*, u.name as reporter_name, c.name as camera_name "
            "FROM events e LEFT JOIN users u ON e.reporter_user_id = u.id "
            "LEFT JOIN cameras c ON e.location_camera_id = c.id "
            "WHERE e.id = ?", (event_id,),
        ).fetchone()
        return dict(row) if row else None


def get_events_in_range(start_date, end_date, shift_id=None, event_type=None, status=None):
    with get_conn() as conn:
        q = ("SELECT e.*, u.name as reporter_name, c.name as camera_name "
             "FROM events e LEFT JOIN users u ON e.reporter_user_id = u.id "
             "LEFT JOIN cameras c ON e.location_camera_id = c.id "
             "WHERE date(e.created_at) BETWEEN ? AND ?")
        params = [start_date, end_date]
        if shift_id:
            q += " AND e.shift_id = ?"
            params.append(shift_id)
        if event_type:
            q += " AND e.event_type = ?"
            params.append(event_type)
        if status:
            q += " AND e.status = ?"
            params.append(status)
        q += " ORDER BY e.created_at DESC"
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def get_shift_events(shift_id):
    with get_conn() as conn:
        q = ("SELECT e.*, u.name as reporter_name, c.name as camera_name "
             "FROM events e LEFT JOIN users u ON e.reporter_user_id = u.id "
             "LEFT JOIN cameras c ON e.location_camera_id = c.id "
             "WHERE e.shift_id = ? ORDER BY e.created_at DESC")
        return [dict(r) for r in conn.execute(q, (shift_id,)).fetchall()]


# ==================== בקרות קשר ====================
def create_comm_check_slot(shift_id, scheduled_time):
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO comm_checks (shift_id, scheduled_time) VALUES (?, ?)",
                (shift_id, scheduled_time),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass


def mark_comm_check(shift_id, scheduled_time, notes=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE comm_checks SET actual_time = ?, notes = ? "
            "WHERE shift_id = ? AND scheduled_time = ?",
            (_now_iso(), notes, shift_id, scheduled_time),
        )
        conn.commit()


def get_shift_comm_checks(shift_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM comm_checks WHERE shift_id = ? ORDER BY scheduled_time ASC",
            (shift_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ==================== נקודות חמות ====================
def add_hotspot(name, area=None, camera_ids=None, priority='medium',
                active_hours=None, watching_for=None, notes=None):
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO hotspots (name, area, camera_ids_json, priority, "
                "active_hours_json, watching_for, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, area,
                 json.dumps(camera_ids or []),
                 priority,
                 json.dumps(active_hours or []),
                 watching_for, notes),
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def get_all_hotspots(active_only=True):
    with get_conn() as conn:
        q = "SELECT * FROM hotspots"
        if active_only:
            q += " WHERE active = 1"
        q += " ORDER BY priority DESC, name ASC"
        rows = conn.execute(q).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['camera_ids'] = json.loads(d.get('camera_ids_json') or '[]')
            d['active_hours'] = json.loads(d.get('active_hours_json') or '[]')
            result.append(d)
        return result


def update_hotspot(hotspot_id, **kwargs):
    with get_conn() as conn:
        updates, params = [], []
        for k, v in kwargs.items():
            if k == 'camera_ids':
                updates.append("camera_ids_json = ?")
                params.append(json.dumps(v or []))
            elif k == 'active_hours':
                updates.append("active_hours_json = ?")
                params.append(json.dumps(v or []))
            elif k in ['name', 'area', 'priority', 'watching_for', 'notes']:
                updates.append(f"{k} = ?")
                params.append(v)
            elif k == 'active':
                updates.append("active = ?")
                params.append(1 if v else 0)
        if updates:
            params.append(hotspot_id)
            conn.execute(f"UPDATE hotspots SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()


def delete_hotspot(hotspot_id):
    with get_conn() as conn:
        conn.execute("UPDATE hotspots SET active = 0 WHERE id = ?", (hotspot_id,))
        conn.commit()


# ==================== אתרי בנייה ====================
def add_construction_site(name, address=None, camera_ids=None, notes=None):
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO construction_sites (name, address, camera_ids_json, notes) "
                "VALUES (?, ?, ?, ?)",
                (name, address, json.dumps(camera_ids or []), notes),
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def get_all_construction_sites(active_only=True):
    with get_conn() as conn:
        q = "SELECT * FROM construction_sites"
        if active_only:
            q += " WHERE active = 1"
        q += " ORDER BY name ASC"
        rows = conn.execute(q).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['camera_ids'] = json.loads(d.get('camera_ids_json') or '[]')
            result.append(d)
        return result


def update_construction_site(site_id, **kwargs):
    with get_conn() as conn:
        updates, params = [], []
        for k, v in kwargs.items():
            if k == 'camera_ids':
                updates.append("camera_ids_json = ?")
                params.append(json.dumps(v or []))
            elif k in ['name', 'address', 'notes', 'start_date', 'end_date']:
                updates.append(f"{k} = ?")
                params.append(v)
            elif k == 'active':
                updates.append("active = ?")
                params.append(1 if v else 0)
        if updates:
            params.append(site_id)
            conn.execute(
                f"UPDATE construction_sites SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()


def delete_construction_site(site_id):
    with get_conn() as conn:
        conn.execute("UPDATE construction_sites SET active = 0 WHERE id = ?", (site_id,))
        conn.commit()


# ==================== Audit Log ====================
def log_action(user_id, action, entity_type=None, entity_id=None, details=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (user_id, action, entity_type, entity_id, details_json, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, action, entity_type, entity_id,
             json.dumps(details, ensure_ascii=False) if details else None,
             _now_iso()),
        )
        conn.commit()


# ==================== מצלמות (v1) ====================
def add_camera(name, is_central=False, area='', scan_policy='', **extra):
    with get_conn() as conn:
        try:
            base_cols = ['name', 'is_central', 'area', 'scan_policy']
            base_vals = [name, 1 if is_central else 0, area, scan_policy]
            for k in ['latitude', 'longitude', 'camera_number', 'address',
                      'street', 'neighborhood', 'matrix', 'camera_type',
                      'direction', 'notes']:
                if k in extra:
                    base_cols.append(k)
                    base_vals.append(extra[k])
            placeholders = ','.join('?' * len(base_vals))
            conn.execute(
                f"INSERT INTO cameras ({','.join(base_cols)}) VALUES ({placeholders})",
                base_vals,
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def bulk_add_cameras(names, is_central=False):
    added = 0
    with get_conn() as conn:
        for name in names:
            name = (name or '').strip()
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


def bulk_add_cameras_structured(camera_data, is_central=False):
    """camera_data: list of (name, area) or (name, area, scan_policy) tuples"""
    added = 0
    with get_conn() as conn:
        for item in camera_data:
            if len(item) == 3:
                name, area, scan_policy = item
            else:
                name, area = item
                scan_policy = ''
            name = (name or '').strip()
            if not name:
                continue
            try:
                conn.execute(
                    "INSERT INTO cameras (name, is_central, area, scan_policy) "
                    "VALUES (?, ?, ?, ?)",
                    (name, 1 if is_central else 0, area or '', scan_policy or ''),
                )
                added += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
    return added


def get_all_cameras():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cameras WHERE is_active = 1 "
            "ORDER BY is_central DESC, id ASC"
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


def get_all_areas():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT area FROM cameras WHERE is_active = 1 "
            "AND area IS NOT NULL AND area != '' ORDER BY area"
        ).fetchall()
        return [r['area'] for r in rows]


def update_camera(camera_id, name=None, is_central=None, area=None, scan_policy=None, **extra):
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
            conn.execute(
                "UPDATE cameras SET scan_policy = ? WHERE id = ?",
                (scan_policy, camera_id),
            )
        for k in ['latitude', 'longitude', 'camera_number', 'address', 'street',
                  'neighborhood', 'matrix', 'camera_type', 'direction',
                  'camera_status', 'notes']:
            if k in extra:
                conn.execute(
                    f"UPDATE cameras SET {k} = ? WHERE id = ?",
                    (extra[k], camera_id),
                )
        conn.commit()


def delete_camera(camera_id):
    with get_conn() as conn:
        conn.execute("UPDATE cameras SET is_active = 0 WHERE id = ?", (camera_id,))
        conn.commit()


def update_camera_location(camera_id, latitude, longitude):
    with get_conn() as conn:
        conn.execute(
            "UPDATE cameras SET latitude = ?, longitude = ? WHERE id = ?",
            (latitude, longitude, camera_id),
        )
        conn.commit()


def get_mapped_cameras():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cameras WHERE is_active = 1 "
            "AND latitude IS NOT NULL AND longitude IS NOT NULL "
            "ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_unmapped_cameras():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cameras WHERE is_active = 1 "
            "AND (latitude IS NULL OR longitude IS NULL) ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


# ==================== תקלות מצלמות (v1) ====================
def add_fault(camera_id, fault_datetime, description, reported_by=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO faults (camera_id, fault_datetime, description, reported_by) "
            "VALUES (?, ?, ?, ?)",
            (camera_id, fault_datetime, description, reported_by),
        )
        conn.commit()


def get_active_faults():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT f.*, c.name as camera_name FROM faults f "
            "JOIN cameras c ON f.camera_id = c.id "
            "WHERE f.resolved = 0 ORDER BY f.fault_datetime DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_faults():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT f.*, c.name as camera_name FROM faults f "
            "JOIN cameras c ON f.camera_id = c.id ORDER BY f.fault_datetime DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def resolve_fault(fault_id, resolved_by=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE faults SET resolved = 1, resolved_at = ?, resolved_by = ? WHERE id = ?",
            (_now_iso(), resolved_by, fault_id),
        )
        conn.commit()


def delete_fault(fault_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM faults WHERE id = ?", (fault_id,))
        conn.commit()


def is_camera_faulty(camera_id):
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


# ==================== סריקות ישנות (v1) - נשאר לתאימות ====================
def mark_scan(camera_id, scheduled_hour, scanned_by="", status="ok", event_details=None, event_category=None):
    """
    מסמן סריקה כבוצעה. **נעילה מעריכה** - אם הסריקה כבר סומנה בעבר, לא ניתן לשנות אותה.
    event_category: 'security' | 'dumping' | 'safety' | 'other' | None
    """
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT scanned_at FROM scans WHERE camera_id = ? AND scheduled_hour = ? AND scanned_at IS NOT NULL",
            (camera_id, scheduled_hour),
        ).fetchone()
        if existing:
            return False
        conn.execute(
            "INSERT INTO scans (camera_id, scheduled_hour, scanned_at, scanned_by, status, event_details, event_category) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(camera_id, scheduled_hour) DO UPDATE SET "
            "scanned_at=excluded.scanned_at, scanned_by=excluded.scanned_by, "
            "status=excluded.status, event_details=excluded.event_details, "
            "event_category=excluded.event_category",
            (camera_id, scheduled_hour, _now_iso(), scanned_by, status, event_details, event_category),
        )
        conn.commit()
        return True


def unmark_scan(camera_id, scheduled_hour):
    """
    ⚠️ נעילת מעקב - סריקה שסומנה לא ניתנת לביטול.
    זה מבטיח מעקב אמיתי אחרי מה בוצע ומתי.
    """
    # ביודעים - לא עושה כלום. זה נעילה מכוונת.
    return False


def get_scans_for_hour(scheduled_hour):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT camera_id, scanned_at, scanned_by, status, event_details "
            "FROM scans WHERE scheduled_hour = ?", (scheduled_hour,),
        ).fetchall()
        return {r['camera_id']: dict(r) for r in rows}


def get_scans_in_range(start_hour, end_hour):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT s.*, c.name as camera_name FROM scans s "
            "JOIN cameras c ON s.camera_id = c.id "
            "WHERE s.scheduled_hour BETWEEN ? AND ? "
            "ORDER BY s.scheduled_hour DESC, c.name ASC",
            (start_hour, end_hour),
        ).fetchall()
        return [dict(r) for r in rows]


def get_issue_scans_in_range(start_hour, end_hour):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT s.*, c.name as camera_name FROM scans s "
            "JOIN cameras c ON s.camera_id = c.id "
            "WHERE s.scheduled_hour BETWEEN ? AND ? AND s.status = 'issue' "
            "ORDER BY s.scheduled_hour DESC, c.name ASC",
            (start_hour, end_hour),
        ).fetchall()
        return [dict(r) for r in rows]


# ==================== הגדרות ====================
def get_setting(key, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row['value'] if row else default


def set_setting(key, value):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        conn.commit()


# ==================== איפוסים (v1) ====================
def reset_scans_and_faults():
    with get_conn() as conn:
        conn.execute("DELETE FROM scans")
        conn.execute("DELETE FROM faults")
        conn.commit()


def reset_all_data():
    """מוחק סריקות, תקלות, מצלמות. שומר משתמשים והגדרות."""
    with get_conn() as conn:
        conn.execute("DELETE FROM scans")
        conn.execute("DELETE FROM faults")
        conn.execute("DELETE FROM cameras")
        conn.commit()
def refresh_operators():
    """מסיר את מוקדן 1-4 הישנים ומכניס את השמות האמיתיים. מריצים פעם אחת."""
    with get_conn() as conn:
        cursor = conn.cursor()
        # מחיקת המוקדנים הזמניים
        cursor.execute("DELETE FROM users WHERE role = 'operator' AND username LIKE 'operator%'")

        # שמות אמיתיים
        real_operators = [
            ('riki', 'ריקי'),
            ('sarit', 'שרית'),
            ('itai', 'איתי'),
            ('mai', 'מאי'),
            ('elinor', 'אלינור'),
            ('tali', 'טלי'),
            ('sima', 'סימה'),
            ('guy', 'גיא'),
            ('lev', 'לב'),
            ('shani', 'שני'),
            ('liron', 'לירון'),
            ('ronit', 'רונית'),
        ]
        for username, name in real_operators:
            try:
                cursor.execute(
                    "INSERT INTO users (username, name, role) VALUES (?, ?, 'operator')",
                    (username, name),
                )
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        return len(real_operators)
# ==================== לו"ז סריקות דינמי ====================
def add_scheduled_plan(name, start_time, end_time, camera_ids=None,
                       days_of_week='all', priority='medium',
                       description='', active=True):
    """
    יוצר חלון זמן חדש בלו"ז הסריקות.
    days_of_week: 'all' או מחרוזת ימי שבוע מופרדת בפסיקים ('0,1,2' - Mon=0, Sun=6)
    """
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO scheduled_scan_plans "
                "(name, description, start_time, end_time, days_of_week, "
                "camera_ids_json, priority, active) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, description, start_time, end_time, days_of_week,
                 json.dumps(camera_ids or []), priority, 1 if active else 0),
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def get_all_scheduled_plans(active_only=True):
    """מחזיר את כל התוכניות בלו"ז"""
    with get_conn() as conn:
        q = "SELECT * FROM scheduled_scan_plans"
        if active_only:
            q += " WHERE active = 1"
        q += " ORDER BY start_time ASC"
        rows = conn.execute(q).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['camera_ids'] = json.loads(d.get('camera_ids_json') or '[]')
            result.append(d)
        return result


def update_scheduled_plan(plan_id, **kwargs):
    with get_conn() as conn:
        updates, params = [], []
        for k, v in kwargs.items():
            if k == 'camera_ids':
                updates.append("camera_ids_json = ?")
                params.append(json.dumps(v or []))
            elif k in ['name', 'description', 'start_time', 'end_time',
                       'days_of_week', 'priority']:
                updates.append(f"{k} = ?")
                params.append(v)
            elif k == 'active':
                updates.append("active = ?")
                params.append(1 if v else 0)
        if updates:
            params.append(plan_id)
            conn.execute(
                f"UPDATE scheduled_scan_plans SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()


def delete_scheduled_plan(plan_id):
    with get_conn() as conn:
        conn.execute("UPDATE scheduled_scan_plans SET active = 0 WHERE id = ?", (plan_id,))
        conn.commit()


def get_active_scan_plans_for_datetime(dt):
    """
    מחזיר את כל התוכניות שרלוונטיות לרגע נתון (שעה + יום שבוע).
    """
    current_time_str = dt.strftime("%H:%M")
    current_weekday = str(dt.weekday())  # Python: Mon=0, Sun=6

    all_plans = get_all_scheduled_plans(active_only=True)
    matching = []

    for p in all_plans:
        # בדיקת יום שבוע
        days = p.get('days_of_week', 'all')
        if days and days != 'all':
            allowed_days = days.split(',')
            if current_weekday not in allowed_days:
                continue

        # בדיקת חלון זמן
        start = p.get('start_time', '')
        end = p.get('end_time', '')
        if not start or not end:
            continue

        if start <= end:
            # חלון רגיל (לא חוצה חצות)
            if start <= current_time_str < end:
                matching.append(p)
        else:
            # חלון שחוצה חצות (למשל 23:00-07:00)
            if current_time_str >= start or current_time_str < end:
                matching.append(p)

    return matching
