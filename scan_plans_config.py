"""
תוכנית הצפייה - מוקד רואה 106 טירת כרמל
מוגדר מהספק שהתקבל. סריקות נעשות כל 30 דקות לפי חלוקת שעות.
המנהלת יכולה לערוך את התוכנית בעתיד דרך UI (יישמר ב-settings JSON).
"""
from datetime import datetime, time

# ============ תוכניות סריקה לפי שעות היום ============
# כל רשומה מגדירה חלון זמן ואת סוג/תוכן הסריקה עבורו
# fields: start_hour, end_hour (24-hour, exclusive), plan_type, name, description, categories, alert

PLANS = [
    {
        'start_hour': 7, 'end_hour': 9,
        'plan_type': 'morning_regular',
        'name': 'מוסדות חינוך + צירי תנועה + אתרי בנייה',
        'description': 'סריקת מוסדות חינוך, צירים ראשיים ואתרי בנייה',
        'categories': ['schools', 'roads', 'construction'],
        'alert': None,
    },
    {
        'start_hour': 9, 'end_hour': 11,
        'plan_type': 'load_hotspots',
        'name': 'מתכונת עומס - נקודות חמות',
        'description': 'שעות עומס במוקד - סריקה של נקודות חמות בלבד',
        'categories': ['hotspots'],
        'alert': '⚠️ מתכונת עומס: סריקת נקודות חמות בלבד',
    },
    {
        'start_hour': 11, 'end_hour': 13,
        'plan_type': 'proactive_urban',
        'name': 'סריקה עירונית יזומה',
        'description': 'איתור פסולת, גזם, מפגעי ניקיון, ונדליזם, בטיחות. יעד: פתיחת פניות יזומות',
        'categories': ['urban_proactive'],
        'alert': '💡 סריקה יזומה - איתור מפגעים ופתיחת פניות',
    },
    {
        'start_hour': 13, 'end_hour': 16,
        'plan_type': 'public_buildings',
        'name': 'מבני ציבור + מוסדות חינוך + צירים',
        'description': 'ספרייה, עירייה, רווחה, מוסדות חינוך (דגש על יציאת תלמידים), צירי כניסה/יציאה',
        'categories': ['public_buildings', 'schools_dismissal', 'roads'],
        'alert': None,
    },
    {
        'start_hour': 16, 'end_hour': 20,
        'plan_type': 'parks',
        'name': 'פארקים וגינות משחקים',
        'description': 'גני משחקים ופארקים - דגש על ונדליזם, רעש, התקהלות, פגיעה במתקנים',
        'categories': ['parks'],
        'alert': None,
    },
    {
        'start_hour': 20, 'end_hour': 23,
        'plan_type': 'youth_activity',
        'name': 'פארקים וצירים - פעילות נוער',
        'description': 'ציר ז\'בוטינסקי, סקייטפארק, פארק הנינג\'ה - דגש על שוטטות, קטטות, ונדליזם',
        'categories': ['youth_hotspots'],
        'alert': None,
    },
    {
        'start_hour': 23, 'end_hour': 5,
        'plan_type': 'night',
        'name': 'נקודות חמות + אתרי בנייה + כניסות/יציאות',
        'description': 'שעות לילה - דגש על פעילות חשודה, פריצות, גניבות, רכבים חשודים',
        'categories': ['hotspots', 'construction', 'roads_gates'],
        'alert': '🌙 משמרת לילה - בדיקת קשר כל 30 דקות!',
    },
    {
        'start_hour': 5, 'end_hour': 7,
        'plan_type': 'early_morning',
        'name': 'צירי כניסה/יציאה + אתרי בנייה',
        'description': 'שעות הבוקר המוקדמות',
        'categories': ['roads_gates', 'construction'],
        'alert': None,
    },
]


# ============ קטגוריות מוקדים ============
# מגדיר אילו מוקדים שייכים לאיזה קטגוריה
# כל מוקד יכול להיות מיוצג ע"י שם + הערה על כיסוי (יש מצלמה / אין מצלמה)

CATEGORIES = {
    # מוסדות חינוך
    'schools': [
        {'name': 'יגאל אלון', 'has_camera': True},
        {'name': 'נוף ים', 'has_camera': True},
        {'name': 'החותרים', 'has_camera': True},
        {'name': 'שיפמן', 'has_camera': True},
        {'name': 'דגניה', 'has_camera': False, 'note': 'פער כיסוי - אין מצלמה'},
        {'name': 'זבולון', 'has_camera': False, 'note': 'פער כיסוי - אין מצלמה'},
        {'name': 'ברזני', 'has_camera': False, 'note': 'פער כיסוי - אין מצלמה'},
        {'name': 'אפרים צמח', 'has_camera': False, 'note': 'פער כיסוי - אין מצלמה'},
        {'name': 'קמפוס', 'has_camera': False, 'note': 'פער כיסוי - אין מצלמה'},
        {'name': 'אריאל', 'has_camera': False, 'note': 'פער כיסוי - אין מצלמה'},
        {'name': 'יובל', 'has_camera': False, 'note': 'פער כיסוי - אין מצלמה'},
    ],

    'schools_dismissal': [
        {'name': 'יגאל אלון (יציאת תלמידים)', 'has_camera': True},
        {'name': 'נוף ים (יציאת תלמידים)', 'has_camera': True},
        {'name': 'החותרים (יציאת תלמידים)', 'has_camera': True},
        {'name': 'שיפמן (יציאת תלמידים)', 'has_camera': True},
    ],

    # צירי תנועה
    'roads': [
        {'name': 'כניסה/יציאה צפונית', 'has_camera': True},
        {'name': 'כניסה/יציאה אמצעית - ז\'בוטינסקי', 'has_camera': True},
        {'name': 'כניסה/יציאה דרומית', 'has_camera': True},
    ],

    'roads_gates': [
        {'name': 'כניסה צפונית', 'has_camera': True},
        {'name': 'יציאה צפונית', 'has_camera': True},
        {'name': 'כניסה דרומית', 'has_camera': True},
        {'name': 'יציאה דרומית', 'has_camera': True},
        {'name': 'ז\'בוטינסקי - אמצע', 'has_camera': True},
    ],

    # אתרי בנייה - יטענו דינאמית מהטבלה, זה default fallback
    'construction': [
        {'name': 'בית הספר החדש בנוף ים', 'has_camera': True},
    ],

    # נקודות חמות עומס (בוקר עומס וגם לילה)
    'hotspots': [
        {'name': 'סקייטפארק', 'has_camera': True},
        {'name': 'גן נחום', 'has_camera': True},
        {'name': 'יצחק שמיר', 'has_camera': True},
        {'name': 'כיכר החותרים', 'has_camera': True},
        {'name': 'בניין העירייה', 'has_camera': True},
    ],

    # סריקה עירונית יזומה
    'urban_proactive': [
        {'name': 'סריקת פסולת בעיר', 'has_camera': True,
         'note': 'איתור השלכות פסולת/גזם/ונדליזם'},
        {'name': 'מפגעי בטיחות', 'has_camera': True,
         'note': 'בורות, מכשולים, מפגעים'},
        {'name': 'צירים ראשיים - ניקיון', 'has_camera': True},
    ],

    # מבני ציבור
    'public_buildings': [
        {'name': 'ספרייה עירונית', 'has_camera': True},
        {'name': 'בניין העירייה', 'has_camera': True},
        {'name': 'רווחה', 'has_camera': True, 'note': 'בדיקת מצלמות רלוונטיות'},
    ],

    # פארקים
    'parks': [
        {'name': 'גן חרצית', 'has_camera': False, 'note': 'פער כיסוי'},
        {'name': 'גן יצחק שמיר', 'has_camera': True},
        {'name': 'סקייטפארק', 'has_camera': True},
        {'name': 'גן נחום', 'has_camera': True},
        {'name': 'נחל גלים', 'has_camera': True},
        {'name': 'מנחם בגין', 'has_camera': False, 'note': 'פער כיסוי'},
        {'name': 'גן נדיר', 'has_camera': False, 'note': 'פער כיסוי'},
        {'name': 'חניון מונהיים', 'has_camera': True},
        {'name': 'גן הזריחה', 'has_camera': True},
        {'name': 'פארק הנינג\'ה', 'has_camera': False, 'note': 'פער כיסוי'},
    ],

    # נוער ושוטטות
    'youth_hotspots': [
        {'name': 'ציר ז\'בוטינסקי - לכל אורכו', 'has_camera': True},
        {'name': 'סקייטפארק', 'has_camera': True},
        {'name': 'פארק הנינג\'ה', 'has_camera': False, 'note': 'פער כיסוי'},
    ],
}


# ============ פונקציות עזר ============
def get_plan_for_time(dt):
    """מחזיר את התוכנית שרלוונטית לזמן נתון"""
    hour = dt.hour
    for plan in PLANS:
        s, e = plan['start_hour'], plan['end_hour']
        if s < e:
            if s <= hour < e:
                return plan
        else:  # crosses midnight (e.g. 23-5)
            if hour >= s or hour < e:
                return plan
    return None


def get_locations_for_plan(plan):
    """מחזיר רשימת מוקדים לסריקה עבור תוכנית - איחוד קטגוריות"""
    if not plan:
        return []
    locations = []
    seen_names = set()
    for cat_key in plan.get('categories', []):
        for loc in CATEGORIES.get(cat_key, []):
            if loc['name'] not in seen_names:
                locations.append({
                    'name': loc['name'],
                    'has_camera': loc.get('has_camera', True),
                    'note': loc.get('note', ''),
                    'category': cat_key,
                })
                seen_names.add(loc['name'])
    return locations


def get_all_time_slots(shift_start, shift_end):
    """יוצר רשימת סלוטים של חצי שעה בין תחילת המשמרת לסופה"""
    slots = []
    current = shift_start.replace(minute=0, second=0, microsecond=0)
    # אם המשמרת מתחילה בחצי שעה, התאם
    if shift_start.minute >= 30:
        current = current.replace(minute=30)
    while current < shift_end:
        slots.append(current)
        # דלג 30 דקות
        m = current.minute
        if m == 0:
            current = current.replace(minute=30)
        else:
            new_hour = (current.hour + 1) % 24
            if new_hour == 0:
                # חדש יום
                from datetime import timedelta
                current = (current + timedelta(hours=1)).replace(minute=0)
            else:
                current = current.replace(hour=new_hour, minute=0)
    return slots


def get_plan_type_by_shift_type(shift_type):
    """מחזיר את סוג התוכנית העיקרי עבור סוג משמרת"""
    if shift_type == 'morning':
        return 'morning_regular'
    if shift_type == 'evening':
        return 'parks'
    if shift_type == 'night':
        return 'night'
    return 'morning_regular'
