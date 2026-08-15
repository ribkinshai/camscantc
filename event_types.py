"""
הגדרות של סוגי אירועים וקטגוריות שקשורות למערכת המוקד.
לפי הספק - סקציה 7-9.
"""

# ============ סוגי אירועים ============
EVENT_TYPES = [
    {'key': 'trash_dump', 'label': 'השלכת פסולת', 'requires_details': 'dumping'},
    {'key': 'trash', 'label': 'פסולת / גזם'},
    {'key': 'vandalism', 'label': 'ונדליזם'},
    {'key': 'noise', 'label': 'רעש'},
    {'key': 'gathering', 'label': 'התקהלות'},
    {'key': 'violence', 'label': 'אלימות / קטטה'},
    {'key': 'criminal', 'label': 'אירוע פלילי', 'alert': 'יש לפעול בהתאם לנוהל ולדווח למשטרת ישראל / גורמי חירום.'},
    {'key': 'safety_hazard', 'label': 'מפגע בטיחות'},
    {'key': 'construction_site', 'label': 'אירוע באתר בנייה'},
    {'key': 'suspicious_vehicle', 'label': 'רכב חשוד'},
    {'key': 'suspicious_activity', 'label': 'פעילות חשודה'},
    {'key': 'camera_fault', 'label': 'תקלת מצלמה', 'requires_details': 'camera_fault'},
    {'key': 'other', 'label': 'אחר'},
]


# ============ גורמי טיפול ============
HANDLING_BODIES = [
    {'key': 'inspection', 'label': 'פיקוח'},
    {'key': 'municipal_police', 'label': 'שיטור עירוני'},
    {'key': 'israel_police', 'label': 'משטרת ישראל'},
    {'key': 'firefighters', 'label': 'כבאות והצלה'},
    {'key': 'mda', 'label': 'מד"א'},
    {'key': 'other', 'label': 'גורם אחר'},
]


# ============ סטטוסים ============
EVENT_STATUSES = [
    {'key': 'new', 'label': 'חדש', 'color': 'blue'},
    {'key': 'forwarded', 'label': 'הועבר לטיפול', 'color': 'orange'},
    {'key': 'force_en_route', 'label': 'כוח בדרך', 'color': 'orange'},
    {'key': 'handling', 'label': 'בטיפול', 'color': 'orange'},
    {'key': 'closed', 'label': 'טופל', 'color': 'green'},
    {'key': 'not_found', 'label': 'לא אותר', 'color': 'gray'},
    {'key': 'forwarded_further', 'label': 'הועבר להמשך טיפול', 'color': 'blue'},
]


# ============ סיבות לאי-ביצוע סריקה ============
NOT_DONE_REASONS = [
    {'key': 'call_load', 'label': 'עומס שיחות'},
    {'key': 'active_event', 'label': 'אירוע פעיל'},
    {'key': 'camera_issue', 'label': 'תקלה במצלמות'},
    {'key': 'other_mission', 'label': 'משימה מבצעית אחרת'},
    {'key': 'other', 'label': 'אחר', 'requires_details': True},
]


# ============ סוגי משמרת ============
SHIFT_TYPES = [
    {'key': 'morning', 'label': 'בוקר', 'default_start': 7, 'default_end': 15},
    {'key': 'evening', 'label': 'ערב', 'default_start': 15, 'default_end': 23},
    {'key': 'night', 'label': 'לילה', 'default_start': 23, 'default_end': 7},
]


# ============ סוגי תרגילים ============
DRILL_TYPES = [
    {'key': 'weekly_dry', 'label': 'תרגיל שבועי יבש'},
    {'key': 'monthly_combined', 'label': 'תרגיל חודשי משולב'},
    {'key': 'quarterly_complex', 'label': 'תרגיל רבעוני מורכב'},
]


# ============ עדיפויות (לנקודות חמות ומבצעים) ============
PRIORITIES = [
    {'key': 'high', 'label': 'גבוהה', 'color': 'red'},
    {'key': 'medium', 'label': 'בינונית', 'color': 'orange'},
    {'key': 'low', 'label': 'נמוכה', 'color': 'green'},
]


# ============ סטטוסים לסריקה ============
SCAN_STATUSES = [
    {'key': 'pending', 'label': 'טרם בוצע', 'color': 'gray', 'icon': '⏳'},
    {'key': 'no_findings', 'label': 'בוצע ללא ממצא', 'color': 'green', 'icon': '✅'},
    {'key': 'has_event', 'label': 'בוצע עם אירוע', 'color': 'orange', 'icon': '⚠️'},
    {'key': 'not_done', 'label': 'לא בוצע', 'color': 'red', 'icon': '❌'},
]


# ============ פונקציות עזר ============
def get_event_type(key):
    for et in EVENT_TYPES:
        if et['key'] == key:
            return et
    return None


def get_event_type_label(key):
    et = get_event_type(key)
    return et['label'] if et else key


def get_handling_body_label(key):
    for hb in HANDLING_BODIES:
        if hb['key'] == key:
            return hb['label']
    return key


def get_status_label(key):
    for s in EVENT_STATUSES:
        if s['key'] == key:
            return s['label']
    return key


def get_scan_status_info(key):
    for s in SCAN_STATUSES:
        if s['key'] == key:
            return s
    return {'key': key, 'label': key, 'color': 'gray', 'icon': '?'}


def get_shift_type_label(key):
    for st in SHIFT_TYPES:
        if st['key'] == key:
            return st['label']
    return key


def get_shift_type_from_time(dt, settings=None):
    """זיהוי סוג משמרת לפי שעה"""
    hour = dt.hour
    if settings:
        morning = int(settings.get('shift_morning_start', 7))
        evening = int(settings.get('shift_evening_start', 15))
        night = int(settings.get('shift_night_start', 23))
    else:
        morning, evening, night = 7, 15, 23

    if morning <= hour < evening:
        return 'morning'
    elif evening <= hour < night:
        return 'evening'
    else:
        return 'night'


def get_not_done_reason_label(key):
    for r in NOT_DONE_REASONS:
        if r['key'] == key:
            return r['label']
    return key
