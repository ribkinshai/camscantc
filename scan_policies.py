"""
מדיניות סריקה - הגדרת חוקים לתדירות סריקה של מצלמות
Scan policies - rules defining when specific cameras must be scanned.
"""

POLICY_DESCRIPTIONS = {
    'every_hour': 'בכל שעה',
    'every_3h': 'כל 3 שעות (00, 03, 06...)',
    'evening_2h': 'כל שעתיים מ-16:00 (16, 18, 20, 22)',
    'evening_hourly': 'כל שעה מ-16:00',
    'night_hourly': 'כל שעה מ-20:00',
    'weekend_summer_night': 'שישי/שבת + יולי-אוגוסט מ-21:00',
}


def should_scan(policy_name, dt):
    """
    בדיקה אם מצלמה עם מדיניות מסוימת צריכה להיסרק בזמן מסוים.
    Check if a camera with the given policy should be scanned at datetime dt.

    dt: datetime object (מומלץ בשעון ישראל / recommended: Israel timezone)
    """
    if not policy_name:
        return False

    hour = dt.hour
    weekday = dt.weekday()  # Mon=0, Fri=4, Sat=5, Sun=6
    month = dt.month

    if policy_name == 'every_hour':
        return True

    if policy_name == 'every_3h':
        # נסרק ב-00, 03, 06, 09, 12, 15, 18, 21
        return hour % 3 == 0

    if policy_name == 'evening_2h':
        # מ-16:00 כל שעתיים: 16, 18, 20, 22
        if hour < 16:
            return False
        return (hour - 16) % 2 == 0

    if policy_name == 'evening_hourly':
        # מ-16:00 כל שעה: 16-23
        return hour >= 16

    if policy_name == 'night_hourly':
        # מ-20:00 כל שעה: 20-23
        return hour >= 20

    if policy_name == 'weekend_summer_night':
        # מ-21:00 בשישי/שבת או ביולי/אוגוסט
        if hour < 21:
            return False
        if month in [7, 8]:  # יולי / אוגוסט
            return True
        if weekday in [4, 5]:  # שישי / שבת
            return True
        return False

    # Unknown policy - default to no scan
    return False


if __name__ == "__main__":
    from datetime import datetime
    # Verification tests
    test_cases = [
        # (policy, datetime, expected)
        ('every_hour', datetime(2026, 7, 14, 3), True),
        ('every_3h', datetime(2026, 7, 14, 3), True),
        ('every_3h', datetime(2026, 7, 14, 4), False),
        ('every_3h', datetime(2026, 7, 14, 21), True),
        ('evening_2h', datetime(2026, 7, 14, 15), False),
        ('evening_2h', datetime(2026, 7, 14, 16), True),
        ('evening_2h', datetime(2026, 7, 14, 17), False),
        ('evening_2h', datetime(2026, 7, 14, 20), True),
        ('evening_hourly', datetime(2026, 7, 14, 15), False),
        ('evening_hourly', datetime(2026, 7, 14, 16), True),
        ('night_hourly', datetime(2026, 7, 14, 19), False),
        ('night_hourly', datetime(2026, 7, 14, 20), True),
        # Weekend/summer - July every day 21+
        ('weekend_summer_night', datetime(2026, 7, 14, 21), True),  # Tue July
        ('weekend_summer_night', datetime(2026, 7, 14, 20), False),
        # November Tuesday 21 - not weekend
        ('weekend_summer_night', datetime(2026, 11, 3, 21), False),
        # November Friday 21 - weekend
        ('weekend_summer_night', datetime(2026, 11, 6, 21), True),
        # November Saturday 22 - weekend
        ('weekend_summer_night', datetime(2026, 11, 7, 22), True),
        # November Friday 20 - too early
        ('weekend_summer_night', datetime(2026, 11, 6, 20), False),
    ]
    all_ok = True
    for policy, dt, expected in test_cases:
        actual = should_scan(policy, dt)
        status = "OK" if actual == expected else "FAIL"
        if actual != expected:
            all_ok = False
        print(f"  [{status}] {policy} @ {dt}: got {actual}, want {expected}")
    print("\nAll tests passed!" if all_ok else "\nTESTS FAILED")
