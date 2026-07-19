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
    (priority_cameras, rotating_cameras)
    - priority: מצלמות עם מדיניות סריקה שתואמת לשעה זו
    - rotating: מצלמות בסבב רגיל שנבחרות לפי אינדקס השעה
    """
    from scan_policies import should_scan

    all_cams = db.get_all_cameras()

    if not include_faulty:
        faulty_ids = db.get_faulty_camera_ids()
        all_cams = [c for c in all_cams if c['id'] not in faulty_ids]

    priority = []
    rotating_pool = []

    for cam in all_cams:
        policy = (cam.get('scan_policy') or '').strip()
        # Backward compat: מצלמות שסומנו כ-is_central בלי מדיניות מפורשת = every_hour
        if not policy and cam.get('is_central'):
            policy = 'every_hour'

        if policy:
            if should_scan(policy, dt):
                priority.append(cam)
            # אם המדיניות לא תואמת - המצלמה לא מופיעה בשעה זו
        else:
            rotating_pool.append(cam)

    rotating_count = int(db.get_setting('rotating_count', '20'))

    if not rotating_pool or rotating_count <= 0:
        return priority, []

    dt_hour = dt.replace(minute=0, second=0, microsecond=0)
    hour_index = int((dt_hour - EPOCH).total_seconds() // 3600)

    total_rot = len(rotating_pool)
    if rotating_count >= total_rot:
        return priority, rotating_pool

    num_groups = math.ceil(total_rot / rotating_count)
    group = hour_index % num_groups
    start = group * rotating_count
    end = start + rotating_count
    selected = rotating_pool[start:end]

    if len(selected) < rotating_count:
        needed = rotating_count - len(selected)
        selected = selected + rotating_pool[:needed]

    return priority, selected
