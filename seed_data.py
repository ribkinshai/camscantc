"""
סקריפט אכלוס נתוני דמה - 200 מצלמות
Seed 200 dummy cameras for testing:
  - 10 קבועות (מרכזיות)
  - 190 מתחלפות

יכול לרוץ בשתי דרכים:
  1. מקומית מהטרמינל:  python seed_data.py
  2. מתוך האפליקציה: הגדרות → כפתור "טען 200 מצלמות דמה"

בטוח להרצה מרובה - לא ייווצרו כפילויות.
"""
import database as db


# 10 מצלמות קבועות - נסרקות בכל שעה
CENTRAL_CAMERAS = [
    "כניסה ראשית",
    "יציאת חירום מרכזית",
    "לובי קבלה",
    "עמדת אבטחה",
    "חדר בקרה",
    "מעלית מרכזית - קומת קרקע",
    "כניסת שירות",
    "חניון - כניסה ראשית",
    "חניון - יציאה ראשית",
    "שער היקפי - ראשי",
]


def generate_rotating_cameras():
    """יצירת 190 מצלמות מתחלפות במגוון אזורים במוקד"""
    cams = []

    # מסדרונות: 10 קומות × 4 אגפים = 40
    for floor in range(1, 11):
        for section in ["צפון", "דרום", "מזרח", "מערב"]:
            cams.append(f"מסדרון קומה {floor} - אגף {section}")

    # מעליות: 6 מעליות × 5 נקודות = 30
    for elev in range(1, 7):
        for spot in ["קרקע", "קומה 3", "קומה 6", "קומה 9", "מעל הגג"]:
            cams.append(f"מעלית {elev} - {spot}")

    # חדרי מדרגות: 4 חדרים × 10 קומות = 40
    for stair in ["A", "B", "C", "D"]:
        for floor in range(1, 11):
            cams.append(f"חדר מדרגות {stair} - קומה {floor}")

    # חניון תת קרקעי: 4 קומות × 5 מצלמות = 20
    for level in range(1, 5):
        for i in range(1, 6):
            cams.append(f"חניון קומה -{level} - מצלמה {i}")

    # אזורים משותפים בקומות: 10 קומות × 2 = 20
    for floor in range(1, 11):
        cams.append(f"אזור המתנה קומה {floor}")
        cams.append(f"פינת שירותים קומה {floor}")

    # גדרות היקפיות: 20 נקודות
    for i in range(1, 21):
        cams.append(f"גדר היקפית - נקודה {i:02d}")

    # כניסות משניות: 5
    for i in range(1, 6):
        cams.append(f"כניסה משנית {i}")

    # גגות: 3
    for side in ["צפוני", "דרומי", "מזרחי"]:
        cams.append(f"גג - צד {side}")

    # מחסנים: 7
    for i in range(1, 8):
        cams.append(f"מחסן {i}")

    # מטבחונים בקומות זוגיות: 5
    for floor in [2, 4, 6, 8, 10]:
        cams.append(f"מטבחון קומה {floor}")

    return cams


def seed_demo_data():
    """טעינת 200 מצלמות דמה למסד. מחזיר סיכום הפעולה."""
    db.init_db()
    existing = {c['name'] for c in db.get_all_cameras()}

    added_central = 0
    for name in CENTRAL_CAMERAS:
        if name not in existing:
            if db.add_camera(name, is_central=True):
                added_central += 1

    rotating = generate_rotating_cameras()
    added_rotating = 0
    for name in rotating:
        if name not in existing:
            if db.add_camera(name, is_central=False):
                added_rotating += 1

    return {
        'central_added': added_central,
        'rotating_added': added_rotating,
        'central_planned': len(CENTRAL_CAMERAS),
        'rotating_planned': len(rotating),
        'total_now': len(db.get_all_cameras()),
    }


if __name__ == "__main__":
    print("טוען 200 מצלמות דמה...")
    result = seed_demo_data()
    print(f"נוספו {result['central_added']}/{result['central_planned']} מצלמות קבועות")
    print(f"נוספו {result['rotating_added']}/{result['rotating_planned']} מצלמות מתחלפות")
    print(f"סה\"כ מצלמות כעת במסד: {result['total_now']}")
