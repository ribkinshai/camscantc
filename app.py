"""
מערכת מעקב סריקות מצלמות - עיצוב מחודש
Camera Scan Tracking System - Redesigned
"""
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import json

# מרכז טירת כרמל לתצוגת מפה
TIRAT_CARMEL_CENTER = [32.7602, 34.9702]


def _get_area_coords():
    """קואורדינטות אזורים - נשמרות כ-JSON בהגדרות"""
    raw = db.get_setting('area_coords', '{}')
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _save_area_coords(coords_dict):
    db.set_setting('area_coords', json.dumps(coords_dict, ensure_ascii=False))


def _camera_map_position(cam, area_coords):
    """מיקום מצלמה במפה: קואורדינטה משלה ← קואורדינטת אזור + פיזור ← None"""
    if cam.get('latitude') is not None and cam.get('longitude') is not None:
        return float(cam['latitude']), float(cam['longitude'])
    area = cam.get('area', '')
    if area in area_coords:
        base = area_coords[area]
        # פיזור דטרמיניסטי סביב מרכז האזור (עד ~15 מטר)
        cam_id = cam['id']
        lat_offset = ((cam_id * 7) % 30 - 15) / 100000.0
        lng_offset = ((cam_id * 13) % 30 - 15) / 100000.0
        return float(base['lat']) + lat_offset, float(base['lng']) + lng_offset
    return None
import database as db
import scheduler as sch


def now_il():
    """שעה נוכחית לפי שעון ישראל"""
    return datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None)


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
    st.session_state['current_page'] = "סריקה שוטפת"

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

    /* Flip sidebar to right side */
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
    [data-testid="stMetricLabel"] {{
        color: {MUTED} !important;
        font-size: 0.85rem !important;
    }}
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
    .top-item .label {{
        font-size: 0.75rem;
        color: {MUTED};
        margin-bottom: 4px;
    }}
    .top-item .value {{
        font-size: 1.15rem;
        font-weight: 500;
        color: {TEXT};
    }}

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

    .camera-name {{
        font-size: 0.95rem;
        font-weight: 500;
        color: {TEXT};
    }}
    .camera-meta {{
        font-size: 0.8rem;
        color: {MUTED};
        margin-top: 2px;
    }}
    .event-note {{
        font-size: 0.8rem;
        color: {AMBER};
        font-style: italic;
        margin-top: 3px;
    }}
</style>
""", unsafe_allow_html=True)
# ============ הגנת סיסמא ============
def check_password():
    """שער סיסמא. אם לא מאומת - מציג מסך כניסה ועוצר."""
    if st.session_state.get('authenticated'):
        return

    # מסך כניסה
    st.markdown(f"""
    <div style="max-width: 420px; margin: 80px auto 20px; text-align: center;">
        <div style="font-size: 3.5rem; margin-bottom: 12px;">🎥</div>
        <h1 style="color: {TEXT}; margin: 0; font-size: 1.8rem;">מוקד רואה</h1>
        <p style="color: {MUTED}; margin-top: 8px; font-size: 0.95rem;">
            מערכת מעקב סריקות מצלמות
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login_form"):
            st.markdown(f"**🔒 הזן סיסמא כדי להיכנס**")
            password = st.text_input(
                "סיסמא",
                type="password",
                placeholder="הזן סיסמא כאן",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                "כניסה",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                expected = None
                try:
                    expected = st.secrets.get("APP_PASSWORD")
                except Exception:
                    pass

                if not expected:
                    st.error("סיסמת המערכת לא הוגדרה. פנה למנהל המערכת.")
                    st.stop()

                if password == expected:
                    st.session_state['authenticated'] = True
                    st.rerun()
                else:
                    st.error("סיסמא שגויה")

    st.stop()


check_password()

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
    if c1.button(
        "🌙 כהה",
        use_container_width=True,
        type="primary" if is_dark else "secondary",
    ):
        st.session_state['theme'] = 'dark'
        st.rerun()
    if c2.button(
        "☀️ בהיר",
        use_container_width=True,
        type="primary" if not is_dark else "secondary",
    ):
        st.session_state['theme'] = 'light'
        st.rerun()

    st.markdown("---")

    _nav_button("סריקה שוטפת", "✅ סריקה שוטפת")
    _nav_button("לוח בקרה", "📊 לוח בקרה")
    _nav_button("תקלות", "⚠️ תקלות")
    _nav_button("מפה", "🗺️ מפה")

    with st.expander("⚙️ ניהול"):
        _nav_button("מצלמות", "🎥 מצלמות")
        _nav_button("היסטוריה", "📈 היסטוריה")
        _nav_button("הגדרות", "⚙️ הגדרות")

    now = now_il()
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
    <div style="font-size: 0.85rem; color: {MUTED}; line-height: 1.7;
                direction: rtl; text-align: right;">
        <div>
            <b style="color:{TEXT};">🕐 <span id="clk-time">--:--:--</span></b>
            · <span id="clk-date">--/--/----</span>
        </div>
        <div>משמרת: <b style="color:{TEXT};">{sch.get_shift_name(now)}</b></div>
    </div>
    <script>
    (function() {{
        function updateClock() {{
            var now = new Date();
            var timeStr = now.toLocaleTimeString('en-GB', {{
                timeZone: 'Asia/Jerusalem',
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            }});
            var dateStr = now.toLocaleDateString('en-GB', {{
                timeZone: 'Asia/Jerusalem'
            }});
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
    st.sidebar.markdown("")
if st.sidebar.button("🔒 יציאה מהמערכת", use_container_width=True, key="logout_btn"):
    st.session_state.pop('authenticated', None)
    st.session_state.pop('scanner_name', None)
    st.rerun()

page = st.session_state['current_page']
now = now_il()
current_hour = now.replace(minute=0, second=0, microsecond=0)
current_hour_key = sch.hour_key(current_hour)


# ============ עמוד: סריקה שוטפת ============
if page == "סריקה שוטפת":

    # ---- כרטיס נציג פעיל ----
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
                        display: flex; align-items: center; gap: 14px;
                        margin-bottom: 12px;">
                <span style="font-size: 1.6rem;">👤</span>
                <div>
                    <div style="font-size: 0.75rem; color: {MUTED};">נציג פעיל במשמרת</div>
                    <div style="font-size: 1.15rem; font-weight: 500; color: {TEXT};">
                        {scanner_name}
                    </div>
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
                reason = st.text_area(
                    "סיבה", height=120,
                    placeholder="הקלד כאן את הסיבה...",
                    label_visibility="collapsed",
                )
                bc1, bc2 = st.columns(2)
                save = bc1.form_submit_button("💾 שמור", type="primary", use_container_width=True)
                cancel = bc2.form_submit_button("↩️ ביטול", use_container_width=True)

                if save:
                    if not reason.strip():
                        st.error("יש למלא סיבה")
                    else:
                        db.mark_scan(
                            cam_id, current_hour_key,
                            st.session_state.get('scanner_name', ''),
                            status='issue', event_details=reason.strip(),
                        )
                        st.session_state.pop('issue_cam_id', None)
                        st.session_state.pop('issue_cam_name', None)
                        st.rerun()
                if cancel:
                    st.session_state.pop('issue_cam_id', None)
                    st.session_state.pop('issue_cam_name', None)
                    st.rerun()

        st.stop()

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
    search = fc1.text_input(
        "🔍 חיפוש מצלמה", "",
        placeholder="הקלד שם, מספר או חלק ממנו...",
    )
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
            time_str = info['scanned_at'][11:16] if info['scanned_at'] else ''
            if status == 'issue':
                dot_class = 'issue'
                meta = f"לא נסרק · {time_str}"
            else:
                dot_class = 'ok'
                meta = f"נסרק · {time_str}"
            if by:
                meta += f" · {by}"

            cols = st.columns([5, 1])
            cols[0].markdown(f"""
                <div style="padding: 4px 0;">
                    <span class="status-dot {dot_class}"></span>
                    <span class="camera-name">{cam['name']}</span>
                    <div class="camera-meta">{meta}</div>
                </div>
            """, unsafe_allow_html=True)
            if cols[1].button("בטל", key=f"u_{prefix}_{cam['id']}", use_container_width=True):
                db.unmark_scan(cam['id'], current_hour_key)
                st.rerun()
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

    st.markdown("---")
    if not search.strip():
        if st.button("סמן את כל הנותרות כנסרקו", type="secondary"):
            for cam in central + rotating:
                if cam['id'] not in scanned_now:
                    db.mark_scan(cam['id'], current_hour_key, scanner_name, status='ok')
            st.rerun()


# ============ עמוד: לוח בקרה (כולל לו"ז) ============
elif page == "לוח בקרה":
    st.header("לוח בקרה")

    all_cameras = db.get_all_cameras()
    central_cameras = db.get_central_cameras()
    active_faults = db.get_active_faults()
    missed = sch.get_missed_scans(now, lookback_hours=8)

    start_key = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:00")
    end_key = now.strftime("%Y-%m-%d %H:00")
    recent_issues = db.get_issue_scans_in_range(start_key, end_key)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("מצלמות פעילות", len(all_cameras))
    m2.metric("קבועות", len(central_cameras))
    m3.metric("תקולות", len(active_faults))
    m4.metric("סריקות חסרות (8ש')", len(missed))
    m5.metric("אירועים (24ש')", len(recent_issues))

    if missed:
        with st.expander(f"⚠️ פירוט {len(missed)} סריקות חסרות"):
            data = []
            for hk, cam in missed:
                data.append({
                    "שעה": hk,
                    "שם המצלמה": cam['name'],
                    "סוג": "קבועה" if cam['is_central'] else "מתחלפת",
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    if recent_issues:
        st.markdown("### אירועים אחרונים בסריקות")
        data = []
        for s in recent_issues[:10]:
            data.append({
                "שעה": s['scheduled_hour'],
                "שם המצלמה": s['camera_name'],
                "פירוט": s['event_details'] or "-",
                "דווח ע\"י": s['scanned_by'] or "-",
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    if active_faults:
        st.markdown("### מצלמות תקולות")
        data = []
        for f in active_faults:
            data.append({
                "שם המצלמה": f['camera_name'],
                "תאריך ושעת התקלה": f['fault_datetime'],
                "תיאור התקלה": f['description'],
                "דווח ע\"י": f.get('reported_by') or "-",
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    # לו"ז מוטמע
    st.markdown("### לו\"ז - השעות הקרובות")
    hours = st.slider("שעות להצגה", 6, 48, 12)
    schedule = sch.get_upcoming_schedule(now, hours)
    for slot in schedule:
        header = f"🕐 {slot['datetime'].strftime('%d/%m %H:00')} · {slot['shift']} · {len(slot['central']) + len(slot['rotating'])} מצלמות"
        with st.expander(header):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**קבועות ({len(slot['central'])}):**")
                for cam in slot['central']:
                    st.markdown(f"- {cam['name']}")
            with c2:
                st.markdown(f"**מתחלפות ({len(slot['rotating'])}):**")
                for cam in slot['rotating']:
                    st.markdown(f"- {cam['name']}")


# ============ עמוד: מצלמות ============
elif page == "מפה":
    st.header("🗺️ מפת מצלמות טירת כרמל")

    try:
        import folium
        from streamlit_folium import st_folium
    except ImportError:
        st.error(
            "חסרות ספריות מפה. וודא ש-`requirements.txt` מכיל: `folium` ו-`streamlit-folium`, "
            "ואז לחץ Reboot app בסטרימליט."
        )
        st.stop()

    map_tab, area_tab, csv_tab = st.tabs([
        "🗺️ תצוגת מפה",
        "📍 קואורדינטות אזורים",
        "📤 יבוא CSV",
    ])

    all_cams = db.get_all_cameras()
    faulty_ids = db.get_faulty_camera_ids()
    area_coords = _get_area_coords()

    # אירועים ב-24 השעות האחרונות
    recent_start = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:00")
    recent_end = now.strftime("%Y-%m-%d %H:00")
    recent_issues = db.get_issue_scans_in_range(recent_start, recent_end)
    recent_issue_cam_ids = set(i['camera_id'] for i in recent_issues)

    # חישוב מיקומים
    positioned = []
    unpositioned = []
    for cam in all_cams:
        pos = _camera_map_position(cam, area_coords)
        if pos:
            positioned.append((cam, pos))
        else:
            unpositioned.append(cam)

    # ==== טאב מפה ====
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
                "1. עבור לטאב **📍 קואורדינטות אזורים** ← הזן קואורדינטה ל-35 אזורים ← 30 דקות עבודה\n"
                "2. עבור לטאב **📤 יבוא CSV** ← העלה קובץ עם כל המיקומים\n"
                "3. עבור ל**ניהול → מצלמות** ← ערוך מצלמה בודדת"
            )
        else:
            filter_opt = st.radio(
                "הצג:",
                ["הכל", "רק תקינות", "רק תקולות", "רק עם אירועים אחרונים"],
                horizontal=True,
                key="map_filter",
            )

            display = positioned
            if filter_opt == "רק תקינות":
                display = [(c, p) for c, p in positioned
                           if c['id'] not in faulty_ids and c['id'] not in recent_issue_cam_ids]
            elif filter_opt == "רק תקולות":
                display = [(c, p) for c, p in positioned if c['id'] in faulty_ids]
            elif filter_opt == "רק עם אירועים אחרונים":
                display = [(c, p) for c, p in positioned if c['id'] in recent_issue_cam_ids]

            fmap = folium.Map(
                location=TIRAT_CARMEL_CENTER,
                zoom_start=14,
                tiles='OpenStreetMap',
            )

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

    # ==== טאב אזורים ====
    with area_tab:
        st.markdown("### 📍 עריכת קואורדינטות אזורים")
        st.caption("הזן קואורדינטה מרכזית לכל אזור. כל המצלמות באזור יופיעו סביב הנקודה עם פיזור קטן.")

        areas = db.get_all_areas()
        st.caption(f"מרכז טירת כרמל: **32.7602, 34.9702** (העתק והדבק כנקודת עוגן)")

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

    # ==== טאב CSV ====
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

                # הצגת סטטוס מיקום מתחת לשם (אם רלוונטי)
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

        # ---- טעינת מצלמות דמה ----
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

        # ---- אזור סכנה - איפוס ----
        st.markdown(f"""
            <div style="background-color: {RED}22; border-right: 3px solid {RED};
                        border-radius: 8px; padding: 12px 16px; margin: 8px 0;">
                <div style="font-weight: 500; color: {TEXT};">⚠️ אזור סכנה - איפוס נתונים</div>
                <div style="font-size: 0.85rem; color: {MUTED}; margin-top: 4px;">
                    מיועד לשלב הבדיקות. פעולות אלה בלתי הפיכות!
                </div>
            </div>
        """, unsafe_allow_html=True)

        # איפוס נתוני פעילות
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

        # ---- טעינת מצלמות אמיתיות ----
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
