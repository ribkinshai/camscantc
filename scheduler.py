"""
מודול לו"ז הסריקות - יצירת לוח זמנים וזיהוי סריקות שהוחמצו
Scheduler: schedule generation, rotation logic, missed scan detection
"""
import math
from datetime import datetime, timedelta

import database as db

# עוגן זמן קבוע לחישוב הסבב - כדי שהסבב יהיה עקבי בין הפעלות
EPOCH = datetime(2024, 1, 1, 0, 0, 0)


def hour_key(dt: datetime) -> str:
    """המפתח הקנוני של שעה - YYYY-MM-DD HH:00"""
    return dt.strftime("%Y-%m-%d %H:00")


def get_shift_name(dt: datetime) -> str:
    """זיהוי משמרת לפי שעה"""
    morning_start = int(db.get_setting('shift_morning_start', '7'))
    evening_start = int(db.get_setting('shift_evening_start', '15'))
    night_start = int(db.get_setting('shift_night_start', '23'))
    hour = dt.hour
    if morning_start <= hour < evening_start:
        return "בוקר"
    elif evening_start <= hour < night_start:
        return "ערב"
    else:
        return "לילה"


def get_cameras_for_hour(dt: datetime, include_faulty: bool = False):
    """
    החזרת המצלמות שאמורות להיסרק בשעה מסוימת.
    מצלמות מרכזיות תמיד נכללות; מצלמות רגילות מסתובבות לפי אינדקס השעה.
    """
    central = db.get_central_cameras()
    rotating = db.get_rotating_cameras()

    if not include_faulty:
        faulty_ids = db.get_faulty_camera_ids()
        central = [c for c in central if c['id'] not in faulty_ids]
        rotating = [c for c in rotating if c['id'] not in faulty_ids]

    rotating_count = int(db.get_setting('rotating_count', '20'))

    if not rotating or rotating_count <= 0:
        return central, []

    # חישוב אינדקס שעה מהעוגן
    dt_hour = dt.replace(minute=0, second=0, microsecond=0)
    hour_index = int((dt_hour - EPOCH).total_seconds() // 3600)

    total_rot = len(rotating)
    if rotating_count >= total_rot:
        return central, rotating

    num_groups = math.ceil(total_rot / rotating_count)
    group = hour_index % num_groups
    start = group * rotating_count
    end = start + rotating_count
    selected = rotating[start:end]

    # אם הקבוצה האחרונה קטנה - נשלים מההתחלה
    if len(selected) < rotating_count:
        needed = rotating_count - len(selected)
        selected = selected + rotating[:needed]

    return central, selected


def get_missed_scans(now: datetime, lookback_hours: int = 8):
    """
    החזרת רשימה של סריקות שהוחמצו.
    לכל שעה בטווח הבדיקה - מחזירה (hour_key, camera) לכל מצלמה שלא נסרקה.
    """
    missed = []
    grace_minutes = int(db.get_setting('alert_grace_minutes', '15'))
    current_hour = now.replace(minute=0, second=0, microsecond=0)

    # בדיקה של שעות שעברו
    for i in range(1, lookback_hours + 1):
        past_hour = current_hour - timedelta(hours=i)
        past_key = hour_key(past_hour)
        central, rotating = get_cameras_for_hour(past_hour, include_faulty=False)
        expected = central + rotating
        scanned = db.get_scans_for_hour(past_key)
        for cam in expected:
            if cam['id'] not in scanned:
                missed.append((past_key, cam))

    # בדיקה של השעה הנוכחית - רק אחרי זמן החסד
    if now.minute >= grace_minutes:
        current_key = hour_key(current_hour)
        central, rotating = get_cameras_for_hour(current_hour, include_faulty=False)
        expected = central + rotating
        scanned = db.get_scans_for_hour(current_key)
        for cam in expected:
            if cam['id'] not in scanned:
                missed.append((current_key, cam))

    return missed


def get_upcoming_schedule(start_dt: datetime, hours: int = 24):
    """יצירת לו"ז ל-N השעות הקרובות"""
    schedule = []
    start_dt = start_dt.replace(minute=0, second=0, microsecond=0)
    for i in range(hours):
        dt = start_dt + timedelta(hours=i)
        central, rotating = get_cameras_for_hour(dt, include_faulty=False)
        schedule.append({
            'datetime': dt,
            'hour_key': hour_key(dt),
            'shift': get_shift_name(dt),
            'central': central,
            'rotating': rotating,
        })
    return schedule
