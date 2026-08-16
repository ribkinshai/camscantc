"""
מערכת מעקב סריקות מצלמות - מוקד 106 טירת כרמל
"""
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
try:
    from streamlit_autorefresh import st_autorefresh
    _HAS_AUTOREFRESH = True
except ImportError:
    _HAS_AUTOREFRESH = False
import database as db
import scheduler as sch
import auth


# מרכז טירת כרמל לתצוגת מפה
TIRAT_CARMEL_CENTER = [32.7602, 34.9702]


def now_il():
    """שעה נוכחית לפי שעון ישראל"""
    return datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None)


def _get_area_coords():
    raw = db.get_setting('area_coords', '{}')
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _save_area_coords(coords_dict):
    db.set_setting('area_coords', json.dumps(coords_dict, ensure_ascii=False))


def _camera_map_position(cam, area_coords):
    if cam.get('latitude') is not None and cam.get('longitude') is not None:
        return float(cam['latitude']), float(cam['longitude'])
    area = cam.get('area', '')
    if area in area_coords:
        base = area_coords[area]
        cam_id = cam['id']
        lat_offset = ((cam_id * 7) % 30 - 15) / 100000.0
        lng_offset = ((cam_id * 13) % 30 - 15) / 100000.0
        return float(base['lat']) + lat_offset, float(base['lng']) + lng_offset
    return None


db.init_db()

st.set_page_config(
    page_title="מעקב סריקות מצלמות",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============ Session state ============
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'
if 'current_page' not in st.session_state:
    if st.session_state.get('user_role') == 'manager':
        st.session_state['current_page'] = "לוח בקרה"
    else:
        st.session_state['current_page'] = "סריקה שוטפת"

if st.session_state.get('user_role') == 'manager' and st.session_state.get('current_page') == "סריקה שוטפת":
    st.session_state['current_page'] = "לוח בקרה"

is_dark = st.session_state['theme'] == 'dark'


# ============ צבעי נושא ============
if is_dark:
    BG = '#0f1419'
    SURFACE = '#1a1f26'
    SURFACE2 = '#242b34'
    TEXT = '#e4e7eb'
    MUTED = '#94a3b8'
    BORDER = '#2d3742'
    ACCENT = '#4ade80'
    AMBER = '#fbbf24'
    RED = '#f87171'
    BTN_FG = '#0f1419'
else:
    BG = '#f8fafc'
    SURFACE = '#ffffff'
    SURFACE2 = '#f1f5f9'
    TEXT = '#0f172a'
    MUTED = '#64748b'
    BORDER = '#e2e8f0'
    ACCENT = '#16a34a'
    AMBER = '#d97706'
    RED = '#dc2626'
    BTN_FG = '#ffffff'


# ============ CSS ============
st.markdown(f"""
<style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
        background-color: {BG};
    }}
    [data-testid="stSidebar"] {{ background-color: {SURFACE}; }}

    [data-testid="stAppViewContainer"] {{
        flex-direction: row-reverse !important;
    }}
    section[data-testid="stSidebar"] {{
        left: auto !important;
        right: 0 !important;
    }}
    section[data-testid="stSidebar"][aria-expanded="false"] {{
        margin-left: 0 !important;
        margin-right: -21rem !important;
        transform: none !important;
    }}
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {{
        right: 0.5rem !important;
        left: auto !important;
    }}
    [data-testid="stHeader"] {{ background-color: transparent; }}

    .stMarkdown, p, li, span, label, h1, h2, h3, h4, h5, h6 {{
        color: {TEXT};
        direction: rtl;
        text-align: right;
    }}
    div[data-testid="stMarkdownContainer"] {{ color: {TEXT}; }}

    .stTextInput input, .stTextArea textarea, .stNumberInput input,
    .stDateInput input, .stTimeInput input {{
        background-color: {SURFACE2} !important;
        color: {TEXT} !important;
        border: 1px solid {BORDER} !important;
        text-align: right !important;
        direction: rtl !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: {SURFACE2} !important;
        color: {TEXT} !important;
        border-color: {BORDER} !important;
    }}

    .stButton button {{
        background-color: {SURFACE2};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.15s ease;
    }}
    .stButton button:hover {{
        background-color: {BORDER};
        border-color: {MUTED};
    }}
    .stButton button[kind="primary"] {{
        background-color: {ACCENT} !important;
        color: {BTN_FG} !important;
        border: 1px solid {ACCENT} !important;
    }}
    .stButton button[kind="primary"]:hover {{ filter: brightness(1.1); }}
    .stButton button[kind="tertiary"] {{
        background-color: {RED} !important;
        color: white !important;
        border: 1px solid {RED} !important;
    }}
    .stButton button[kind="tertiary"]:hover {{ filter: brightness(1.1); }}

    .stAlert {{ direction: rtl; text-align: right; border-radius: 8px; }}
    .stProgress > div > div > div {{ background-color: {ACCENT} !important; }}

    [data-testid="stMetric"] {{
        background-color: {SURFACE2};
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid {BORDER};
    }}
    [data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-size: 0.85rem !important; }}
    [data-testid="stMetricValue"] {{ color: {TEXT} !important; }}

    div[data-baseweb="tab-list"] {{
        gap: 4px;
        background-color: {SURFACE2};
        padding: 4px;
        border-radius: 8px;
        direction: rtl;
    }}
    button[data-baseweb="tab"] {{
        background-color: transparent !important;
        color: {MUTED} !important;
        border-radius: 6px !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        background-color: {SURFACE} !important;
        color: {TEXT} !important;
    }}

    [data-testid="stExpander"] {{
        background-color: {SURFACE2};
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
    [data-testid="stExpander"] summary {{ color: {TEXT}; }}

    .stDataFrame, .stDataFrame table {{ direction: rtl; }}

    .top-bar {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 12px;
        background-color: {SURFACE2};
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
        border: 1px solid {BORDER};
    }}
    .top-item .label {{ font-size: 0.75rem; color: {MUTED}; margin-bottom: 4px; }}
    .top-item .value {{ font-size: 1.15rem; font-weight: 500; color: {TEXT}; }}

    .status-dot {{
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        margin-left: 8px;
        vertical-align: middle;
    }}
    .status-dot.pending {{ background: {MUTED}; }}
    .status-dot.ok {{ background: {ACCENT}; }}
    .status-dot.issue {{ background: {RED}; }}

    .camera-name {{ font-size: 0.95rem; font-weight: 500; color: {TEXT}; }}
    .camera-meta {{ font-size: 0.8rem; color: {MUTED}; margin-top: 2px; }}
    .event-note {{ font-size: 0.8rem; color: {AMBER}; font-style: italic; margin-top: 3px; }}
</style>
""", unsafe_allow_html=True)

auth.require_login((TEXT, MUTED, BG, SURFACE))

# ============ אוטו-רענון גלובלי ============
# חייב להיקרא ברמת הטופ בכל rerun עם אותו key - אחרת נכשל
if _HAS_AUTOREFRESH:
    # ברירת מחדל: כבוי (פעם בשעה)
    _refresh_interval_ms = 60 * 60 * 1000

    _in_form = (
        st.session_state.get('issue_cam_id')
        or st.session_state.get('editing_scanner')
        or not st.session_state.get('scanner_name')
    )

    _on_scan_page = (
        st.session_state.get('current_page') == 'סריקה שוטפת'
        and st.session_state.get('user_role') != 'manager'
    )

    if _on_scan_page and not _in_form:
        _refresh_interval_ms = 15 * 1000  # 15 שניות

    _refresh_count = st_autorefresh(
        interval=_refresh_interval_ms,
        limit=None,
        key="global_page_refresh",
    )
else:
    _refresh_count = 0
# ============ Sidebar ============
def _nav_button(name, label):
    is_current = st.session_state['current_page'] == name
    if st.button(
        label,
        use_container_width=True,
        type="primary" if is_current else "secondary",
        key=f"nav_{name}",
    ):
        st.session_state['current_page'] = name
        st.session_state.pop('issue_cam_id', None)
        st.session_state.pop('issue_cam_name', None)
        st.rerun()


with st.sidebar:
    st.markdown("### מוקד רואה")

    c1, c2 = st.columns(2)
    if c1.button("🌙 כהה", use_container_width=True,
                 type="primary" if is_dark else "secondary"):
        st.session_state['theme'] = 'dark'
        st.rerun()
    if c2.button("☀️ בהיר", use_container_width=True,
                 type="primary" if not is_dark else "secondary"):
        st.session_state['theme'] = 'light'
        st.rerun()

    st.markdown("---")

    _user_role = st.session_state.get('user_role', 'operator')

    if _user_role == 'manager':
        _nav_button("לוח בקרה", "📊 לוח בקרה")
        _nav_button("לוז סריקות", "📅 לו״ז סריקות")
        _nav_button("נקודות חמות", "🔥 נקודות חמות")
        _nav_button("אתרי בנייה", "🏗️ אתרי בנייה")

        with st.expander("⚙️ ניהול מערכת", expanded=False):
            _nav_button("תקלות", "⚠️ תקלות")
            _nav_button("מפה", "🗺️ מפה")
            _nav_button("מצלמות", "🎥 מצלמות")
            _nav_button("היסטוריה", "📈 היסטוריה")
            _nav_button("הגדרות", "⚙️ הגדרות")
    else:
        _nav_button("סריקה שוטפת", "✅ סריקה שוטפת")
        _nav_button("נקודות חמות", "🔥 נקודות חמות")
        _nav_button("אתרי בנייה", "🏗️ אתרי בנייה")
        _nav_button("תקלות", "⚠️ תקלות")
        _nav_button("מפה", "🗺️ מפה")

    _now_temp = now_il()
    st.markdown(
        f'<div style="margin-top: 20px; padding-top: 12px; border-top: 1px solid {BORDER};"></div>',
        unsafe_allow_html=True,
    )
    components.html(f"""
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Assistant', sans-serif;
        }}
    </style>
    <div style="font-size: 0.85rem; color: {MUTED}; line-height: 1.7; direction: rtl; text-align: right;">
        <div>
            <b style="color:{TEXT};">🕐 <span id="clk-time">--:--:--</span></b>
            · <span id="clk-date">--/--/----</span>
        </div>
        <div>משמרת: <b style="color:{TEXT};">{sch.get_shift_name(_now_temp)}</b></div>
    </div>
    <script>
    (function() {{
        function updateClock() {{
            var now = new Date();
            var timeStr = now.toLocaleTimeString('en-GB', {{
                timeZone: 'Asia/Jerusalem', hour12: false,
                hour: '2-digit', minute: '2-digit', second: '2-digit'
            }});
            var dateStr = now.toLocaleDateString('en-GB', {{ timeZone: 'Asia/Jerusalem' }});
            var t = document.getElementById('clk-time');
            var d = document.getElementById('clk-date');
            if (t) t.textContent = timeStr;
            if (d) d.textContent = dateStr;
        }}
        updateClock();
        setInterval(updateClock, 1000);
    }})();
    </script>
    """, height=60)

user_info = auth.current_user()
if user_info:
    role_label = 'מנהלת' if user_info['role'] == 'manager' else 'מוקדן'
    st.sidebar.markdown(f"""
    <div style="background-color: {SURFACE2}; border: 1px solid {BORDER};
                border-radius: 6px; padding: 8px 12px; margin-top: 8px; font-size: 0.85rem;">
        <div style="color: {MUTED}; font-size: 0.75rem;">מחובר כ:</div>
        <div style="color: {TEXT}; font-weight: 500;">👤 {user_info['name']}</div>
        <div style="color: {MUTED}; font-size: 0.75rem;">{role_label}</div>
    </div>
    """, unsafe_allow_html=True)

if st.sidebar.button("🔒 יציאה מהמערכת", use_container_width=True, key="logout_btn"):
    auth.logout()
    st.rerun()
def render_current_plan_banner():
    """
    מציג בנר עם התוכנית הפעילה לשעה הנוכחית + כפתורי סימון אינטראקטיביים.
    בזמן אמת - מסתנכרן עם השעה בפועל.
    """
    _now_for_plan = now_il()
    active_plans = db.get_active_scan_plans_for_datetime(_now_for_plan)

    if not active_plans:
        return

    all_cams_for_plan = db.get_all_cameras()
    cam_map = {c['id']: c for c in all_cams_for_plan}
    faulty_ids_plan = db.get_faulty_camera_ids()

    current_hour_local = _now_for_plan.replace(minute=0, second=0, microsecond=0)
    current_hour_key_local = sch.hour_key(current_hour_local)
    scanned_now_plan = db.get_scans_for_hour(current_hour_key_local)
    scanner_name_local = st.session_state.get('scanner_name', '') or st.session_state.get('user_name', '')

    is_dark_local = st.session_state.get('theme', 'light') == 'dark'

    for plan in active_plans:
        priority = plan.get('priority', 'medium')
        priority_colors = {'high': '#dc2626', 'medium': '#d97706', 'low': '#16a34a'}
        priority_icons = {'high': '🔴', 'medium': '🟠', 'low': '🟢'}
        border_color = priority_colors.get(priority, '#d97706')
        icon = priority_icons.get(priority, '📋')

        banner_bg = '#1e293b' if is_dark_local else '#f0f9ff'
        text_color = '#e2e8f0' if is_dark_local else '#0c4a6e'

        cams_in_plan = [cam_map[cid] for cid in plan.get('camera_ids', [])
                        if cid in cam_map and cid not in faulty_ids_plan]
        scanned_count = sum(1 for c in cams_in_plan if c['id'] in scanned_now_plan)
        total_count = len(cams_in_plan)
        progress_pct = int(scanned_count / total_count * 100) if total_count > 0 else 0

        # ---- הבנר עצמו ----
        st.markdown(f"""
        <div style="background-color: {banner_bg}; border: 2px solid {border_color};
                    border-radius: 10px; padding: 14px 18px; margin-bottom: 4px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <span style="font-size: 1.5rem;">{icon}📅</span>
                <div style="flex: 1;">
                    <div style="font-weight: 700; font-size: 1.15rem; color: {text_color};">
                        תוכנית פעילה: {plan['name']}
                    </div>
                    <div style="font-size: 0.85rem; color: {text_color}; opacity: 0.85; margin-top: 3px;">
                        ⏰ {plan.get('start_time', '')} - {plan.get('end_time', '')}  ·
                        📊 בוצעו {scanned_count} מתוך {total_count} ({progress_pct}%)
                    </div>
                </div>
            </div>
            {f'<div style="font-size: 0.9rem; color: {text_color}; margin-top: 6px; padding-top: 6px; border-top: 1px solid {border_color}44;"><b>📝 דגשים:</b> {plan.get("description")}</div>' if plan.get('description') else ''}
        </div>
        """, unsafe_allow_html=True)

        # ---- רשימת מצלמות עם כפתורי סימון ----
        if cams_in_plan:
            with st.expander(
                f"🎥 סמן סריקות של '{plan['name']}' ({scanned_count}/{total_count} בוצעו)",
                expanded=True,
            ):
                for cam in cams_in_plan:
                    is_scanned = cam['id'] in scanned_now_plan
                    if is_scanned:
                        # שורה נעולה - כבר סומן
                        info = scanned_now_plan[cam['id']]
                        status = info.get('status') or 'ok'
                        time_str = info['scanned_at'][11:19] if info['scanned_at'] else ''
                        by = info['scanned_by'] or ''
                        if status == 'issue':
                            badge_bg = RED
                            badge_label = 'לא נסרק'
                            dot_class = 'issue'
                        else:
                            badge_bg = ACCENT
                            badge_label = 'נסרק'
                            dot_class = 'ok'

                        st.markdown(f"""
                            <div style="padding: 8px 12px; margin-bottom: 6px;
                                        background-color: {SURFACE2}; border-right: 3px solid {badge_bg};
                                        border-radius: 6px;">
                                <div style="display: flex; align-items: center; gap: 10px; justify-content: space-between;">
                                    <div style="flex: 1;">
                                        <span class="status-dot {dot_class}"></span>
                                        <span class="camera-name">{cam['name']}</span>
                                        <div style="font-size: 0.72rem; color: {MUTED}; margin-top: 3px;">
                                            🔒 ע"י {by} · 🗂️ {cam.get('area', '') or '-'}
                                        </div>
                                    </div>
                                    <div style="background-color: {badge_bg}; color: white;
                                                padding: 4px 12px; border-radius: 6px;
                                                font-weight: 500; font-size: 0.85rem;
                                                font-family: 'Courier New', monospace;">
                                        🕐 {time_str} · {badge_label}
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        # שורה פעילה - יש כפתורים
                        cols = st.columns([4, 1, 1])
                        cols[0].markdown(f"""
                            <div style="padding: 4px 0;">
                                <span class="status-dot pending"></span>
                                <span class="camera-name">{cam['name']}</span>
                                <div style="font-size: 0.72rem; color: {MUTED}; margin-top: 3px;">
                                    🗂️ {cam.get('area', '') or '-'}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        if cols[1].button(
                            "✅ נסרק",
                            key=f"plan_ok_{plan['id']}_{cam['id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            db.mark_scan(cam['id'], current_hour_key_local, scanner_name_local, status='ok')
                            st.rerun()
                        if cols[2].button(
                            "❌ לא נסרק",
                            key=f"plan_iss_{plan['id']}_{cam['id']}",
                            type="tertiary",
                            use_container_width=True,
                        ):
                            st.session_state['issue_cam_id'] = cam['id']
                            st.session_state['issue_cam_name'] = cam['name']
                            st.rerun()

        st.markdown("")  # רווח בין תוכניות

        if cams_in_plan:
            with st.expander(f"📋 רשימת המצלמות בתוכנית ({len(cams_in_plan)})", expanded=False):
                for cam in cams_in_plan:
                    area = cam.get('area', '') or '-'
                    st.markdown(f"- **{cam['name']}**  ·  🗂️ {area}")
def render_missed_scans_banner():
    """
    מציג בנר בולט עם מספר הסריקות שהוחמצו + כפתור איפוס.
    - מנהלת: איפוס גלובלי (למנהלת + לכל המוקדנים)
    - מוקדן: איפוס מקומי בלבד (רק בסשן שלו, מנהלת ממשיכה לראות)
    """
    _now_for_check = now_il()
    is_mgr = st.session_state.get('user_role') == 'manager'

    # ---- חישוב סף האיפוס הרלוונטי למשתמש הנוכחי ----
    global_dismiss = db.get_setting('banner_dismissed_until', None)
    local_dismiss = st.session_state.get('banner_dismissed_until_local', None)

    if is_mgr:
        # מנהלת - רק איפוס גלובלי משפיע עליה
        effective_cutoff = global_dismiss
    else:
        # מוקדן - האיפוס המאוחר מבין השניים (גלובלי או מקומי)
        if global_dismiss and local_dismiss:
            effective_cutoff = max(global_dismiss, local_dismiss)
        else:
            effective_cutoff = global_dismiss or local_dismiss

    # ---- קבלת סריקות שהוחמצו + סינון ----
    missed = sch.get_missed_scans(_now_for_check, lookback_hours=8)

    if effective_cutoff:
        # השאר רק סריקות מהוחמצו אחרי סף האיפוס
        missed = [(hk, cam) for hk, cam in missed if hk > effective_cutoff]

    if not missed:
        return  # אין החמצות פעילות - אין מה להציג

    # ---- קיבוץ לפי שעה ----
    by_hour = {}
    for hour_key_val, cam in missed:
        if hour_key_val not in by_hour:
            by_hour[hour_key_val] = []
        by_hour[hour_key_val].append(cam)

    total_missed = len(missed)
    unique_cams = len(set(c['id'] for _, c in missed))
    is_dark_local = st.session_state.get('theme', 'light') == 'dark'
    banner_bg = '#7f1d1d' if is_dark_local else '#fee2e2'
    banner_border = '#dc2626'
    banner_text = '#fef2f2' if is_dark_local else '#7f1d1d'

    st.markdown(f"""
    <style>
        @keyframes pulse-alert {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.6); }}
            50% {{ box-shadow: 0 0 0 12px rgba(220, 38, 38, 0); }}
        }}
        .missed-banner {{
            animation: pulse-alert 2s infinite;
        }}
    </style>
    <div class="missed-banner" style="background-color: {banner_bg};
                border: 2px solid {banner_border};
                border-radius: 10px; padding: 16px 20px; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 2rem;">🚨</span>
            <div style="flex: 1;">
                <div style="font-weight: 700; font-size: 1.15rem; color: {banner_text};">
                    התראה: {total_missed} סריקות לא בוצעו בזמן!
                </div>
                <div style="font-size: 0.9rem; color: {banner_text}; margin-top: 4px;">
                    {unique_cams} מצלמות שונות · פורש ב-{len(by_hour)} שעות
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- כפתור איפוס - שונה לפי תפקיד ----
    bc1, bc2, bc3 = st.columns([2, 2, 1])
    with bc3:
        current_ts = _now_for_check.strftime("%Y-%m-%d %H:%M:%S")
        if is_mgr:
            if st.button(
                "✅ טופל · נקה לכולם",
                key="dismiss_missed_global",
                use_container_width=True,
                type="primary",
                help="מנקה את הבנר גם למוקדנים",
            ):
                db.set_setting('banner_dismissed_until', current_ts)
                st.success("הבנר נוקה לכל המשתמשים")
                st.rerun()
        else:
            if st.button(
                "🔕 נקה אצלי",
                key="dismiss_missed_local",
                use_container_width=True,
                help="מנקה רק אצלך - מנהלת עדיין תראה את ההתראה",
            ):
                st.session_state['banner_dismissed_until_local'] = current_ts
                st.rerun()

    with st.expander(f"📋 פירוט כל {total_missed} הסריקות שהוחמצו", expanded=False):
        for hour_key_val in sorted(by_hour.keys(), reverse=True):
            cams_in_hour = by_hour[hour_key_val]
            st.markdown(f"**🕐 {hour_key_val}** · {len(cams_in_hour)} מצלמות")
            for cam in cams_in_hour:
                area = cam.get('area', '') or '-'
                st.markdown(f"- {cam['name']}  ·  🗂️ {area}")
            st.markdown("")
page = st.session_state['current_page']
now = now_il()
current_hour = now.replace(minute=0, second=0, microsecond=0)
current_hour_key = sch.hour_key(current_hour)


# ============ עמוד: סריקה שוטפת ============
if page == "סריקה שוטפת":

    # ============ הגנה: מסך זה למוקדנים בלבד ============
    if st.session_state.get('user_role') == 'manager':
        st.warning("⚠️ מסך זה מיועד למוקדנים בלבד. מנהלת עוקבת דרך לוח הבקרה.")
        st.info("💡 עבור ל-**📊 לוח בקרה** בסרגל הצד לצפייה בסטטוס הסריקות של המשמרת.")
        st.stop()

    # ---- כרטיס נציג פעיל ----
    if not st.session_state.get('scanner_name'):
        st.session_state['scanner_name'] = st.session_state.get('user_name', '')
    scanner_name = st.session_state.get('scanner_name', '')
    edit_mode = st.session_state.get('editing_scanner', False)

    if not scanner_name or edit_mode:
        st.markdown(f"""
            <div style="background-color: {AMBER}22; border-right: 3px solid {AMBER};
                        border-radius: 8px; padding: 14px 18px; margin-bottom: 14px;">
                <div style="font-weight: 500; color: {TEXT}; font-size: 1.05rem;">
                    👤 הזן שם נציג למשמרת הנוכחית
                </div>
                <div style="font-size: 0.85rem; color: {MUTED}; margin-top: 4px;">
                    כל הסריקות והתקלות יירשמו על שם זה
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.form("scanner_form"):
            fc1, fc2 = st.columns([3, 1])
            new_name = fc1.text_input(
                "שם הנציג", value=scanner_name,
                placeholder="שם מלא", label_visibility="collapsed",
            )
            if fc2.form_submit_button("💾 שמור", type="primary", use_container_width=True):
                if new_name.strip():
                    st.session_state['scanner_name'] = new_name.strip()
                    st.session_state.pop('editing_scanner', None)
                    st.rerun()
                else:
                    st.error("יש להזין שם")

        if scanner_name and edit_mode:
            if st.button("↩️ ביטול", key="cancel_edit_scanner"):
                st.session_state.pop('editing_scanner', None)
                st.rerun()

        st.stop()
    else:
        nc1, nc2 = st.columns([5, 1])
        nc1.markdown(f"""
            <div style="background-color: {SURFACE2}; border: 1px solid {BORDER};
                        border-right: 3px solid {ACCENT};
                        border-radius: 8px; padding: 12px 18px;
                        display: flex; align-items: center; gap: 14px; margin-bottom: 12px;">
                <span style="font-size: 1.6rem;">👤</span>
                <div>
                    <div style="font-size: 0.75rem; color: {MUTED};">נציג פעיל במשמרת</div>
                    <div style="font-size: 1.15rem; font-weight: 500; color: {TEXT};">{scanner_name}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        if nc2.button("🔄 החלף נציג", use_container_width=True):
            st.session_state['editing_scanner'] = True
            st.rerun()

    # ---- חלונית "מדוע לא נסרק?" ----
    if st.session_state.get('issue_cam_id'):
        cam_id = st.session_state['issue_cam_id']
        cam_name = st.session_state.get('issue_cam_name', '')

        c1, c2, c3 = st.columns([1, 3, 1])
        with c2:
            st.markdown("### ❌ מדוע לא נסרק?")
            st.caption(f"מצלמה: **{cam_name}** · שעה: {current_hour_key}")

            with st.form(f"not_scanned_form_{cam_id}", clear_on_submit=False):
                st.markdown("**🏷️ סוג האירוע:**")
                category_options = {
                    '🛡️ בטחון (אלימות, ונדליזם, פעילות חשודה)': 'security',
                    '🗑️ גזם וגרוטאות (השלכות, פסולת, ניקיון)': 'dumping',
                    '❓ אחר': 'other',
                }
                selected_cat_label = st.radio(
                    "בחר סוג",
                    list(category_options.keys()),
                    label_visibility="collapsed",
                    key=f"cat_radio_{cam_id}",
                )
                selected_category = category_options[selected_cat_label]

                st.markdown("**📝 פירוט:**")
                reason = st.text_area(
                    "סיבה", height=100,
                    placeholder="הקלד כאן את הסיבה/פירוט האירוע...",
                    label_visibility="collapsed",
                )
                bc1, bc2 = st.columns(2)
                save = bc1.form_submit_button("💾 שמור", type="primary", use_container_width=True)
                cancel = bc2.form_submit_button("↩️ ביטול", use_container_width=True)

                if save:
                    if not reason.strip():
                        st.error("יש למלא פירוט")
                    else:
                        db.mark_scan(
                            cam_id, current_hour_key,
                            st.session_state.get('scanner_name', ''),
                            status='issue',
                            event_details=reason.strip(),
                            event_category=selected_category,
                        )
                        st.session_state.pop('issue_cam_id', None)
                        st.session_state.pop('issue_cam_name', None)
                        st.rerun()
                if cancel:
                    st.session_state.pop('issue_cam_id', None)
                    st.session_state.pop('issue_cam_name', None)
                    st.rerun()

        st.stop()
def _get_night_shift_id(dt):
    """
    מחזיר מזהה מספרי ללילה הנוכחי, או None אם לא בשעות לילה.
    לילה = 23:00 של יום מסוים עד 06:59 של היום שאחריו.
    """
    hour = dt.hour
    if hour >= 23:
        night_date = dt.date()
    elif hour < 7:
        night_date = (dt - timedelta(days=1)).date()
    else:
        return None
    return int(night_date.strftime("%Y%m%d"))


def _ensure_night_comm_slots(shift_id, dt):
    """יוצר את 15 סלוטי בדיקת הקשר ללילה הנוכחי (23:30 עד 06:30) אם עוד לא קיימים."""
    if not shift_id:
        return
    if dt.hour >= 23:
        night_start = dt.date()
    else:
        night_start = (dt - timedelta(days=1)).date()

    base = datetime.combine(night_start, time(23, 30))
    for i in range(15):  # 15 סלוטים: 23:30, 00:00, ..., 06:30
        slot_dt = base + timedelta(minutes=30 * i)
        slot_str = slot_dt.strftime("%Y-%m-%d %H:%M")
        db.create_comm_check_slot(shift_id, slot_str)


def render_night_comm_check_widget():
    """
    רכיב בדיקת קשר עם פיקוח - מוצג רק בשעות לילה למוקדנים.
    ממוקם בראש העמוד לגישה מהירה בלי גלילה.
    """
    if st.session_state.get('user_role') != 'operator':
        return

    _now = now_il()
    night_shift_id = _get_night_shift_id(_now)
    if night_shift_id is None:
        return

    _ensure_night_comm_slots(night_shift_id, _now)
    slots = db.get_shift_comm_checks(night_shift_id)
    if not slots:
        return

    now_str = _now.strftime("%Y-%m-%d %H:%M")
    overdue_slots = [s for s in slots if s['scheduled_time'] <= now_str and not s.get('actual_time')]
    upcoming_slots = [s for s in slots if s['scheduled_time'] > now_str]
    completed = sum(1 for s in slots if s.get('actual_time'))
    total = len(slots)

    is_dark_widget = st.session_state.get('theme', 'light') == 'dark'

    # ---- מצב 1: יש בדיקה בפיגור ----
    if overdue_slots:
        current_slot = overdue_slots[0]
        try:
            slot_dt = datetime.strptime(current_slot['scheduled_time'], "%Y-%m-%d %H:%M")
            mins_late = int((_now - slot_dt).total_seconds() / 60)
        except (ValueError, TypeError):
            mins_late = 0

        is_urgent = mins_late > 30

        if is_urgent:
            bg_color = '#7f1d1d' if is_dark_widget else '#fee2e2'
            text_color = '#fecaca' if is_dark_widget else '#7f1d1d'
            border_color = '#dc2626'
            icon = '🚨'
            title_text = f"בדיקת קשר בפיגור חמור! - {mins_late} דקות באיחור"
        else:
            bg_color = '#78350f' if is_dark_widget else '#fef3c7'
            text_color = '#fef3c7' if is_dark_widget else '#78350f'
            border_color = '#d97706'
            icon = '⏰'
            title_text = f"בדיקת קשר ממתינה - {mins_late} דק' מהזמן"

        pulse_style = 'animation: pulse-alert 1.5s infinite;' if is_urgent else ''

        st.markdown(f"""
            <style>
                @keyframes pulse-alert {{
                    0%, 100% {{ box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.6); }}
                    50% {{ box-shadow: 0 0 0 12px rgba(220, 38, 38, 0); }}
                }}
            </style>
            <div style="background-color: {bg_color}; border: 2px solid {border_color};
                        border-radius: 10px; padding: 12px 18px; margin-bottom: 8px; {pulse_style}">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.8rem;">{icon}</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 700; font-size: 1.1rem; color: {text_color};">
                            {title_text}
                        </div>
                        <div style="font-size: 0.9rem; color: {text_color}; opacity: 0.9; margin-top: 3px;">
                            🕐 נדרש בשעה {current_slot['scheduled_time'][11:]} · ✅ בוצעו {completed}/{total} בדיקות
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        bc1, bc2 = st.columns([4, 1])
        if bc1.button(
            f"✅ בצע בדיקת קשר של {current_slot['scheduled_time'][11:]} עכשיו",
            key=f"cc_done_overdue_{current_slot['id']}",
            type="primary",
            use_container_width=True,
        ):
            db.mark_comm_check(night_shift_id, current_slot['scheduled_time'])
            st.rerun()

    # ---- מצב 2: יש בדיקה עתידית ----
    elif upcoming_slots:
        next_slot = upcoming_slots[0]
        try:
            slot_dt = datetime.strptime(next_slot['scheduled_time'], "%Y-%m-%d %H:%M")
            mins_until = int((slot_dt - _now).total_seconds() / 60)
        except (ValueError, TypeError):
            mins_until = 0

        bg_color = '#1e3a5f' if is_dark_widget else '#dbeafe'
        text_color = '#dbeafe' if is_dark_widget else '#1e3a5f'
        border_color = '#3b82f6'

        st.markdown(f"""
            <div style="background-color: {bg_color}; border: 1px solid {border_color};
                        border-radius: 10px; padding: 12px 18px; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.6rem;">🌙</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 700; font-size: 1.05rem; color: {text_color};">
                            בדיקת קשר עם פיקוח · הבאה: {next_slot['scheduled_time'][11:]}
                        </div>
                        <div style="font-size: 0.85rem; color: {text_color}; opacity: 0.85; margin-top: 3px;">
                            ⏱️ בעוד {mins_until} דקות · ✅ בוצעו {completed}/{total}
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ---- מצב 3: כל הבדיקות בוצעו ----
    else:
        bg_color = '#14532d' if is_dark_widget else '#dcfce7'
        text_color = '#bbf7d0' if is_dark_widget else '#14532d'
        border_color = '#16a34a'

        st.markdown(f"""
            <div style="background-color: {bg_color}; border: 1px solid {border_color};
                        border-radius: 10px; padding: 12px 18px; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.6rem;">✅</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 700; font-size: 1.05rem; color: {text_color};">
                            כל בדיקות הקשר של הלילה בוצעו! ({completed}/{total})
                        </div>
                        <div style="font-size: 0.85rem; color: {text_color}; opacity: 0.85; margin-top: 3px;">
                            עבודה נהדרת · המשמרת עמדה בכל הבדיקות
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ---- היסטוריה מתקפלת ----
    with st.expander(f"📋 היסטוריית בדיקות הלילה ({completed}/{total})", expanded=False):
        rows = []
        for s in slots:
            actual = s.get('actual_time', '') or ''
            if actual:
                status_txt = f"✅ בוצע בשעה {actual[11:19]}"
            elif s['scheduled_time'] < now_str:
                status_txt = "❌ הוחמצה"
            else:
                status_txt = "⏰ ממתינה"
            rows.append({
                'שעה מתוזמנת': s['scheduled_time'][11:],
                'סטטוס': status_txt,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    # ---- רכיב בדיקת קשר לילה (מוצג רק בשעות 23:00-06:59) ----
    render_night_comm_check_widget()

    # ---- בנר תוכנית פעילה מהלו״ז ----
    render_current_plan_banner()

    # ---- בנר התראה: סריקות שהוחמצו ----
    render_missed_scans_banner()

    # ---- תצוגה רגילה ----
    central, rotating = sch.get_cameras_for_hour(current_hour, include_faulty=False)
    # ---- תצוגה רגילה ----
    central, rotating = sch.get_cameras_for_hour(current_hour, include_faulty=False)
    scanned_now = db.get_scans_for_hour(current_hour_key)
    total = len(central) + len(rotating)
    completed = sum(1 for c in central + rotating if c['id'] in scanned_now)
    ok_count = sum(1 for c in central + rotating
                   if c['id'] in scanned_now and (scanned_now[c['id']].get('status') or 'ok') == 'ok')
    issue_count = sum(1 for c in central + rotating
                      if c['id'] in scanned_now and scanned_now[c['id']].get('status') == 'issue')

    st.markdown(f"""
    <div class="top-bar">
        <div class="top-item">
            <div class="label">שעה נוכחית</div>
            <div class="value">{current_hour.strftime('%H:00')} · {sch.get_shift_name(now)}</div>
        </div>
        <div class="top-item">
            <div class="label">סטטוס סריקה</div>
            <div class="value">{completed} / {total}</div>
        </div>
        <div class="top-item">
            <div class="label">נסרק / לא נסרק</div>
            <div class="value">
                <span style="color:{ACCENT};">{ok_count}</span>
                <span style="color:{MUTED};"> / </span>
                <span style="color:{RED};">{issue_count}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if total > 0:
        st.progress(completed / total)
    else:
        st.info("אין מצלמות מוגדרות. עבור ל'ניהול → מצלמות' להוסיף.")
        st.stop()

    fc1, fc2 = st.columns([2, 1])
    search = fc1.text_input("🔍 חיפוש מצלמה", "", placeholder="הקלד שם, מספר או חלק ממנו...")
    all_areas_for_hour = sorted(set(c.get('area', '') for c in central + rotating if c.get('area')))
    if all_areas_for_hour:
        selected_area = fc2.selectbox("🗂️ אזור", ["כל האזורים"] + all_areas_for_hour)
    else:
        selected_area = "כל האזורים"

    filtered_central = central
    filtered_rotating = rotating
    if search.strip():
        s = search.strip().lower()
        filtered_central = [c for c in filtered_central if s in c['name'].lower()]
        filtered_rotating = [c for c in filtered_rotating if s in c['name'].lower()]
    if selected_area != "כל האזורים":
        filtered_central = [c for c in filtered_central if c.get('area') == selected_area]
        filtered_rotating = [c for c in filtered_rotating if c.get('area') == selected_area]
    if search.strip() or selected_area != "כל האזורים":
        st.caption(f"נמצאו {len(filtered_central) + len(filtered_rotating)} מצלמות")

    def render_row(cam, prefix):
        is_scanned = cam['id'] in scanned_now
        if is_scanned:
            info = scanned_now[cam['id']]
            status = info.get('status') or 'ok'
            by = info['scanned_by'] or ''
            time_str = info['scanned_at'][11:19] if info['scanned_at'] else ''
            date_str = info['scanned_at'][:10] if info['scanned_at'] else ''
            if status == 'issue':
                dot_class = 'issue'
                badge_bg = RED
                badge_label = 'לא נסרק'
            else:
                dot_class = 'ok'
                badge_bg = ACCENT
                badge_label = 'נסרק'

            meta_parts = []
            if by:
                meta_parts.append(f"ע\"י {by}")
            meta_parts.append(f"📅 {date_str}")
            meta_text = ' · '.join(meta_parts)

            st.markdown(f"""
                <div style="padding: 8px 12px; margin-bottom: 6px;
                            background-color: {SURFACE2}; border-right: 3px solid {badge_bg};
                            border-radius: 6px;">
                    <div style="display: flex; align-items: center; gap: 10px; justify-content: space-between;">
                        <div style="flex: 1;">
                            <span class="status-dot {dot_class}"></span>
                            <span class="camera-name">{cam['name']}</span>
                        </div>
                        <div style="background-color: {badge_bg}; color: white;
                                    padding: 4px 12px; border-radius: 6px;
                                    font-weight: 500; font-size: 0.9rem;
                                    font-family: 'Courier New', monospace;">
                            🕐 {time_str} · {badge_label}
                        </div>
                    </div>
                    <div class="camera-meta" style="margin-top: 4px; font-size: 0.75rem;">
                        🔒 {meta_text}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            cols = st.columns([4, 1, 1])
            cols[0].markdown(f"""
                <div style="padding: 4px 0;">
                    <span class="status-dot pending"></span>
                    <span class="camera-name">{cam['name']}</span>
                </div>
            """, unsafe_allow_html=True)
            if cols[1].button("✅ נסרק", key=f"ok_{prefix}_{cam['id']}", type="primary", use_container_width=True):
                db.mark_scan(cam['id'], current_hour_key, scanner_name, status='ok')
                st.rerun()
            if cols[2].button("❌ לא נסרק", key=f"iss_{prefix}_{cam['id']}", type="tertiary", use_container_width=True):
                st.session_state['issue_cam_id'] = cam['id']
                st.session_state['issue_cam_name'] = cam['name']
                st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**🎯 חובה בשעה זו** · {len(filtered_central)}")
        st.caption("מצלמות עם מדיניות סריקה שתואמת לשעה הנוכחית")
        if not filtered_central and search.strip():
            st.caption("אין תוצאות")
        for cam in filtered_central:
            render_row(cam, "c")
    with col2:
        st.markdown(f"**🔄 בסבב** · {len(filtered_rotating)}")
        if not filtered_rotating and search.strip():
            st.caption("אין תוצאות")
        for cam in filtered_rotating:
            render_row(cam, "r")


st.caption("אין תוצאות")
        for cam in filtered_rotating:
            render_row(cam, "r")


# ============ עמוד: לוח בקרה ============
elif page == "לוח בקרה":
    _is_manager = st.session_state.get('user_role') == 'manager'
    if _is_manager:
        st.header("📊 דשבורד מנהלת · מוקד 106")
        st.caption(f"תמונת מצב חיה של פעילות המוקד · מחוברת: {st.session_state.get('user_name', '')}")
    else:
        st.header("לוח בקרה")

    # ---- בנר התראה: סריקות שהוחמצו ----
    render_missed_scans_banner()

    fc1, fc2, fc3 = st.columns([2, 2, 1])
    fc1, fc2, fc3 = st.columns([2, 2, 1])

    period_options = {
        "היום": (now.date(), now.date()),
        "אתמול": (now.date() - timedelta(days=1), now.date() - timedelta(days=1)),
        "7 ימים אחרונים": (now.date() - timedelta(days=6), now.date()),
        "30 ימים אחרונים": (now.date() - timedelta(days=29), now.date()),
        "טווח מותאם": None,
    }
    selected_period = fc1.selectbox("📅 טווח", list(period_options.keys()), key="dashboard_period")

    if selected_period == "טווח מותאם":
        rc1, rc2 = st.columns(2)
        start_date = rc1.date_input("מתאריך", value=now.date() - timedelta(days=6), key="dash_start")
        end_date = rc2.date_input("עד תאריך", value=now.date(), key="dash_end")
    else:
        start_date, end_date = period_options[selected_period]

    all_cams_for_filter = db.get_all_cameras()
    all_areas_for_filter = sorted(set(c.get('area', '') for c in all_cams_for_filter if c.get('area')))
    selected_area_filter = fc2.selectbox("🗂️ אזור", ["כל האזורים"] + all_areas_for_filter, key="dash_area")

    start_key_range = f"{start_date} 00:00"
    end_key_range = f"{end_date} 23:59"

    all_scans = db.get_scans_in_range(start_key_range, end_key_range)
    all_issues_scans = [s for s in all_scans if s.get('status') == 'issue']
    all_ok_scans = [s for s in all_scans if s.get('status') != 'issue']

    all_faults_list = db.get_all_faults()
    active_faults_list = db.get_active_faults()

    all_cameras_list = db.get_all_cameras()
    total_cams = len(all_cameras_list)
    faulty_ids = db.get_faulty_camera_ids()

    if selected_area_filter != "כל האזורים":
        area_cam_ids = {c['id'] for c in all_cameras_list if c.get('area') == selected_area_filter}
        all_scans = [s for s in all_scans if s.get('camera_id') in area_cam_ids]
        all_issues_scans = [s for s in all_issues_scans if s.get('camera_id') in area_cam_ids]
        all_ok_scans = [s for s in all_ok_scans if s.get('camera_id') in area_cam_ids]

    st.markdown("### 📈 מדדי ביצוע")

    m1, m2, m3, m4 = st.columns(4)
    total_scans = len(all_scans)
    ok_count = len(all_ok_scans)
    issue_count = len(all_issues_scans)
    compliance_pct = round((ok_count / total_scans * 100), 1) if total_scans > 0 else 0

    m1.metric("סה\"כ סריקות", total_scans)
    m2.metric("נסרקו תקין", ok_count)
    m3.metric("נסרקו לא תקין", issue_count)
    m4.metric("עמידה בתוכנית", f"{compliance_pct}%")

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("מצלמות פעילות", total_cams)
    m6.metric("מצלמות תקולות", len(faulty_ids))
    m7.metric("תקלות פעילות", len(active_faults_list))
    m8.metric("סה\"כ תקלות היסטוריות", len(all_faults_list))

    st.markdown("---")

    if all_scans:
        df_scans = pd.DataFrame(all_scans)
        df_scans['datetime'] = pd.to_datetime(df_scans['scheduled_hour'], errors='coerce')
        df_scans['hour'] = df_scans['datetime'].dt.hour
        df_scans['date'] = df_scans['datetime'].dt.date
        df_scans['status_label'] = df_scans['status'].apply(
            lambda s: '⚠️ לא נסרק' if s == 'issue' else '✅ נסרק'
        )

        gc1, gc2 = st.columns(2)

        with gc1:
            st.markdown("#### 📊 סריקות לפי שעה")
            hourly = df_scans.groupby(['hour', 'status_label']).size().reset_index(name='count')
            if len(hourly) > 0:
                fig = px.bar(
                    hourly, x='hour', y='count', color='status_label',
                    labels={'hour': 'שעה', 'count': 'מספר סריקות', 'status_label': 'סטטוס'},
                    color_discrete_map={'⚠️ לא נסרק': RED, '✅ נסרק': ACCENT},
                    height=320,
                )
                fig.update_layout(
                    xaxis=dict(tickmode='linear', dtick=1),
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=TEXT),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
                    margin=dict(l=20, r=20, t=20, b=20),
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with gc2:
            st.markdown("#### 🥧 חלוקת סטטוס סריקות")
            status_counts = df_scans['status_label'].value_counts().reset_index()
            status_counts.columns = ['סטטוס', 'מספר']
            fig = px.pie(
                status_counts, names='סטטוס', values='מספר',
                color='סטטוס',
                color_discrete_map={'⚠️ לא נסרק': RED, '✅ נסרק': ACCENT},
                hole=0.4, height=320,
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color=TEXT),
                legend=dict(orientation='h', yanchor='bottom', y=-0.1, x=0.5, xanchor='center'),
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # ============ ביצועים לפי נציג - טבלה ============
        st.markdown("---")
        st.markdown("#### 👥 ביצועים לפי נציג")
        df_scans['scanned_by'] = df_scans['scanned_by'].fillna('לא ידוע').replace('', 'לא ידוע')
        by_scanner = df_scans.groupby('scanned_by').agg(
            total=('id', 'count'),
            ok=('status', lambda s: (s != 'issue').sum()),
            issues=('status', lambda s: (s == 'issue').sum()),
        ).reset_index()
        by_scanner['אחוז_תקינות'] = (by_scanner['ok'] / by_scanner['total'] * 100).round(1).astype(str) + '%'
        by_scanner_display = by_scanner.copy()
        by_scanner_display.columns = ['שם נציג', 'סה"כ סריקות', 'תקינות', 'לא תקינות', 'אחוז תקינות']
        st.dataframe(
            by_scanner_display.sort_values('סה"כ סריקות', ascending=False),
            use_container_width=True, hide_index=True,
        )

        # ============ גרף: נציגים לפי מספר סריקות ============
        st.markdown("---")
        st.markdown("#### 🏆 דירוג נציגים - מספר סריקות")
        st.caption("מציג את הנציגים לפי סך הסריקות שביצעו (תקינות + לא תקינות)")

        rank_scanners = by_scanner.sort_values('total', ascending=True).tail(15)
        if not rank_scanners.empty:
            fig_scanners = px.bar(
                rank_scanners,
                y='scanned_by', x='total',
                orientation='h',
                text='total',
                labels={'scanned_by': 'נציג', 'total': 'סה"כ סריקות'},
                color='total',
                color_continuous_scale='Blues',
                height=max(320, len(rank_scanners) * 32),
            )
            fig_scanners.update_traces(textposition='outside')
            fig_scanners.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color=TEXT),
                margin=dict(l=20, r=40, t=20, b=20),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_scanners, use_container_width=True, config={'displayModeBar': False})

        # ============ גרף: נציגים שזיהו הכי הרבה אירועים ============
        if issue_count > 0:
            st.markdown("---")
            st.markdown("#### 🎯 נציגים שזיהו הכי הרבה אירועים")
            st.caption("נציגים שסימנו הכי הרבה מצלמות כ'לא נסרק' - מזהי האירועים המובילים")

            top_detectors = by_scanner[by_scanner['issues'] > 0].sort_values('issues', ascending=True).tail(15)
            if not top_detectors.empty:
                fig_detectors = px.bar(
                    top_detectors,
                    y='scanned_by', x='issues',
                    orientation='h',
                    text='issues',
                    labels={'scanned_by': 'נציג', 'issues': 'מספר אירועים שזוהו'},
                    color='issues',
                    color_continuous_scale='Reds',
                    height=max(320, len(top_detectors) * 32),
                )
                fig_detectors.update_traces(textposition='outside')
                fig_detectors.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=TEXT),
                    margin=dict(l=20, r=40, t=20, b=20),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_detectors, use_container_width=True, config={'displayModeBar': False})

        # ============ גרף: נציגים שפספסו הכי הרבה סריקות ============
        try:
            missed_all = sch.get_missed_scans(now, lookback_hours=168)  # שבוע אחורה
        except Exception:
            missed_all = []

        # סינון לפי טווח התאריכים שנבחר
        missed_in_range = []
        for hk, cam in missed_all:
            try:
                hk_date_str = hk[:10]
                hk_date = datetime.strptime(hk_date_str, "%Y-%m-%d").date()
                if start_date <= hk_date <= end_date:
                    missed_in_range.append((hk, cam))
            except (ValueError, TypeError):
                pass

        # מפוצל לפי איזה נציג היה במשמרת בשעה שהוחמצה
        if missed_in_range and not df_scans.empty:
            st.markdown("---")
            st.markdown("#### ⚠️ נציגים שפספסו הכי הרבה סריקות")
            st.caption(f"סריקות שלא בוצעו כלל בזמן המתוכנן · טווח נבחר · סה\"כ {len(missed_in_range)} החמצות")

            # בונים dictionary של שעה -> נציג פעיל באותה שעה
            df_scans_sorted = df_scans.sort_values('scanned_at')
            df_scans_sorted['scan_hour'] = df_scans_sorted['scheduled_hour']
            hour_to_scanner = {}
            for _, row in df_scans_sorted.iterrows():
                h = row['scheduled_hour']
                if h not in hour_to_scanner:
                    hour_to_scanner[h] = row['scanned_by']

            # ספירת החמצות פר נציג
            misses_by_scanner = {}
            for hk, cam in missed_in_range:
                scanner = hour_to_scanner.get(hk, '(לא ידוע - אין סריקות בשעה)')
                misses_by_scanner[scanner] = misses_by_scanner.get(scanner, 0) + 1

            if misses_by_scanner:
                misses_df = pd.DataFrame([
                    {'scanner': k, 'misses': v}
                    for k, v in misses_by_scanner.items()
                ]).sort_values('misses', ascending=True).tail(15)

                fig_misses = px.bar(
                    misses_df,
                    y='scanner', x='misses',
                    orientation='h',
                    text='misses',
                    labels={'scanner': 'נציג', 'misses': 'מספר סריקות שהוחמצו'},
                    color='misses',
                    color_continuous_scale='Oranges',
                    height=max(320, len(misses_df) * 32),
                )
                fig_misses.update_traces(textposition='outside')
                fig_misses.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=TEXT),
                    margin=dict(l=20, r=40, t=20, b=20),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_misses, use_container_width=True, config={'displayModeBar': False})
                st.caption("💡 הערה: הנציג משויך לשעה לפי מי שביצע סריקות באותה שעה. אם אף אחד לא סרק - הנתון יוצג כ'לא ידוע'.")

        # ============ גרף: מוקדים עם הכי הרבה אירועים ============
        if issue_count > 0:
            st.markdown("---")
            st.markdown("#### 🔥 מצלמות עם הכי הרבה אירועים שזוהו")
            st.caption("המצלמות שדרכן זוהו הכי הרבה אירועים - מקומות שדורשים תשומת לב מיוחדת")

            df_issues_only = pd.DataFrame(all_issues_scans)
            top_cams = df_issues_only.groupby('camera_name').size().reset_index(name='count').sort_values('count', ascending=True).tail(15)

            if not top_cams.empty:
                fig_top_cams = px.bar(
                    top_cams,
                    y='camera_name', x='count',
                    orientation='h',
                    text='count',
                    labels={'camera_name': 'שם מצלמה', 'count': 'מספר אירועים'},
                    color='count',
                    color_continuous_scale='Reds',
                    height=max(320, len(top_cams) * 32),
                )
                fig_top_cams.update_traces(textposition='outside')
                fig_top_cams.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=TEXT),
                    margin=dict(l=20, r=40, t=20, b=20),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_top_cams, use_container_width=True, config={'displayModeBar': False})

            # טבלה נוספת - כל המצלמות עם אירועים
            st.markdown("**📊 טבלה מלאה של כל המצלמות עם אירועים**")
            top_cams_full = df_issues_only.groupby('camera_name').size().reset_index(name='מספר אירועים').sort_values('מספר אירועים', ascending=False)
            top_cams_full.columns = ['שם מצלמה', 'מספר אירועים']
            st.dataframe(top_cams_full, use_container_width=True, hide_index=True)

        if issue_count > 0:
            st.markdown("---")
            st.markdown("#### 🔥 מוקדים עם הכי הרבה אירועים")
            df_issues_only = pd.DataFrame(all_issues_scans)
            top_cams = df_issues_only.groupby('camera_name').size().reset_index(name='מספר אירועים').sort_values('מספר אירועים', ascending=False).head(10)
            top_cams.columns = ['שם מצלמה', 'מספר אירועים']
            st.dataframe(top_cams, use_container_width=True, hide_index=True)
    else:
        st.info("אין נתוני סריקה בטווח הנבחר")
    # ============ טבלת סריקות מפורטת - כל הסריקות עם שעת ביצוע ============
    if all_scans:
        st.markdown("---")
        st.markdown("#### 🕐 יומן סריקות מפורט")
        st.caption(f"כל הסריקות בטווח - עם שעת הביצוע המדויקת · סה\"כ {len(all_scans)} סריקות")

        filter_scanner_col, filter_status_col, filter_cam_col = st.columns([2, 2, 3])

        # סינון לפי נציג
        all_scanners = sorted(set(s.get('scanned_by') or '(לא ידוע)' for s in all_scans))
        selected_scanner = filter_scanner_col.selectbox(
            "👤 סנן לפי נציג",
            ["כל הנציגים"] + all_scanners,
            key="dash_scanner_filter",
        )

        # סינון לפי סטטוס
        selected_scan_status = filter_status_col.selectbox(
            "סטטוס",
            ["הכל", "✅ תקין בלבד", "⚠️ לא תקין בלבד"],
            key="dash_status_filter",
        )

        # חיפוש מצלמה
        camera_search = filter_cam_col.text_input(
            "🔍 חיפוש מצלמה",
            "",
            placeholder="הקלד שם או חלק ממנו...",
            key="dash_cam_search",
        )

        # החלת הסינונים
        filtered_scans = all_scans
        if selected_scanner != "כל הנציגים":
            if selected_scanner == '(לא ידוע)':
                filtered_scans = [s for s in filtered_scans if not s.get('scanned_by')]
            else:
                filtered_scans = [s for s in filtered_scans if s.get('scanned_by') == selected_scanner]
        if selected_scan_status == "✅ תקין בלבד":
            filtered_scans = [s for s in filtered_scans if (s.get('status') or 'ok') != 'issue']
        elif selected_scan_status == "⚠️ לא תקין בלבד":
            filtered_scans = [s for s in filtered_scans if s.get('status') == 'issue']
        if camera_search.strip():
            q = camera_search.strip().lower()
            filtered_scans = [s for s in filtered_scans if q in (s.get('camera_name') or '').lower()]

        st.caption(f"מציג: {len(filtered_scans)} סריקות")

        # מיון לפי שעת ביצוע (החדשות למעלה)
        sorted_scans = sorted(
            filtered_scans,
            key=lambda x: x.get('scanned_at') or x.get('scheduled_hour', ''),
            reverse=True,
        )

        # בניית טבלה עם שעה מדויקת ופער זמן
        rows = []
        for s in sorted_scans[:100]:  # הגבלה של 100 שורות תצוגה - למקרה של הרבה נתונים
            status = s.get('status') or 'ok'
            scheduled = s.get('scheduled_hour', '')
            scanned_at = s.get('scanned_at') or ''

            # חישוב פער זמן: כמה זמן אחרי השעה המתוזמנת נסרק בפועל
            time_diff_display = '-'
            if scheduled and scanned_at:
                try:
                    sched_dt = datetime.strptime(scheduled, "%Y-%m-%d %H:%M")
                    actual_dt = datetime.strptime(scanned_at[:19], "%Y-%m-%d %H:%M:%S")
                    diff_minutes = int((actual_dt - sched_dt).total_seconds() / 60)
                    if diff_minutes < 0:
                        time_diff_display = f"⏰ {abs(diff_minutes)} דק' מוקדם"
                    elif diff_minutes < 15:
                        time_diff_display = f"✅ בזמן ({diff_minutes} דק')"
                    elif diff_minutes < 60:
                        time_diff_display = f"🟡 {diff_minutes} דק' באיחור"
                    else:
                        hours = diff_minutes // 60
                        mins = diff_minutes % 60
                        time_diff_display = f"🔴 {hours}:{mins:02d} באיחור"
                except (ValueError, TypeError):
                    time_diff_display = '-'

            rows.append({
                "שעה מתוזמנת": scheduled,
                "בוצע בפועל": scanned_at[:19] if scanned_at else '-',
                "פער זמן": time_diff_display,
                "שם המצלמה": s.get('camera_name', '-'),
                "סטטוס": "⚠️ לא תקין" if status == 'issue' else "✅ תקין",
                "נציג": s.get('scanned_by') or '-',
                "פירוט": s.get('event_details') or '-',
            })

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            if len(sorted_scans) > 100:
                st.caption(f"⚠️ מציג 100 מתוך {len(sorted_scans)} תוצאות. צמצם סינון או ייצא לקובץ CSV לתצוגה מלאה.")
        else:
            st.info("אין סריקות התואמות לסינון")
    # ============ סיווג אירועים: בטחון / השלכות / בטיחות / אחר ============
    if all_issues_scans:
        st.markdown("---")
        st.markdown("#### 🛡️ סיווג אירועים אוטומטי")
        st.caption("סיווג לפי מילות מפתח בפירוט האירוע · אירועים ללא מילים מזוהות מסווגים כ'אחר'")

        security_keywords = [
            'אלימות', 'ונדליזם', 'קטטה', 'פלילי', 'התקהלות',
            'רכב חשוד', 'חשוד', 'פריצה', 'גניבה', 'שוטטות',
            'תגרה', 'סכין', 'נשק', 'איום', 'תקיפה', 'שוד',
        ]
        dumping_keywords = [
            'השלכ', 'פסולת', 'גזם', 'גרוטא', 'ניקיון', 'זבל',
            'אשפה', 'לכלוך', 'שקיות', 'ריהוט', 'שאריות',
        ]
        safety_keywords = [
            'בטיחות', 'בור', 'תאורה', 'מפגע', 'סכנה', 'סכן',
            'שבור', 'שבורה', 'חסום', 'תקלת חשמל', 'עמוד', 'שלט',
        ]

        def categorize_event(scan_item):
            """
            סיווג משולב: קודם בודק אם הנציג סימן קטגוריה במפורש,
            אחרת נופל אחורה לזיהוי אוטומטי לפי מילות מפתח (עבור סריקות ישנות).
            """
            explicit_cat = scan_item.get('event_category')
            if explicit_cat == 'security':
                return 'בטחון'
            if explicit_cat == 'dumping':
                return 'גזם/גרוטאות'
            if explicit_cat == 'safety':
                return 'בטיחות'
            if explicit_cat == 'other':
                return 'אחר'

            # fallback לזיהוי אוטומטי לסריקות ישנות שאין להן קטגוריה
            text = scan_item.get('event_details', '')
            if not text or str(text).strip() == '-':
                return 'ללא פירוט'
            text_str = str(text).lower()
            for kw in security_keywords:
                if kw in text_str:
                    return 'בטחון'
            for kw in dumping_keywords:
                if kw in text_str:
                    return 'גזם/גרוטאות'
            for kw in safety_keywords:
                if kw in text_str:
                    return 'בטיחות'
            return 'אחר'

        # החלת הסיווג על כל האירועים
        categorized = []
        for s in all_issues_scans:
            cat = categorize_event(s)
            item = dict(s)
            item['category'] = cat
            categorized.append(item)

        df_cat = pd.DataFrame(categorized)
        counts = df_cat['category'].value_counts()

        # ---- ארבעה מדדים מרכזיים ----
        security_count = int(counts.get('בטחון', 0))
        dumping_count = int(counts.get('גזם/גרוטאות', 0))
        safety_count = int(counts.get('בטיחות', 0))
        other_count = int(counts.get('אחר', 0)) + int(counts.get('ללא פירוט', 0))

        cm1, cm2, cm3, cm4 = st.columns(4)
        cm1.metric("🛡️ אירועי בטחון", security_count)
        cm2.metric("🗑️ גזם וגרוטאות", dumping_count)
        cm3.metric("⚠️ מפגעי בטיחות", safety_count)
        cm4.metric("❓ אחר / לא מסווג", other_count)

        color_map_cat = {
            'בטחון': '#dc2626',
            'גזם/גרוטאות': '#d97706',
            'בטיחות': '#ca8a04',
            'אחר': '#94a3b8',
            'ללא פירוט': '#64748b',
        }

        # ---- שני גרפים זה לצד זה ----
        cat_g1, cat_g2 = st.columns(2)

        with cat_g1:
            st.markdown("**🥧 חלוקת אירועים לפי סוג**")
            pie_df = counts.reset_index()
            pie_df.columns = ['קטגוריה', 'כמות']
            fig_pie = px.pie(
                pie_df, names='קטגוריה', values='כמות',
                color='קטגוריה', color_discrete_map=color_map_cat,
                hole=0.4, height=320,
            )
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color=TEXT),
                legend=dict(orientation='h', yanchor='bottom', y=-0.15, x=0.5, xanchor='center'),
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})

        with cat_g2:
            st.markdown("**📊 מגמה יומית לפי סוג**")
            try:
                df_cat['date_only'] = pd.to_datetime(df_cat['scheduled_hour'], errors='coerce').dt.date
                by_date_cat = df_cat.groupby(['date_only', 'category']).size().reset_index(name='count')
                by_date_cat['date_only'] = by_date_cat['date_only'].astype(str)

                if not by_date_cat.empty:
                    fig_trend = px.bar(
                        by_date_cat, x='date_only', y='count', color='category',
                        color_discrete_map=color_map_cat,
                        labels={'date_only': 'תאריך', 'count': 'מספר אירועים', 'category': 'סוג'},
                        height=320,
                    )
                    fig_trend.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color=TEXT),
                        legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
                        margin=dict(l=20, r=20, t=40, b=20),
                        xaxis_title=None,
                    )
                    st.plotly_chart(fig_trend, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("אין נתונים להצגה")
            except Exception:
                st.info("אין נתונים להצגה")

        # ---- טבלה השוואתית לפי נציג ----
        st.markdown("**👥 סיווג אירועים לפי נציג**")
        df_cat['scanner_name'] = df_cat['scanned_by'].fillna('לא ידוע').replace('', 'לא ידוע')
        pivot_scanner_cat = df_cat.pivot_table(
            index='scanner_name',
            columns='category',
            values='id',
            aggfunc='count',
            fill_value=0,
        ).reset_index()

        # וידוא שכל העמודות קיימות
        for col in ['בטחון', 'גזם/גרוטאות', 'בטיחות', 'אחר', 'ללא פירוט']:
            if col not in pivot_scanner_cat.columns:
                pivot_scanner_cat[col] = 0

        pivot_scanner_cat['סה"כ'] = (
            pivot_scanner_cat['בטחון'] + pivot_scanner_cat['גזם/גרוטאות'] +
            pivot_scanner_cat['בטיחות'] + pivot_scanner_cat['אחר'] +
            pivot_scanner_cat.get('ללא פירוט', 0)
        )
        pivot_scanner_cat = pivot_scanner_cat.sort_values('סה"כ', ascending=False)
        pivot_scanner_cat = pivot_scanner_cat.rename(columns={'scanner_name': 'נציג'})

        # סידור עמודות בסדר הגיוני
        cols_order = ['נציג', 'בטחון', 'גזם/גרוטאות', 'בטיחות', 'אחר']
        if 'ללא פירוט' in pivot_scanner_cat.columns:
            cols_order.append('ללא פירוט')
        cols_order.append('סה"כ')
        cols_order = [c for c in cols_order if c in pivot_scanner_cat.columns]

        st.dataframe(pivot_scanner_cat[cols_order], use_container_width=True, hide_index=True)

        # ---- פירוט אירועים לפי קטגוריה ----
        with st.expander("📋 פירוט אירועים לפי סיווג", expanded=False):
            for cat_name in ['בטחון', 'גזם/גרוטאות', 'בטיחות', 'אחר', 'ללא פירוט']:
                cat_items = [s for s in categorized if s['category'] == cat_name]
                if cat_items:
                    st.markdown(f"### {cat_name} · {len(cat_items)} אירועים")
                    rows_cat = []
                    for s in sorted(cat_items, key=lambda x: x.get('scheduled_hour', ''), reverse=True)[:30]:
                        rows_cat.append({
                            'שעה מתוזמנת': s.get('scheduled_hour', '-'),
                            'בוצע בפועל': (s.get('scanned_at') or '-')[:19],
                            'מצלמה': s.get('camera_name', '-'),
                            'פירוט האירוע': s.get('event_details') or '-',
                            'נציג': s.get('scanned_by') or '-',
                        })
                    st.dataframe(pd.DataFrame(rows_cat), use_container_width=True, hide_index=True)
                    if len(cat_items) > 30:
                        st.caption(f"מציג 30 מתוך {len(cat_items)}")
                    st.markdown("")
    if all_issues_scans:
        st.markdown("---")
        st.markdown("#### ⚠️ אירועים אחרונים בסריקות")
        rows = []
        for s in sorted(all_issues_scans, key=lambda x: x['scheduled_hour'], reverse=True)[:20]:
            rows.append({
                "שעה מתוזמנת": s['scheduled_hour'],
                "בוצע בפועל": s.get('scanned_at', '-'),
                "שם המצלמה": s['camera_name'],
                "פירוט האירוע": s.get('event_details') or '-',
                "דווח ע\"י": s.get('scanned_by') or '-',
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if active_faults_list:
        st.markdown("---")
        st.markdown("#### 🚫 מצלמות תקולות פעילות")
        rows = []
        for f in active_faults_list:
            rows.append({
                "שם המצלמה": f['camera_name'],
                "תאריך תקלה": f['fault_datetime'],
                "תיאור": f['description'],
                "דווח ע\"י": f.get('reported_by') or '-',
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
# ============ בדיקות קשר לילה ============
    comm_checks_data = db.get_comm_checks_in_date_range(str(start_date), str(end_date))
    if comm_checks_data:
        st.markdown("---")
        st.markdown("#### 🌙 בדיקות קשר במשמרות לילה")

        total_checks = len(comm_checks_data)
        done_checks = sum(1 for c in comm_checks_data if c.get('actual_time'))
        missed_checks = 0
        for c in comm_checks_data:
            if not c.get('actual_time') and c['scheduled_time'] < now_il().strftime("%Y-%m-%d %H:%M"):
                missed_checks += 1

        compliance_comm_pct = round((done_checks / total_checks * 100), 1) if total_checks > 0 else 0

        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("סה\"כ בדיקות מתוזמנות", total_checks)
        cc2.metric("בדיקות שבוצעו", done_checks)
        cc3.metric("בדיקות שהוחמצו", missed_checks)
        cc4.metric("אחוז עמידה", f"{compliance_comm_pct}%")

        # טבלת פירוט
        with st.expander(f"📋 פירוט כל בדיקות הקשר בטווח ({total_checks} בדיקות)", expanded=False):
            rows_cc = []
            for c in comm_checks_data:
                actual = c.get('actual_time', '') or ''
                if actual:
                    try:
                        sched = datetime.strptime(c['scheduled_time'], "%Y-%m-%d %H:%M")
                        act = datetime.strptime(actual[:19], "%Y-%m-%d %H:%M:%S")
                        diff_min = int((act - sched).total_seconds() / 60)
                        if diff_min < 0:
                            timing = f"מוקדם ב-{abs(diff_min)} דק'"
                        elif diff_min < 5:
                            timing = f"✅ בזמן ({diff_min} דק')"
                        else:
                            timing = f"🟡 באיחור {diff_min} דק'"
                    except (ValueError, TypeError):
                        timing = '-'
                    status_txt = f"✅ בוצע"
                    actual_display = actual[11:19]
                else:
                    if c['scheduled_time'] < now_il().strftime("%Y-%m-%d %H:%M"):
                        status_txt = "❌ הוחמצה"
                        timing = '-'
                    else:
                        status_txt = "⏰ ממתינה"
                        timing = '-'
                    actual_display = '-'

                rows_cc.append({
                    'תאריך': c['scheduled_time'][:10],
                    'שעה מתוזמנת': c['scheduled_time'][11:],
                    'בוצע בפועל': actual_display,
                    'סטטוס': status_txt,
                    'עמידה בזמן': timing,
                })

            st.dataframe(pd.DataFrame(rows_cc), use_container_width=True, hide_index=True)
    st.markdown("---")
    st.markdown("#### 📥 ייצוא נתונים")
    ec1, ec2 = st.columns(2)

    if all_scans:
        df_export = pd.DataFrame(all_scans)
        if not df_export.empty:
            csv = df_export.to_csv(index=False).encode('utf-8-sig')
            ec1.download_button(
                "📥 ייצא נתוני סריקות (CSV)", csv,
                f"scans_{start_date}_to_{end_date}.csv", "text/csv",
                use_container_width=True,
            )

    if all_faults_list:
        df_export_faults = pd.DataFrame(all_faults_list)
        csv_faults = df_export_faults.to_csv(index=False).encode('utf-8-sig')
        ec2.download_button(
            "📥 ייצא נתוני תקלות (CSV)", csv_faults,
            f"faults_{start_date}_to_{end_date}.csv", "text/csv",
            use_container_width=True,
        )


# ============ עמוד: נקודות חמות ============
elif page == "לוז סריקות":
    if st.session_state.get('user_role') != 'manager':
        st.error("עמוד זה זמין למנהלת בלבד")
        st.stop()

    st.header("📅 לו״ז סריקות")
    st.caption("הגדרת חלונות זמן קבועים שבהם יש לסרוק מצלמות ספציפיות · הלו״ז מוצג למוקדן בזמן אמת")

    all_plans = db.get_all_scheduled_plans(active_only=True)
    all_cams_for_plan = db.get_all_cameras()

    # ---- טופס עריכה/הוספה ----
    editing_id = st.session_state.get('editing_plan_id')
    adding_new = st.session_state.get('adding_new_plan', False)

    if editing_id or adding_new:
        plan = next((p for p in all_plans if p['id'] == editing_id), None) if editing_id else {}
        title = f"✏️ עריכת תוכנית: {plan.get('name', '')}" if editing_id else "➕ הוספת תוכנית לו״ז"
        st.markdown(f"### {title}")

        with st.form(f"plan_form_{editing_id or 'new'}", clear_on_submit=False):
            name = st.text_input("שם התוכנית *", value=plan.get('name', ''),
                                 placeholder="למשל: בוקר - מוסדות חינוך")
            description = st.text_area("תיאור (מה לחפש/דגשים)",
                                        value=plan.get('description', ''),
                                        placeholder="ונדליזם, התקהלות, מפגעי בטיחות...",
                                        height=60)

            tc1, tc2 = st.columns(2)
            start_time = tc1.text_input("שעת התחלה (HH:MM) *",
                                         value=plan.get('start_time', '07:00'),
                                         placeholder="07:00")
            end_time = tc2.text_input("שעת סיום (HH:MM) *",
                                       value=plan.get('end_time', '09:00'),
                                       placeholder="09:00")
            st.caption("💡 טיפ: לחלון שחוצה חצות (למשל לילה 23:00-05:00) - הזן start=23:00, end=05:00")

            priority = st.selectbox(
                "עדיפות",
                ['high', 'medium', 'low'],
                format_func=lambda x: {'high': '🔴 גבוהה', 'medium': '🟠 בינונית', 'low': '🟢 נמוכה'}[x],
                index=['high', 'medium', 'low'].index(plan.get('priority', 'medium')),
            )

            # ---- ימי שבוע ----
            st.markdown("**📆 ימי פעילות**")
            days_str = plan.get('days_of_week', 'all')
            all_days_selected = (days_str == 'all')
            selected_days_set = set() if all_days_selected else set(days_str.split(','))

            all_days_check = st.checkbox("פעיל בכל ימי השבוע", value=all_days_selected)

            selected_days = []
            if not all_days_check:
                st.caption("סמן את הימים שבהם התוכנית פעילה:")
                dc1, dc2, dc3, dc4, dc5, dc6, dc7 = st.columns(7)
                day_map = [
                    ('6', 'א׳', dc1),  # Sunday = 6 in Python weekday()
                    ('0', 'ב׳', dc2),  # Monday = 0
                    ('1', 'ג׳', dc3),
                    ('2', 'ד׳', dc4),
                    ('3', 'ה׳', dc5),
                    ('4', 'ו׳', dc6),
                    ('5', 'ש׳', dc7),
                ]
                for day_num, day_label, col in day_map:
                    if col.checkbox(day_label, value=day_num in selected_days_set,
                                    key=f"day_{editing_id}_{day_num}"):
                        selected_days.append(day_num)

            # ---- שיוך מצלמות ----
            st.markdown("**🎥 מצלמות בתוכנית**")

            # אופציה למילוי לפי אזור
            all_areas_plan = sorted(set(c.get('area', '') for c in all_cams_for_plan if c.get('area')))
            selected_area_bulk = st.selectbox(
                "💡 מלא אוטומטית לפי אזור (אופציונלי)",
                ["-- בחר אזור להוספה מהירה --"] + all_areas_plan,
                key=f"area_bulk_{editing_id or 'new'}",
            )

            cam_display = {f"{c['name']} ({c.get('area', '') or 'לא ידוע'})": c['id']
                           for c in all_cams_for_plan}
            current_cam_ids = set(plan.get('camera_ids', []))

            if selected_area_bulk != "-- בחר אזור להוספה מהירה --":
                # הוספת כל המצלמות באזור לבחירה
                area_cam_ids = {c['id'] for c in all_cams_for_plan if c.get('area') == selected_area_bulk}
                current_cam_ids = current_cam_ids | area_cam_ids

            current_cam_labels = [lbl for lbl, cid in cam_display.items() if cid in current_cam_ids]

            selected_cam_labels = st.multiselect(
                f"בחר מצלמות ({len(current_cam_labels)} נבחרו)",
                list(cam_display.keys()),
                default=current_cam_labels,
            )
            selected_cam_ids = [cam_display[l] for l in selected_cam_labels]

            bc1, bc2 = st.columns(2)
            save = bc1.form_submit_button("💾 שמור", type="primary", use_container_width=True)
            cancel = bc2.form_submit_button("↩️ ביטול", use_container_width=True)

            if save:
                if not name.strip():
                    st.error("יש למלא שם")
                elif not start_time.strip() or not end_time.strip():
                    st.error("יש למלא שעת התחלה וסיום")
                else:
                    # validate time format
                    import re
                    time_pattern = r'^\d{2}:\d{2}$'
                    if not re.match(time_pattern, start_time.strip()) or not re.match(time_pattern, end_time.strip()):
                        st.error("פורמט זמן שגוי - השתמש ב-HH:MM (למשל 07:00)")
                    else:
                        days_value = 'all' if all_days_check else (','.join(selected_days) if selected_days else 'all')
                        if editing_id:
                            db.update_scheduled_plan(
                                editing_id,
                                name=name.strip(),
                                description=description.strip(),
                                start_time=start_time.strip(),
                                end_time=end_time.strip(),
                                days_of_week=days_value,
                                priority=priority,
                                camera_ids=selected_cam_ids,
                            )
                            st.success("התוכנית עודכנה")
                        else:
                            db.add_scheduled_plan(
                                name=name.strip(),
                                description=description.strip(),
                                start_time=start_time.strip(),
                                end_time=end_time.strip(),
                                days_of_week=days_value,
                                priority=priority,
                                camera_ids=selected_cam_ids,
                            )
                            st.success("התוכנית נוספה")
                        st.session_state.pop('editing_plan_id', None)
                        st.session_state.pop('adding_new_plan', None)
                        st.rerun()

            if cancel:
                st.session_state.pop('editing_plan_id', None)
                st.session_state.pop('adding_new_plan', None)
                st.rerun()

        st.stop()

    # כפתור הוספה
    if st.button("➕ הוסף תוכנית לו״ז חדשה", type="primary"):
        st.session_state['adding_new_plan'] = True
        st.rerun()

    # ---- רשימת תוכניות ----
    if not all_plans:
        st.info(
            "אין תוכניות לו״ז מוגדרות עדיין.\n\n"
            "**דוגמאות לתוכניות שכדאי להגדיר:**\n"
            "- בוקר (07:00-09:00) - מוסדות חינוך + צירי תנועה\n"
            "- עומס בוקר (09:00-11:00) - נקודות חמות\n"
            "- ערב (16:00-20:00) - פארקים וגינות משחקים\n"
            "- לילה (23:00-05:00) - נקודות חמות + אתרי בנייה"
        )
    else:
        st.markdown(f"### 📋 תוכניות פעילות · {len(all_plans)}")

        priority_icons = {'high': '🔴', 'medium': '🟠', 'low': '🟢'}
        priority_labels = {'high': 'גבוהה', 'medium': 'בינונית', 'low': 'נמוכה'}
        day_labels_map = {'6': 'א׳', '0': 'ב׳', '1': 'ג׳', '2': 'ד׳', '3': 'ה׳', '4': 'ו׳', '5': 'ש׳'}

        for plan in all_plans:
            icon = priority_icons.get(plan.get('priority', 'medium'), '⚪')
            plabel = priority_labels.get(plan.get('priority', 'medium'), '')

            days_str = plan.get('days_of_week', 'all')
            if days_str == 'all':
                days_display = 'כל ימי השבוע'
            else:
                days_list = days_str.split(',')
                days_display = ' · '.join([day_labels_map.get(d, d) for d in days_list])

            cams_count = len(plan.get('camera_ids', []))

            with st.container(border=True):
                st.markdown(f"### {icon} {plan['name']}")
                st.caption(
                    f"⏰ {plan.get('start_time', '?')} - {plan.get('end_time', '?')}  ·  "
                    f"📆 {days_display}  ·  עדיפות: {plabel}  ·  🎥 {cams_count} מצלמות"
                )
                if plan.get('description'):
                    st.markdown(f"**📝 תיאור:** {plan.get('description')}")

                ac1, ac2, _ac3 = st.columns([1, 1, 4])
                if ac1.button("✏️ ערוך", key=f"edit_plan_{plan['id']}"):
                    st.session_state['editing_plan_id'] = plan['id']
                    st.rerun()
                if ac2.button("🗑️ הסר", key=f"del_plan_{plan['id']}"):
                    db.delete_scheduled_plan(plan['id'])
                    st.rerun()
elif page == "נקודות חמות":
    _is_manager_hs = st.session_state.get('user_role') == 'manager'
    st.header("🔥 נקודות חמות")
    if _is_manager_hs:
        st.caption("ניהול נקודות חמות - הוספה, עריכה ומחיקה")
    else:
        st.caption("נקודות חמות במוקד - צפייה בלבד")

    all_hotspots = db.get_all_hotspots(active_only=True)

    if _is_manager_hs:
        editing_id = st.session_state.get('editing_hotspot_id')
        adding_new = st.session_state.get('adding_new_hotspot', False)

        if editing_id or adding_new:
            hs = next((h for h in all_hotspots if h['id'] == editing_id), None) if editing_id else {}
            title = f"✏️ עריכת נקודה חמה: {hs.get('name', '')}" if editing_id else "➕ הוספת נקודה חמה חדשה"
            st.markdown(f"### {title}")

            with st.form(f"hotspot_form_{editing_id or 'new'}", clear_on_submit=False):
                fc1, fc2 = st.columns(2)
                name = fc1.text_input("שם הנקודה החמה *", value=hs.get('name', ''))
                area = fc2.text_input("אזור", value=hs.get('area', ''))

                priority = st.selectbox(
                    "עדיפות",
                    ['high', 'medium', 'low'],
                    format_func=lambda x: {'high': '🔴 גבוהה', 'medium': '🟠 בינונית', 'low': '🟢 נמוכה'}[x],
                    index=['high', 'medium', 'low'].index(hs.get('priority', 'medium')),
                )

                watching_for = st.text_area(
                    "מה מחפשים במקום?",
                    value=hs.get('watching_for', ''),
                    placeholder="ונדליזם, רעש, התקהלות...",
                    height=80,
                )

                st.markdown("**⏰ שעות פעילות**")
                st.caption("סמן את חלונות הזמן בהם הנקודה החמה פעילה במיוחד")
                time_windows = [
                    ("07:00-09:00", "בוקר מוקדם"),
                    ("09:00-11:00", "עומס בוקר"),
                    ("11:00-13:00", "צהריים"),
                    ("13:00-16:00", "אחר צהריים"),
                    ("16:00-20:00", "אחרי הצהריים"),
                    ("20:00-23:00", "ערב"),
                    ("23:00-05:00", "לילה"),
                    ("05:00-07:00", "שחר"),
                ]
                current_windows = set(hs.get('active_hours', []))
                selected_windows = []
                tc1, tc2 = st.columns(2)
                for i, (window, label) in enumerate(time_windows):
                    col = tc1 if i % 2 == 0 else tc2
                    if col.checkbox(f"{window} · {label}", value=window in current_windows, key=f"win_{editing_id}_{window}"):
                        selected_windows.append(window)

                st.markdown("**🎥 שיוך מצלמות**")
                cams_for_hs = db.get_all_cameras()
                cam_display = {f"{c['name']} ({c.get('area', '') or 'לא ידוע'})": c['id'] for c in cams_for_hs}
                current_cam_ids = set(hs.get('camera_ids', []))
                current_cam_labels = [lbl for lbl, cid in cam_display.items() if cid in current_cam_ids]

                selected_cam_labels = st.multiselect(
                    "בחר מצלמות משויכות",
                    list(cam_display.keys()),
                    default=current_cam_labels,
                )
                selected_cam_ids = [cam_display[l] for l in selected_cam_labels]

                notes = st.text_area("הערות", value=hs.get('notes', ''), height=60)

                bc1, bc2 = st.columns(2)
                save = bc1.form_submit_button("💾 שמור", type="primary", use_container_width=True)
                cancel = bc2.form_submit_button("↩️ ביטול", use_container_width=True)

                if save:
                    if not name.strip():
                        st.error("יש למלא שם")
                    else:
                        if editing_id:
                            db.update_hotspot(
                                editing_id,
                                name=name.strip(), area=area.strip(),
                                priority=priority, watching_for=watching_for.strip(),
                                notes=notes.strip(),
                                active_hours=selected_windows,
                                camera_ids=selected_cam_ids,
                            )
                            st.success("עודכן בהצלחה")
                        else:
                            new_id = db.add_hotspot(
                                name=name.strip(), area=area.strip(),
                                priority=priority, watching_for=watching_for.strip(),
                                notes=notes.strip(),
                                active_hours=selected_windows,
                                camera_ids=selected_cam_ids,
                            )
                            if new_id:
                                st.success("נוסף בהצלחה")
                            else:
                                st.error("שם כבר קיים במערכת")
                        st.session_state.pop('editing_hotspot_id', None)
                        st.session_state.pop('adding_new_hotspot', None)
                        st.rerun()

                if cancel:
                    st.session_state.pop('editing_hotspot_id', None)
                    st.session_state.pop('adding_new_hotspot', None)
                    st.rerun()

            st.stop()

        if st.button("➕ הוסף נקודה חמה חדשה", type="primary"):
            st.session_state['adding_new_hotspot'] = True
            st.rerun()

    if not all_hotspots:
        st.info("אין נקודות חמות מוגדרות במערכת עדיין")
    else:
        st.markdown(f"### 📋 נקודות חמות פעילות · {len(all_hotspots)}")

        priority_icons_map = {'high': '🔴', 'medium': '🟠', 'low': '🟢'}
        priority_labels_map = {'high': 'גבוהה', 'medium': 'בינונית', 'low': 'נמוכה'}

        for hs in all_hotspots:
            p = hs.get('priority', 'medium')
            hours_display = ' · '.join(hs.get('active_hours', [])) if hs.get('active_hours') else 'לא הוגדר'
            cams_count = len(hs.get('camera_ids', []))
            area_display = hs.get('area', '') or 'לא הוגדר'
            watching_display = hs.get('watching_for') or 'לא הוגדר'
            icon = priority_icons_map.get(p, '⚪')
            plabel = priority_labels_map.get(p, p)

            with st.container(border=True):
                st.markdown(f"### {icon} {hs['name']}")
                st.caption(f"🗂️ {area_display}  ·  עדיפות: {plabel}  ·  {cams_count} מצלמות משויכות")
                st.markdown(f"**⏰ שעות פעילות:** {hours_display}")
                st.markdown(f"**👁️ מה מחפשים:** {watching_display}")
                if hs.get('notes'):
                    st.markdown(f"**📝 הערות:** {hs.get('notes')}")

                if _is_manager_hs:
                    ac1, ac2, _ac3 = st.columns([1, 1, 4])
                    if ac1.button("✏️ ערוך", key=f"edit_hs_{hs['id']}"):
                        st.session_state['editing_hotspot_id'] = hs['id']
                        st.rerun()
                    if ac2.button("🗑️ הסר", key=f"del_hs_{hs['id']}"):
                        db.delete_hotspot(hs['id'])
                        st.rerun()


# ============ עמוד: אתרי בנייה ============
elif page == "אתרי בנייה":
    _is_manager_cs = st.session_state.get('user_role') == 'manager'
    st.header("🏗️ אתרי בנייה")
    if _is_manager_cs:
        st.caption("ניהול אתרי בנייה - הוספה, עריכה ומחיקה")
    else:
        st.caption("אתרי בנייה פעילים - צפייה בלבד")

    all_sites = db.get_all_construction_sites(active_only=True)

    if _is_manager_cs:
        editing_id = st.session_state.get('editing_site_id')
        adding_new = st.session_state.get('adding_new_site', False)

        if editing_id or adding_new:
            site = next((s for s in all_sites if s['id'] == editing_id), None) if editing_id else {}
            title = f"✏️ עריכת אתר בנייה: {site.get('name', '')}" if editing_id else "➕ הוספת אתר בנייה חדש"
            st.markdown(f"### {title}")

            with st.form(f"site_form_{editing_id or 'new'}", clear_on_submit=False):
                name = st.text_input("שם האתר *", value=site.get('name', ''))
                address = st.text_input("כתובת", value=site.get('address', ''))

                sc1, sc2 = st.columns(2)
                start_date_val = site.get('start_date', '') or ''
                end_date_val = site.get('end_date', '') or ''
                start_date_input = sc1.text_input("תאריך התחלה (YYYY-MM-DD)", value=start_date_val)
                end_date_input = sc2.text_input("תאריך סיום צפוי (YYYY-MM-DD)", value=end_date_val)

                st.markdown("**🎥 מצלמות משויכות לאתר**")
                cams_for_site = db.get_all_cameras()
                cam_display = {f"{c['name']} ({c.get('area', '') or 'לא ידוע'})": c['id'] for c in cams_for_site}
                current_cam_ids = set(site.get('camera_ids', []))
                current_cam_labels = [lbl for lbl, cid in cam_display.items() if cid in current_cam_ids]

                selected_cam_labels = st.multiselect(
                    "בחר מצלמות שרואות את האתר",
                    list(cam_display.keys()),
                    default=current_cam_labels,
                )
                selected_cam_ids = [cam_display[l] for l in selected_cam_labels]

                notes = st.text_area(
                    "הערות", value=site.get('notes', ''),
                    placeholder="דגשים מיוחדים, שעות עבודה, סיכונים...",
                    height=80,
                )

                bc1, bc2 = st.columns(2)
                save = bc1.form_submit_button("💾 שמור", type="primary", use_container_width=True)
                cancel = bc2.form_submit_button("↩️ ביטול", use_container_width=True)

                if save:
                    if not name.strip():
                        st.error("יש למלא שם")
                    else:
                        if editing_id:
                            db.update_construction_site(
                                editing_id,
                                name=name.strip(), address=address.strip(),
                                notes=notes.strip(),
                                start_date=start_date_input.strip() or None,
                                end_date=end_date_input.strip() or None,
                                camera_ids=selected_cam_ids,
                            )
                            st.success("עודכן בהצלחה")
                        else:
                            new_id = db.add_construction_site(
                                name=name.strip(), address=address.strip(),
                                notes=notes.strip(),
                                camera_ids=selected_cam_ids,
                            )
                            if new_id and (start_date_input.strip() or end_date_input.strip()):
                                db.update_construction_site(
                                    new_id,
                                    start_date=start_date_input.strip() or None,
                                    end_date=end_date_input.strip() or None,
                                )
                            if new_id:
                                st.success("נוסף בהצלחה")
                            else:
                                st.error("שם כבר קיים במערכת")
                        st.session_state.pop('editing_site_id', None)
                        st.session_state.pop('adding_new_site', None)
                        st.rerun()

                if cancel:
                    st.session_state.pop('editing_site_id', None)
                    st.session_state.pop('adding_new_site', None)
                    st.rerun()

            st.stop()

        if st.button("➕ הוסף אתר בנייה חדש", type="primary"):
            st.session_state['adding_new_site'] = True
            st.rerun()

    if not all_sites:
        st.info("אין אתרי בנייה מוגדרים במערכת עדיין")
    else:
        st.markdown(f"### 📋 אתרי בנייה פעילים · {len(all_sites)}")

        for site in all_sites:
            cams_count = len(site.get('camera_ids', []))
            date_range = ''
            if site.get('start_date') and site.get('end_date'):
                date_range = f"{site['start_date']} → {site['end_date']}"
            elif site.get('start_date'):
                date_range = f"החל מ-{site['start_date']}"
            elif site.get('end_date'):
                date_range = f"עד {site['end_date']}"

            with st.container(border=True):
                st.markdown(f"### 🏗️ {site['name']}")
                caption_parts = []
                if site.get('address'):
                    caption_parts.append(f"📍 {site.get('address')}")
                caption_parts.append(f"{cams_count} מצלמות משויכות")
                if date_range:
                    caption_parts.append(f"📅 {date_range}")
                st.caption("  ·  ".join(caption_parts))

                if site.get('notes'):
                    st.markdown(f"**📝 הערות:** {site.get('notes')}")

                if _is_manager_cs:
                    ac1, ac2, _ac3 = st.columns([1, 1, 4])
                    if ac1.button("✏️ ערוך", key=f"edit_site_{site['id']}"):
                        st.session_state['editing_site_id'] = site['id']
                        st.rerun()
                    if ac2.button("🗑️ הסר", key=f"del_site_{site['id']}"):
                        db.delete_construction_site(site['id'])
                        st.rerun()


# ============ עמוד: מפה ============
elif page == "מפה":
    st.header("🗺️ מפת מצלמות טירת כרמל")

    try:
        import folium
        from streamlit_folium import st_folium
    except ImportError:
        st.error("חסרות ספריות מפה. וודא ש-`requirements.txt` מכיל: `folium` ו-`streamlit-folium`, ואז Reboot app.")
        st.stop()

    map_tab, area_tab, csv_tab = st.tabs([
        "🗺️ תצוגת מפה",
        "📍 קואורדינטות אזורים",
        "📤 יבוא CSV",
    ])

    all_cams = db.get_all_cameras()
    faulty_ids = db.get_faulty_camera_ids()
    area_coords = _get_area_coords()

    recent_start = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:00")
    recent_end = now.strftime("%Y-%m-%d %H:00")
    recent_issues = db.get_issue_scans_in_range(recent_start, recent_end)
    recent_issue_cam_ids = set(i['camera_id'] for i in recent_issues)

    positioned = []
    unpositioned = []
    for cam in all_cams:
        pos = _camera_map_position(cam, area_coords)
        if pos:
            positioned.append((cam, pos))
        else:
            unpositioned.append(cam)

    with map_tab:
        total = len(all_cams)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("במפה", f"{len(positioned)} / {total}")
        m2.metric("תקולות במפה", sum(1 for c, _ in positioned if c['id'] in faulty_ids))
        m3.metric("אירועים (24ש')", sum(1 for c, _ in positioned if c['id'] in recent_issue_cam_ids))
        m4.metric("ללא מיקום", len(unpositioned))

        if not positioned:
            st.info(
                "🗺️ **אין עדיין מצלמות עם מיקום במפה.**\n\n"
                "**דרכים להוסיף:**\n"
                "1. עבור לטאב **📍 קואורדינטות אזורים** ← הזן קואורדינטה ל-35 אזורים\n"
                "2. עבור לטאב **📤 יבוא CSV** ← העלה קובץ עם כל המיקומים\n"
                "3. עבור ל**ניהול → מצלמות** ← ערוך מצלמה בודדת"
            )
        else:
            filter_opt = st.radio(
                "הצג:",
                ["הכל", "רק תקינות", "רק תקולות", "רק עם אירועים אחרונים"],
                horizontal=True, key="map_filter",
            )

            display = positioned
            if filter_opt == "רק תקינות":
                display = [(c, p) for c, p in positioned
                           if c['id'] not in faulty_ids and c['id'] not in recent_issue_cam_ids]
            elif filter_opt == "רק תקולות":
                display = [(c, p) for c, p in positioned if c['id'] in faulty_ids]
            elif filter_opt == "רק עם אירועים אחרונים":
                display = [(c, p) for c, p in positioned if c['id'] in recent_issue_cam_ids]

            fmap = folium.Map(location=TIRAT_CARMEL_CENTER, zoom_start=14, tiles='OpenStreetMap')

            for cam, (lat, lng) in display:
                is_faulty = cam['id'] in faulty_ids
                has_recent_issue = cam['id'] in recent_issue_cam_ids

                if is_faulty:
                    color = 'red'
                    icon_name = 'exclamation'
                    status_text = '⚠️ תקולה'
                    status_color = '#dc2626'
                elif has_recent_issue:
                    color = 'orange'
                    icon_name = 'eye'
                    status_text = '👁️ אירוע ב-24 שעות אחרונות'
                    status_color = '#d97706'
                else:
                    color = 'green'
                    icon_name = 'video-camera'
                    status_text = '✅ תקינה'
                    status_color = '#16a34a'

                popup_html = f"""
                <div style="direction: rtl; font-family: Arial; min-width: 220px;">
                    <div style="font-weight: bold; font-size: 14px;">{cam['name']}</div>
                    <div style="color: #666; margin-top: 6px; font-size: 12px;">
                        🗂️ {cam.get('area', '') or '-'}
                    </div>
                    <div style="margin-top: 8px; color: {status_color}; font-weight: bold;">
                        {status_text}
                    </div>
                </div>
                """

                folium.Marker(
                    location=[lat, lng],
                    popup=folium.Popup(popup_html, max_width=280),
                    tooltip=cam['name'],
                    icon=folium.Icon(color=color, icon=icon_name, prefix='fa'),
                ).add_to(fmap)

            st_folium(fmap, width=None, height=650, returned_objects=[], key="main_map")

            st.markdown(f"""
            <div style="background: {SURFACE2}; padding: 10px 14px; border-radius: 6px; margin-top: 10px;">
                <b>מקרא:</b>
                <span style="margin: 0 16px; color: {ACCENT};">🟢 תקינה</span>
                <span style="margin: 0 16px; color: {AMBER};">🟠 אירוע ב-24 שעות</span>
                <span style="color: {RED};">🔴 תקולה</span>
            </div>
            """, unsafe_allow_html=True)

        if unpositioned:
            with st.expander(f"📍 {len(unpositioned)} מצלמות ללא מיקום"):
                data = [{"שם": c['name'], "אזור": c.get('area', '') or '-'} for c in unpositioned]
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    with area_tab:
        st.markdown("### 📍 עריכת קואורדינטות אזורים")
        st.caption("הזן קואורדינטה מרכזית לכל אזור. כל המצלמות באזור יופיעו סביב הנקודה עם פיזור קטן.")

        areas = db.get_all_areas()
        st.caption("מרכז טירת כרמל: **32.7602, 34.9702** (העתק והדבק כנקודת עוגן)")

        with st.form("area_coords_form"):
            for area in areas:
                curr = area_coords.get(area, {})
                cols = st.columns([2, 1, 1])
                cols[0].markdown(f"**{area}**")
                cols[1].text_input(
                    "קו רוחב",
                    value=str(curr.get('lat', '')) if curr.get('lat') else "",
                    placeholder="32.760000",
                    key=f"area_lat_{area}",
                    label_visibility="collapsed",
                )
                cols[2].text_input(
                    "קו אורך",
                    value=str(curr.get('lng', '')) if curr.get('lng') else "",
                    placeholder="34.970000",
                    key=f"area_lng_{area}",
                    label_visibility="collapsed",
                )

            if st.form_submit_button("💾 שמור קואורדינטות אזורים", type="primary"):
                new_coords = {}
                errors = []
                for area in areas:
                    lat_str = st.session_state.get(f"area_lat_{area}", "").strip()
                    lng_str = st.session_state.get(f"area_lng_{area}", "").strip()
                    if not lat_str and not lng_str:
                        continue
                    try:
                        new_coords[area] = {'lat': float(lat_str), 'lng': float(lng_str)}
                    except ValueError:
                        errors.append(area)
                if errors:
                    st.error(f"שגיאה באזורים: {', '.join(errors)}")
                else:
                    _save_area_coords(new_coords)
                    st.success(f"נשמרו קואורדינטות ל-{len(new_coords)} אזורים")
                    st.rerun()

    with csv_tab:
        st.markdown("### 📤 יבוא קואורדינטות מקובץ CSV")
        st.caption("פורמט: `camera_number,latitude,longitude` (למשל: `40,32.7530,34.9689`)")

        uploaded = st.file_uploader("העלה CSV", type=['csv'], key="coord_csv")
        if uploaded is not None:
            try:
                df_upload = pd.read_csv(uploaded)
                if not all(col in df_upload.columns for col in ['camera_number', 'latitude', 'longitude']):
                    st.error("הקובץ חייב לכלול עמודות: camera_number, latitude, longitude")
                else:
                    st.write(f"נקרא: **{len(df_upload)}** שורות")
                    st.dataframe(df_upload.head(10), use_container_width=True)

                    if st.button("✅ אשר ייבא", type="primary"):
                        cams = db.get_all_cameras()
                        updated = 0
                        not_found = []
                        for _, row in df_upload.iterrows():
                            try:
                                num = int(row['camera_number'])
                                lat = float(row['latitude'])
                                lng = float(row['longitude'])
                                prefix = f"#{num} - "
                                matching = [c for c in cams if c['name'].startswith(prefix)]
                                if matching:
                                    db.update_camera_location(matching[0]['id'], lat, lng)
                                    updated += 1
                                else:
                                    not_found.append(num)
                            except (ValueError, TypeError):
                                pass
                        st.success(f"עודכנו {updated} מצלמות")
                        if not_found:
                            st.warning(f"לא נמצאו במערכת: {not_found[:20]}{'...' if len(not_found) > 20 else ''}")
                        st.rerun()
            except Exception as e:
                st.error(f"שגיאה בקריאת הקובץ: {e}")

        st.markdown("---")
        st.markdown("**דוגמה לקובץ CSV:**")
        st.code(
            "camera_number,latitude,longitude\n"
            "40,32.7530,34.9689\n"
            "41,32.7531,34.9690\n"
            "48,32.7602,34.9702",
            language="csv",
        )


# ============ עמוד: מצלמות ============
elif page == "מצלמות":
    st.header("ניהול מצלמות")

    tab1, tab2, tab3 = st.tabs(["רשימה", "הוספה", "יבוא מרובה"])

    with tab1:
        cams = db.get_all_cameras()
        central_count = sum(1 for c in cams if c['is_central'])
        st.markdown(f"סה\"כ: **{len(cams)}** · קבועות: **{central_count}** · מתחלפות: **{len(cams) - central_count}**")

        mc1, mc2 = st.columns([1, 1])
        search = mc1.text_input("🔍 חיפוש", "")
        all_areas = db.get_all_areas()
        selected_manage_area = mc2.selectbox(
            "🗂️ סנן לפי אזור",
            ["כל האזורים"] + all_areas,
        )
        filter_type = st.radio(
            "סנן:",
            ["הכל", "קבועות", "מתחלפות"],
            horizontal=True,
        )

        filtered = cams
        if search:
            filtered = [c for c in filtered if search.lower() in c['name'].lower()]
        if selected_manage_area != "כל האזורים":
            filtered = [c for c in filtered if c.get('area') == selected_manage_area]
        if filter_type == "קבועות":
            filtered = [c for c in filtered if c['is_central']]
        elif filter_type == "מתחלפות":
            filtered = [c for c in filtered if not c['is_central']]

        st.caption(f"מציג {len(filtered)}")

        if filtered:
            faulty_ids = db.get_faulty_camera_ids()
            for cam in filtered:
                is_faulty = cam['id'] in faulty_ids
                cols = st.columns([3, 2, 2, 1])
                indicator = f' <span style="color:{RED}; font-size: 0.85rem;">⚠ תקולה</span>' if is_faulty else ''
                cols[0].markdown(f'<span class="camera-name">{cam["name"]}</span>{indicator}', unsafe_allow_html=True)
                area_display = cam.get('area', '') or '-'
                policy_display = cam.get('scan_policy', '') or 'בסבב'
                try:
                    from scan_policies import POLICY_DESCRIPTIONS
                    policy_text = POLICY_DESCRIPTIONS.get(policy_display, policy_display) if policy_display != 'בסבב' else 'בסבב'
                except ImportError:
                    policy_text = policy_display
                cols[1].markdown(
                    f'<span style="color:{MUTED}; font-size:0.8rem;">🗂️ {area_display}<br>⏰ {policy_text}</span>',
                    unsafe_allow_html=True,
                )
                new_central = cols[2].checkbox(
                    "בכל שעה",
                    value=bool(cam['is_central']),
                    key=f"central_{cam['id']}",
                    help="סמן כדי לגרום למצלמה זו להיסרק בכל שעה (מעקף למדיניות)",
                )
                if new_central != bool(cam['is_central']):
                    db.update_camera(cam['id'], is_central=new_central)
                    st.rerun()
                if cols[3].button("🗑️", key=f"del_{cam['id']}"):
                    db.delete_camera(cam['id'])
                    st.rerun()

                has_own_coords = cam.get('latitude') is not None and cam.get('longitude') is not None
                if has_own_coords:
                    st.caption(f"📍 {cam['latitude']:.5f}, {cam['longitude']:.5f}")

    with tab2:
        with st.form("add_camera"):
            name = st.text_input("שם המצלמה")
            is_central = st.checkbox("מצלמה קבועה (נסרקת בכל שעה)")
            if st.form_submit_button("הוסף", type="primary"):
                if name:
                    if db.add_camera(name.strip(), is_central):
                        st.success(f"נוסף: {name}")
                        st.rerun()
                    else:
                        st.error("שם כפול")

    with tab3:
        bulk = st.text_area("הכנס שמות (שם בכל שורה)", height=250)
        bulk_central = st.checkbox("הכל כקבועות")
        if st.button("ייבא", type="primary"):
            names = [n for n in bulk.split("\n") if n.strip()]
            if names:
                added = db.bulk_add_cameras(names, bulk_central)
                st.success(f"נוספו {added}/{len(names)}")
                st.rerun()


# ============ עמוד: היסטוריה ============
elif page == "היסטוריה":
    st.header("היסטוריית סריקות")

    c1, c2 = st.columns(2)
    start_date = c1.date_input("מתאריך", value=date.today() - timedelta(days=1))
    end_date = c2.date_input("עד תאריך", value=date.today())

    start_k = f"{start_date} 00:00"
    end_k = f"{end_date} 23:00"
    scans = db.get_scans_in_range(start_k, end_k)

    if scans:
        filter_status = st.radio(
            "סנן:",
            ["הכל", "רק תקינות", "רק תקלות"],
            horizontal=True,
        )
        if filter_status == "רק תקינות":
            scans = [s for s in scans if (s.get('status') or 'ok') == 'ok']
        elif filter_status == "רק תקלות":
            scans = [s for s in scans if s.get('status') == 'issue']

        data = []
        for s in scans:
            status = s.get('status') or 'ok'
            data.append({
                "שעה מתוזמנת": s['scheduled_hour'],
                "שם המצלמה": s['camera_name'],
                "בוצע בפועל": s['scanned_at'],
                "בוצע ע\"י": s['scanned_by'] or "-",
                "סטטוס": "⚠️ תקלה" if status == 'issue' else "✅ תקין",
                "פירוט": s.get('event_details') or "-",
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 הורד CSV", csv, "history.csv", "text/csv")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**סיכום ע\"י נציג**")
            by_scanner = df.groupby("בוצע ע\"י").size().reset_index(name="מס' סריקות")
            st.dataframe(by_scanner, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("**סיכום לפי סטטוס**")
            by_status = df.groupby("סטטוס").size().reset_index(name="מס' סריקות")
            st.dataframe(by_status, use_container_width=True, hide_index=True)
    else:
        st.info("אין נתונים בטווח")


# ============ עמוד: הגדרות ============
elif page == "הגדרות":
    st.header("הגדרות")

    st.markdown("### הגדרות סריקה")
    with st.form("scan_settings"):
        rotating_count = st.number_input(
            "מקסימום סריקות בשעה (סה\"כ)",
            min_value=1, max_value=200,
            value=int(db.get_setting('rotating_count', '30')),
            help="סה\"כ מצלמות שיוצגו לסריקה בכל שעה. מצלמות חובה נכללות במניין - הסבב מתמלא מהיתר.",
        )
        grace = st.number_input(
            "זמן חסד להתראה (דקות)",
            min_value=0, max_value=59,
            value=int(db.get_setting('alert_grace_minutes', '15')),
        )
        if st.form_submit_button("שמור", type="primary"):
            db.set_setting('rotating_count', rotating_count)
            db.set_setting('alert_grace_minutes', grace)
            st.success("נשמר")

    st.markdown("### שעות משמרות")
    with st.form("shift_settings"):
        c1, c2, c3 = st.columns(3)
        m_start = c1.number_input("בוקר", 0, 23, int(db.get_setting('shift_morning_start', '7')))
        e_start = c2.number_input("ערב", 0, 23, int(db.get_setting('shift_evening_start', '15')))
        n_start = c3.number_input("לילה", 0, 23, int(db.get_setting('shift_night_start', '23')))
        if st.form_submit_button("שמור משמרות", type="primary"):
            db.set_setting('shift_morning_start', m_start)
            db.set_setting('shift_evening_start', e_start)
            db.set_setting('shift_night_start', n_start)
            st.success("נשמר")

    st.markdown("### רענון תצוגה")
    auto_refresh = st.checkbox(
        "רענן את הדף אוטומטית כל 30 שניות",
        value=st.session_state.get('auto_refresh', False),
        help="מומלץ למי שיושב מול המסך כל המשמרת - השעה והמצלמות יתעדכנו לבד",
    )
    st.session_state['auto_refresh'] = auto_refresh

    st.markdown("### ייצוא")
    cams = db.get_all_cameras()
    if cams:
        df = pd.DataFrame(cams)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 הורד רשימת מצלמות", csv, "cameras.csv", "text/csv")

    with st.expander("🔧 כלי עזר"):
        st.caption("שימושי בהתחלה או לצורך בדיקות")

        st.markdown("**מצלמות דמה**")
        current_count = len(db.get_all_cameras())
        if current_count >= 200:
            st.info(f"כבר יש {current_count} מצלמות במערכת")
        else:
            if st.button("טען 200 מצלמות דמה"):
                try:
                    import seed_data
                    result = seed_data.seed_demo_data()
                    st.success(f"נוספו {result['central_added']} קבועות + {result['rotating_added']} מתחלפות")
                    st.rerun()
                except ImportError:
                    st.error("קובץ seed_data.py לא נמצא")

        st.markdown("---")

        st.markdown(f"""
            <div style="background-color: {RED}22; border-right: 3px solid {RED};
                        border-radius: 8px; padding: 12px 16px; margin: 8px 0;">
                <div style="font-weight: 500; color: {TEXT};">⚠️ אזור סכנה - איפוס נתונים</div>
                <div style="font-size: 0.85rem; color: {MUTED}; margin-top: 4px;">
                    מיועד לשלב הבדיקות. פעולות אלה בלתי הפיכות!
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("**איפוס סריקות ותקלות** (משאיר מצלמות)")
        confirm_activity = st.checkbox(
            "אני מאשר מחיקת כל הסריקות והתקלות",
            key="confirm_reset_activity",
        )
        if st.button(
            "🧹 מחק סריקות + תקלות",
            disabled=not confirm_activity,
            key="reset_activity_btn",
        ):
            db.reset_scans_and_faults()
            st.session_state.pop("confirm_reset_activity", None)
            st.success("כל הסריקות והתקלות נמחקו. המצלמות נשארו.")
            st.rerun()

        st.markdown("")
        st.markdown("**איפוס מלא** (מוחק גם מצלמות)")
        confirm_full = st.checkbox(
            "אני מאשר מחיקת הכל כולל המצלמות",
            key="confirm_reset_full",
        )
        if st.button(
            "💥 מחק הכל",
            disabled=not confirm_full,
            key="reset_full_btn",
        ):
            db.reset_all_data()
            st.session_state.pop("confirm_reset_full", None)
            st.success("הכל נמחק. אפשר לטעון שוב 200 מצלמות דמה מלמעלה.")
            st.rerun()

        st.markdown("---")
        st.markdown("---")
        st.markdown("**רשימת נציגים אמיתיים**")
        st.caption("מסיר את 'מוקדן 1-4' הזמניים ומכניס את השמות האמיתיים (12 נציגים)")
        confirm_ops = st.checkbox(
            "אני מאשר החלפת רשימת המוקדנים",
            key="confirm_refresh_ops",
        )
        if st.button(
            "🔄 עדכן רשימת נציגים",
            disabled=not confirm_ops,
            key="refresh_ops_btn",
        ):
            count = db.refresh_operators()
            st.session_state.pop("confirm_refresh_ops", None)
            st.success(f"נוספו {count} נציגים אמיתיים. המוקדנים הזמניים הוסרו.")
            st.rerun()

        st.markdown("---")
        st.markdown("**מצלמות אמיתיות - טירת כרמל (191 מצלמות ב-35 אזורים)**")
        current_count2 = len(db.get_all_cameras())
        confirm_real = st.checkbox(
            "אני מאשר החלפת כל המצלמות במצלמות האמיתיות של טירת כרמל",
            key="confirm_load_real",
            help=f"יש כרגע {current_count2} מצלמות - כולן יוחלפו + כל הסריקות והתקלות ימחקו",
        )
        if st.button(
            "🔄 טען 191 מצלמות אמיתיות",
            disabled=not confirm_real,
            key="load_real_btn",
        ):
            try:
                import real_cameras
                db.reset_all_data()
                added = db.bulk_add_cameras_structured(
                    real_cameras.get_camera_data_for_import()
                )
                st.session_state.pop("confirm_load_real", None)
                st.success(f"הוחלפו במערכת {added} מצלמות אמיתיות ב-{len(db.get_all_areas())} אזורים")
                st.rerun()
            except ImportError:
                st.error("קובץ real_cameras.py לא נמצא בשרת - וודא שהעלית אותו")


# ============ רענון אוטומטי (מופעל בכל עמוד אם נבחר בהגדרות) ============
if st.session_state.get('auto_refresh', False):
    st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)
