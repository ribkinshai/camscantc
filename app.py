"""
מערכת מעקב סריקות מצלמות - מוקד 106 טירת כרמל
"""
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo
import json
import re

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


TIRAT_CARMEL_CENTER = [32.7602, 34.9702]


def now_il():
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


if is_dark:
    BG = '#0f1419'; SURFACE = '#1a1f26'; SURFACE2 = '#242b34'
    TEXT = '#e4e7eb'; MUTED = '#94a3b8'; BORDER = '#2d3742'
    ACCENT = '#4ade80'; AMBER = '#fbbf24'; RED = '#f87171'; BTN_FG = '#0f1419'
else:
    BG = '#f8fafc'; SURFACE = '#ffffff'; SURFACE2 = '#f1f5f9'
    TEXT = '#0f172a'; MUTED = '#64748b'; BORDER = '#e2e8f0'
    ACCENT = '#16a34a'; AMBER = '#d97706'; RED = '#dc2626'; BTN_FG = '#ffffff'


st.markdown(f"""
<style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background-color: {BG}; }}
    [data-testid="stSidebar"] {{ background-color: {SURFACE}; }}
    [data-testid="stAppViewContainer"] {{ flex-direction: row-reverse !important; }}
    section[data-testid="stSidebar"] {{ left: auto !important; right: 0 !important; }}
    section[data-testid="stSidebar"][aria-expanded="false"] {{
        margin-left: 0 !important; margin-right: -21rem !important; transform: none !important;
    }}
    [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] {{
        right: 0.5rem !important; left: auto !important;
    }}
    [data-testid="stHeader"] {{ background-color: transparent; }}
    .stMarkdown, p, li, span, label, h1, h2, h3, h4, h5, h6 {{
        color: {TEXT}; direction: rtl; text-align: right;
    }}
    div[data-testid="stMarkdownContainer"] {{ color: {TEXT}; }}
    .stTextInput input, .stTextArea textarea, .stNumberInput input,
    .stDateInput input, .stTimeInput input {{
        background-color: {SURFACE2} !important; color: {TEXT} !important;
        border: 1px solid {BORDER} !important; text-align: right !important; direction: rtl !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: {SURFACE2} !important; color: {TEXT} !important; border-color: {BORDER} !important;
    }}
    .stButton button {{
        background-color: {SURFACE2}; color: {TEXT}; border: 1px solid {BORDER};
        border-radius: 6px; font-weight: 500;
    }}
    .stButton button[kind="primary"] {{
        background-color: {ACCENT} !important; color: {BTN_FG} !important; border: 1px solid {ACCENT} !important;
    }}
    .stButton button[kind="tertiary"] {{
        background-color: {RED} !important; color: white !important; border: 1px solid {RED} !important;
    }}
    .stAlert {{ direction: rtl; text-align: right; border-radius: 8px; }}
    .stProgress > div > div > div {{ background-color: {ACCENT} !important; }}
    [data-testid="stMetric"] {{
        background-color: {SURFACE2}; padding: 12px 16px; border-radius: 8px; border: 1px solid {BORDER};
    }}
    [data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-size: 0.85rem !important; }}
    [data-testid="stMetricValue"] {{ color: {TEXT} !important; }}
    [data-testid="stExpander"] {{ background-color: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 8px; }}
    [data-testid="stExpander"] summary {{ color: {TEXT}; }}
    .stDataFrame, .stDataFrame table {{ direction: rtl; }}
    .top-bar {{
        display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;
        background-color: {SURFACE2}; border-radius: 10px; padding: 14px 18px;
        margin-bottom: 8px; border: 1px solid {BORDER};
    }}
    .top-item .label {{ font-size: 0.75rem; color: {MUTED}; margin-bottom: 4px; }}
    .top-item .value {{ font-size: 1.15rem; font-weight: 500; color: {TEXT}; }}
    .status-dot {{
        display: inline-block; width: 9px; height: 9px; border-radius: 50%;
        margin-left: 8px; vertical-align: middle;
    }}
    .status-dot.pending {{ background: {MUTED}; }}
    .status-dot.ok {{ background: {ACCENT}; }}
    .status-dot.issue {{ background: {RED}; }}
    .camera-name {{ font-size: 0.95rem; font-weight: 500; color: {TEXT}; }}
    .camera-meta {{ font-size: 0.8rem; color: {MUTED}; margin-top: 2px; }}
</style>
""", unsafe_allow_html=True)

auth.require_login((TEXT, MUTED, BG, SURFACE))


if _HAS_AUTOREFRESH:
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
        _refresh_interval_ms = 15 * 1000
    _refresh_count = st_autorefresh(interval=_refresh_interval_ms, limit=None, key="global_page_refresh")
else:
    _refresh_count = 0


def _nav_button(name, label):
    is_current = st.session_state['current_page'] == name
    if st.button(label, use_container_width=True,
                 type="primary" if is_current else "secondary", key=f"nav_{name}"):
        st.session_state['current_page'] = name
        st.session_state.pop('issue_cam_id', None)
        st.session_state.pop('issue_cam_name', None)
        st.rerun()


with st.sidebar:
    st.markdown("### מוקד רואה")
    c1, c2 = st.columns(2)
    if c1.button("🌙 כהה", use_container_width=True,
                 type="primary" if is_dark else "secondary"):
        st.session_state['theme'] = 'dark'; st.rerun()
    if c2.button("☀️ בהיר", use_container_width=True,
                 type="primary" if not is_dark else "secondary"):
        st.session_state['theme'] = 'light'; st.rerun()
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
    st.markdown(f'<div style="margin-top: 20px; padding-top: 12px; border-top: 1px solid {BORDER};"></div>',
                unsafe_allow_html=True)
    components.html(f"""
    <style>body {{ margin: 0; padding: 0; font-family: sans-serif; }}</style>
    <div style="font-size: 0.85rem; color: {MUTED}; line-height: 1.7; direction: rtl; text-align: right;">
        <div><b style="color:{TEXT};">🕐 <span id="clk-time">--:--:--</span></b>
        · <span id="clk-date">--/--/----</span></div>
        <div>משמרת: <b style="color:{TEXT};">{sch.get_shift_name(_now_temp)}</b></div>
    </div>
    <script>
    (function() {{
        function u() {{
            var n = new Date();
            var t = n.toLocaleTimeString('en-GB', {{timeZone: 'Asia/Jerusalem', hour12: false,
                hour: '2-digit', minute: '2-digit', second: '2-digit'}});
            var d = n.toLocaleDateString('en-GB', {{timeZone: 'Asia/Jerusalem'}});
            var e1 = document.getElementById('clk-time'); if (e1) e1.textContent = t;
            var e2 = document.getElementById('clk-date'); if (e2) e2.textContent = d;
        }}
        u(); setInterval(u, 1000);
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
    auth.logout(); st.rerun()


page = st.session_state['current_page']
now = now_il()
current_hour = now.replace(minute=0, second=0, microsecond=0)
current_hour_key = sch.hour_key(current_hour)


def _get_night_shift_id(dt):
    hour = dt.hour
    if hour >= 23:
        night_date = dt.date()
    elif hour < 7:
        night_date = (dt - timedelta(days=1)).date()
    else:
        return None
    return int(night_date.strftime("%Y%m%d"))


def _ensure_night_comm_slots(shift_id, dt):
    if not shift_id:
        return
    if dt.hour >= 23:
        night_start = dt.date()
    else:
        night_start = (dt - timedelta(days=1)).date()
    base = datetime.combine(night_start, time(23, 30))
    for i in range(15):
        slot_dt = base + timedelta(minutes=30 * i)
        slot_str = slot_dt.strftime("%Y-%m-%d %H:%M")
        db.create_comm_check_slot(shift_id, slot_str)


def render_night_comm_check_widget():
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

    is_dark_w = st.session_state.get('theme', 'light') == 'dark'

    if overdue_slots:
        current_slot = overdue_slots[0]
        try:
            slot_dt = datetime.strptime(current_slot['scheduled_time'], "%Y-%m-%d %H:%M")
            mins_late = int((_now - slot_dt).total_seconds() / 60)
        except (ValueError, TypeError):
            mins_late = 0

        is_urgent = mins_late > 30
        if is_urgent:
            bg = '#7f1d1d' if is_dark_w else '#fee2e2'
            tc = '#fecaca' if is_dark_w else '#7f1d1d'
            bc = '#dc2626'; icon = '🚨'
            title_text = f"בדיקת קשר בפיגור חמור! - {mins_late} דקות באיחור"
        else:
            bg = '#78350f' if is_dark_w else '#fef3c7'
            tc = '#fef3c7' if is_dark_w else '#78350f'
            bc = '#d97706'; icon = '⏰'
            title_text = f"בדיקת קשר ממתינה - {mins_late} דק' מהזמן"

        st.markdown(f"""
            <div style="background-color: {bg}; border: 2px solid {bc};
                        border-radius: 10px; padding: 12px 18px; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.8rem;">{icon}</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 700; font-size: 1.1rem; color: {tc};">{title_text}</div>
                        <div style="font-size: 0.9rem; color: {tc}; opacity: 0.9; margin-top: 3px;">
                            🕐 נדרש בשעה {current_slot['scheduled_time'][11:]} · ✅ בוצעו {completed}/{total}
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if st.button(f"✅ בצע בדיקת קשר של {current_slot['scheduled_time'][11:]} עכשיו",
                     key=f"cc_done_overdue_{current_slot['id']}",
                     type="primary", use_container_width=True):
            db.mark_comm_check(night_shift_id, current_slot['scheduled_time'])
            st.rerun()

    elif upcoming_slots:
        next_slot = upcoming_slots[0]
        try:
            slot_dt = datetime.strptime(next_slot['scheduled_time'], "%Y-%m-%d %H:%M")
            mins_until = int((slot_dt - _now).total_seconds() / 60)
        except (ValueError, TypeError):
            mins_until = 0

        bg = '#1e3a5f' if is_dark_w else '#dbeafe'
        tc = '#dbeafe' if is_dark_w else '#1e3a5f'
        bc = '#3b82f6'

        st.markdown(f"""
            <div style="background-color: {bg}; border: 1px solid {bc};
                        border-radius: 10px; padding: 12px 18px; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.6rem;">🌙</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 700; font-size: 1.05rem; color: {tc};">
                            בדיקת קשר עם פיקוח · הבאה: {next_slot['scheduled_time'][11:]}
                        </div>
                        <div style="font-size: 0.85rem; color: {tc}; opacity: 0.85; margin-top: 3px;">
                            ⏱️ בעוד {mins_until} דקות · ✅ בוצעו {completed}/{total}
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    else:
        bg = '#14532d' if is_dark_w else '#dcfce7'
        tc = '#bbf7d0' if is_dark_w else '#14532d'
        bc = '#16a34a'
        st.markdown(f"""
            <div style="background-color: {bg}; border: 1px solid {bc};
                        border-radius: 10px; padding: 12px 18px; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.6rem;">✅</span>
                    <div style="font-weight: 700; font-size: 1.05rem; color: {tc};">
                        כל בדיקות הקשר של הלילה בוצעו! ({completed}/{total})
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

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
            rows.append({'שעה מתוזמנת': s['scheduled_time'][11:], 'סטטוס': status_txt})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_missed_scans_banner():
    _now_for_check = now_il()
    is_mgr = st.session_state.get('user_role') == 'manager'

    global_dismiss = db.get_setting('banner_dismissed_until', None)
    local_dismiss = st.session_state.get('banner_dismissed_until_local', None)

    if is_mgr:
        effective_cutoff = global_dismiss
    else:
        if global_dismiss and local_dismiss:
            effective_cutoff = max(global_dismiss, local_dismiss)
        else:
            effective_cutoff = global_dismiss or local_dismiss

    try:
        missed = sch.get_missed_scans(_now_for_check, lookback_hours=8)
    except Exception:
        missed = []

    if effective_cutoff:
        missed = [(hk, cam) for hk, cam in missed if hk > effective_cutoff]

    if not missed:
        return

    by_hour = {}
    for hour_key_val, cam in missed:
        if hour_key_val not in by_hour:
            by_hour[hour_key_val] = []
        by_hour[hour_key_val].append(cam)

    total_missed = len(missed)
    unique_cams = len(set(c['id'] for _, c in missed))
    is_dark_l = st.session_state.get('theme', 'light') == 'dark'
    bg = '#7f1d1d' if is_dark_l else '#fee2e2'
    bc = '#dc2626'
    tc = '#fef2f2' if is_dark_l else '#7f1d1d'

    st.markdown(f"""
    <div style="background-color: {bg}; border: 2px solid {bc};
                border-radius: 10px; padding: 16px 20px; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 2rem;">🚨</span>
            <div style="flex: 1;">
                <div style="font-weight: 700; font-size: 1.15rem; color: {tc};">
                    התראה: {total_missed} סריקות לא בוצעו בזמן!
                </div>
                <div style="font-size: 0.9rem; color: {tc}; margin-top: 4px;">
                    {unique_cams} מצלמות שונות · פורש ב-{len(by_hour)} שעות
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    bc1, bc2, bc3 = st.columns([2, 2, 1])
    with bc3:
        current_ts = _now_for_check.strftime("%Y-%m-%d %H:%M:%S")
        if is_mgr:
            if st.button("✅ טופל · נקה לכולם", key="dismiss_missed_global",
                         use_container_width=True, type="primary"):
                db.set_setting('banner_dismissed_until', current_ts)
                st.success("הבנר נוקה לכל המשתמשים"); st.rerun()
        else:
            if st.button("🔕 נקה אצלי", key="dismiss_missed_local", use_container_width=True):
                st.session_state['banner_dismissed_until_local'] = current_ts
                st.rerun()

    with st.expander(f"📋 פירוט כל {total_missed} הסריקות שהוחמצו", expanded=False):
        for hour_key_val in sorted(by_hour.keys(), reverse=True):
            cams_in_hour = by_hour[hour_key_val]
            st.markdown(f"**🕐 {hour_key_val}** · {len(cams_in_hour)} מצלמות")
            for cam in cams_in_hour:
                st.markdown(f"- {cam['name']}  ·  🗂️ {cam.get('area', '') or '-'}")
            st.markdown("")


def render_current_plan_banner():
    _now_for_plan = now_il()
    try:
        active_plans = db.get_active_scan_plans_for_datetime(_now_for_plan)
    except Exception:
        active_plans = []

    if not active_plans:
        return

    all_cams_for_plan = db.get_all_cameras()
    cam_map = {c['id']: c for c in all_cams_for_plan}
    faulty_ids_plan = db.get_faulty_camera_ids()

    current_hour_local = _now_for_plan.replace(minute=0, second=0, microsecond=0)
    current_hour_key_local = sch.hour_key(current_hour_local)
    scanned_now_plan = db.get_scans_for_hour(current_hour_key_local)
    scanner_name_local = st.session_state.get('scanner_name', '') or st.session_state.get('user_name', '')

    is_dark_l = st.session_state.get('theme', 'light') == 'dark'

    for plan in active_plans:
        priority = plan.get('priority', 'medium')
        pc = {'high': '#dc2626', 'medium': '#d97706', 'low': '#16a34a'}
        pi = {'high': '🔴', 'medium': '🟠', 'low': '🟢'}
        bc = pc.get(priority, '#d97706')
        icon = pi.get(priority, '📋')

        bg = '#1e293b' if is_dark_l else '#f0f9ff'
        tc = '#e2e8f0' if is_dark_l else '#0c4a6e'

        cams_in_plan = [cam_map[cid] for cid in plan.get('camera_ids', [])
                        if cid in cam_map and cid not in faulty_ids_plan]
        scanned_count = sum(1 for c in cams_in_plan if c['id'] in scanned_now_plan)
        total_count = len(cams_in_plan)
        progress_pct = int(scanned_count / total_count * 100) if total_count > 0 else 0

        desc_html = ''
        if plan.get('description'):
            desc_html = f'<div style="font-size: 0.9rem; color: {tc}; margin-top: 6px; padding-top: 6px; border-top: 1px solid {bc}44;"><b>📝 דגשים:</b> {plan.get("description")}</div>'

        st.markdown(f"""
        <div style="background-color: {bg}; border: 2px solid {bc};
                    border-radius: 10px; padding: 14px 18px; margin-bottom: 4px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <span style="font-size: 1.5rem;">{icon}📅</span>
                <div style="flex: 1;">
                    <div style="font-weight: 700; font-size: 1.15rem; color: {tc};">
                        תוכנית פעילה: {plan['name']}
                    </div>
                    <div style="font-size: 0.85rem; color: {tc}; opacity: 0.85; margin-top: 3px;">
                        ⏰ {plan.get('start_time', '')} - {plan.get('end_time', '')}  ·
                        📊 בוצעו {scanned_count} מתוך {total_count} ({progress_pct}%)
                    </div>
                </div>
            </div>
            {desc_html}
        </div>
        """, unsafe_allow_html=True)

        if cams_in_plan:
            with st.expander(f"🎥 סמן סריקות של '{plan['name']}' ({scanned_count}/{total_count})",
                              expanded=True):
                for cam in cams_in_plan:
                    is_scanned = cam['id'] in scanned_now_plan
                    if is_scanned:
                        info = scanned_now_plan[cam['id']]
                        status = info.get('status') or 'ok'
                        time_str = info['scanned_at'][11:19] if info['scanned_at'] else ''
                        by = info['scanned_by'] or ''
                        if status == 'issue':
                            badge_bg = RED; badge_label = 'לא נסרק'; dot_class = 'issue'
                        else:
                            badge_bg = ACCENT; badge_label = 'נסרק'; dot_class = 'ok'

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
                                                font-weight: 500; font-size: 0.85rem;">
                                        🕐 {time_str} · {badge_label}
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
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
                        if cols[1].button("✅ נסרק", key=f"plan_ok_{plan['id']}_{cam['id']}",
                                          type="primary", use_container_width=True):
                            db.mark_scan(cam['id'], current_hour_key_local, scanner_name_local, status='ok')
                            st.rerun()
                        if cols[2].button("❌ לא נסרק", key=f"plan_iss_{plan['id']}_{cam['id']}",
                                          type="tertiary", use_container_width=True):
                            st.session_state['issue_cam_id'] = cam['id']
                            st.session_state['issue_cam_name'] = cam['name']
                            st.rerun()
        st.markdown("")


# ============ PAGES ============

if page == "סריקה שוטפת":
    if st.session_state.get('user_role') == 'manager':
        st.warning("⚠️ מסך זה מיועד למוקדנים בלבד.")
        st.info("💡 עבור ל-**📊 לוח בקרה** בסרגל הצד.")
        st.stop()

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
            </div>
        """, unsafe_allow_html=True)

        with st.form("scanner_form"):
            fc1, fc2 = st.columns([3, 1])
            new_name = fc1.text_input("שם הנציג", value=scanner_name,
                                       placeholder="שם מלא", label_visibility="collapsed")
            if fc2.form_submit_button("💾 שמור", type="primary", use_container_width=True):
                if new_name.strip():
                    st.session_state['scanner_name'] = new_name.strip()
                    st.session_state.pop('editing_scanner', None)
                    st.rerun()
                else:
                    st.error("יש להזין שם")

        if scanner_name and edit_mode:
            if st.button("↩️ ביטול", key="cancel_edit_scanner"):
                st.session_state.pop('editing_scanner', None); st.rerun()
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
            st.session_state['editing_scanner'] = True; st.rerun()

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
                selected_cat_label = st.radio("בחר סוג", list(category_options.keys()),
                                                label_visibility="collapsed", key=f"cat_radio_{cam_id}")
                selected_category = category_options[selected_cat_label]

                st.markdown("**📝 פירוט:**")
                reason = st.text_area("סיבה", height=100,
                                       placeholder="הקלד כאן את הסיבה/פירוט האירוע...",
                                       label_visibility="collapsed")
                bc1, bc2 = st.columns(2)
                save = bc1.form_submit_button("💾 שמור", type="primary", use_container_width=True)
                cancel = bc2.form_submit_button("↩️ ביטול", use_container_width=True)

                if save:
                    if not reason.strip():
                        st.error("יש למלא פירוט")
                    else:
                        db.mark_scan(cam_id, current_hour_key,
                                     st.session_state.get('scanner_name', ''),
                                     status='issue', event_details=reason.strip(),
                                     event_category=selected_category)
                        st.session_state.pop('issue_cam_id', None)
                        st.session_state.pop('issue_cam_name', None)
                        st.rerun()
                if cancel:
                    st.session_state.pop('issue_cam_id', None)
                    st.session_state.pop('issue_cam_name', None)
                    st.rerun()
        st.stop()

    render_night_comm_check_widget()
    render_current_plan_banner()
    render_missed_scans_banner()

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
        st.info("אין מצלמות מוגדרות."); st.stop()

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

    def render_row(cam, prefix):
        is_scanned = cam['id'] in scanned_now
        if is_scanned:
            info = scanned_now[cam['id']]
            status = info.get('status') or 'ok'
            by = info['scanned_by'] or ''
            time_str = info['scanned_at'][11:19] if info['scanned_at'] else ''
            date_str = info['scanned_at'][:10] if info['scanned_at'] else ''
            if status == 'issue':
                dot_class = 'issue'; badge_bg = RED; badge_label = 'לא נסרק'
            else:
                dot_class = 'ok'; badge_bg = ACCENT; badge_label = 'נסרק'

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
                                    font-weight: 500; font-size: 0.9rem;">
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
            if cols[1].button("✅ נסרק", key=f"ok_{prefix}_{cam['id']}",
                              type="primary", use_container_width=True):
                db.mark_scan(cam['id'], current_hour_key, scanner_name, status='ok')
                st.rerun()
            if cols[2].button("❌ לא נסרק", key=f"iss_{prefix}_{cam['id']}",
                              type="tertiary", use_container_width=True):
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


elif page == "לוח בקרה":
    _is_manager = st.session_state.get('user_role') == 'manager'

    if _is_manager:
        st.header("📊 דשבורד מנהלת · מוקד 106")
        st.caption(f"תמונת מצב חיה · מחוברת: {st.session_state.get('user_name', '')}")
    else:
        st.header("לוח בקרה")

    render_missed_scans_banner()

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

    all_scans = db.get_scans_in_range(f"{start_date} 00:00", f"{end_date} 23:59")
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
        df_scans['status_label'] = df_scans['status'].apply(
            lambda s: '⚠️ לא נסרק' if s == 'issue' else '✅ נסרק')

        gc1, gc2 = st.columns(2)
        with gc1:
            st.markdown("#### 📊 סריקות לפי שעה")
            hourly = df_scans.groupby(['hour', 'status_label']).size().reset_index(name='count')
            if len(hourly) > 0:
                fig = px.bar(hourly, x='hour', y='count', color='status_label',
                             labels={'hour': 'שעה', 'count': 'מספר', 'status_label': 'סטטוס'},
                             color_discrete_map={'⚠️ לא נסרק': RED, '✅ נסרק': ACCENT},
                             height=320)
                fig.update_layout(xaxis=dict(tickmode='linear', dtick=1),
                                  plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                  font=dict(color=TEXT),
                                  legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
                                  margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with gc2:
            st.markdown("#### 🥧 חלוקת סטטוס")
            status_counts = df_scans['status_label'].value_counts().reset_index()
            status_counts.columns = ['סטטוס', 'מספר']
            fig = px.pie(status_counts, names='סטטוס', values='מספר', color='סטטוס',
                         color_discrete_map={'⚠️ לא נסרק': RED, '✅ נסרק': ACCENT},
                         hole=0.4, height=320)
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                              font=dict(color=TEXT),
                              legend=dict(orientation='h', yanchor='bottom', y=-0.1, x=0.5,
                                          xanchor='center'),
                              margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        st.markdown("---")
        st.markdown("#### 👥 ביצועים לפי נציג")
        df_scans['scanned_by'] = df_scans['scanned_by'].fillna('לא ידוע').replace('', 'לא ידוע')
        by_scanner = df_scans.groupby('scanned_by').agg(
            total=('id', 'count'),
            ok=('status', lambda s: (s != 'issue').sum()),
            issues=('status', lambda s: (s == 'issue').sum()),
        ).reset_index()
        by_scanner['אחוז'] = (by_scanner['ok'] / by_scanner['total'] * 100).round(1).astype(str) + '%'
        by_scanner_disp = by_scanner.copy()
        by_scanner_disp.columns = ['שם נציג', 'סה"כ סריקות', 'תקינות', 'לא תקינות', 'אחוז תקינות']
        st.dataframe(by_scanner_disp.sort_values('סה"כ סריקות', ascending=False),
                     use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🏆 דירוג נציגים - מספר סריקות")
        rank_scanners = by_scanner.sort_values('total', ascending=True).tail(15)
        if not rank_scanners.empty:
            fig_s = px.bar(rank_scanners, y='scanned_by', x='total', orientation='h', text='total',
                           labels={'scanned_by': 'נציג', 'total': 'סה"כ'},
                           color='total', color_continuous_scale='Blues',
                           height=max(320, len(rank_scanners) * 32))
            fig_s.update_traces(textposition='outside')
            fig_s.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color=TEXT), margin=dict(l=20, r=40, t=20, b=20),
                                coloraxis_showscale=False)
            st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

        if issue_count > 0:
            st.markdown("---")
            st.markdown("#### 🎯 נציגים שזיהו הכי הרבה אירועים")
            top_det = by_scanner[by_scanner['issues'] > 0].sort_values('issues', ascending=True).tail(15)
            if not top_det.empty:
                fig_d = px.bar(top_det, y='scanned_by', x='issues', orientation='h', text='issues',
                               labels={'scanned_by': 'נציג', 'issues': 'אירועים'},
                               color='issues', color_continuous_scale='Reds',
                               height=max(320, len(top_det) * 32))
                fig_d.update_traces(textposition='outside')
                fig_d.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color=TEXT), margin=dict(l=20, r=40, t=20, b=20),
                                    coloraxis_showscale=False)
                st.plotly_chart(fig_d, use_container_width=True, config={'displayModeBar': False})

            st.markdown("---")
            st.markdown("#### 🔥 מצלמות עם הכי הרבה אירועים")
            df_iss = pd.DataFrame(all_issues_scans)
            top_c = df_iss.groupby('camera_name').size().reset_index(name='count').sort_values('count', ascending=True).tail(15)
            if not top_c.empty:
                fig_c = px.bar(top_c, y='camera_name', x='count', orientation='h', text='count',
                               labels={'camera_name': 'מצלמה', 'count': 'אירועים'},
                               color='count', color_continuous_scale='Reds',
                               height=max(320, len(top_c) * 32))
                fig_c.update_traces(textposition='outside')
                fig_c.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color=TEXT), margin=dict(l=20, r=40, t=20, b=20),
                                    coloraxis_showscale=False)
                st.plotly_chart(fig_c, use_container_width=True, config={'displayModeBar': False})

    if all_issues_scans:
        st.markdown("---")
        st.markdown("#### 🛡️ סיווג אירועים")

        sec_kw = ['אלימות', 'ונדליזם', 'קטטה', 'פלילי', 'התקהלות', 'רכב חשוד', 'חשוד',
                  'פריצה', 'גניבה', 'שוטטות', 'תגרה', 'סכין', 'נשק', 'איום', 'תקיפה', 'שוד']
        dmp_kw = ['השלכ', 'פסולת', 'גזם', 'גרוטא', 'ניקיון', 'זבל', 'אשפה', 'לכלוך',
                  'שקיות', 'ריהוט', 'שאריות']
        sfy_kw = ['בטיחות', 'בור', 'תאורה', 'מפגע', 'סכנה', 'סכן', 'שבור', 'שבורה',
                  'חסום', 'תקלת חשמל', 'עמוד', 'שלט']

        def cat_ev(s):
            ex = s.get('event_category')
            if ex == 'security': return 'בטחון'
            if ex == 'dumping': return 'גזם/גרוטאות'
            if ex == 'safety': return 'בטיחות'
            if ex == 'other': return 'אחר'
            t = s.get('event_details', '')
            if not t or str(t).strip() == '-':
                return 'ללא פירוט'
            ts = str(t).lower()
            for k in sec_kw:
                if k in ts: return 'בטחון'
            for k in dmp_kw:
                if k in ts: return 'גזם/גרוטאות'
            for k in sfy_kw:
                if k in ts: return 'בטיחות'
            return 'אחר'

        cats = []
        for s in all_issues_scans:
            it = dict(s)
            it['category'] = cat_ev(s)
            cats.append(it)

        df_c = pd.DataFrame(cats)
        counts = df_c['category'].value_counts()

        cm1, cm2, cm3, cm4 = st.columns(4)
        cm1.metric("🛡️ אירועי בטחון", int(counts.get('בטחון', 0)))
        cm2.metric("🗑️ גזם וגרוטאות", int(counts.get('גזם/גרוטאות', 0)))
        cm3.metric("⚠️ מפגעי בטיחות", int(counts.get('בטיחות', 0)))
        cm4.metric("❓ אחר", int(counts.get('אחר', 0)) + int(counts.get('ללא פירוט', 0)))

        col_map = {'בטחון': '#dc2626', 'גזם/גרוטאות': '#d97706', 'בטיחות': '#ca8a04',
                   'אחר': '#94a3b8', 'ללא פירוט': '#64748b'}

        cg1, cg2 = st.columns(2)
        with cg1:
            st.markdown("**🥧 חלוקה לפי סוג**")
            pdf = counts.reset_index()
            pdf.columns = ['קטגוריה', 'כמות']
            fp = px.pie(pdf, names='קטגוריה', values='כמות', color='קטגוריה',
                        color_discrete_map=col_map, hole=0.4, height=320)
            fp.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                             font=dict(color=TEXT),
                             legend=dict(orientation='h', yanchor='bottom', y=-0.15, x=0.5,
                                         xanchor='center'),
                             margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fp, use_container_width=True, config={'displayModeBar': False})

        with cg2:
            st.markdown("**📊 מגמה יומית**")
            try:
                df_c['dt_only'] = pd.to_datetime(df_c['scheduled_hour'], errors='coerce').dt.date
                bd = df_c.groupby(['dt_only', 'category']).size().reset_index(name='count')
                bd['dt_only'] = bd['dt_only'].astype(str)
                if not bd.empty:
                    ft = px.bar(bd, x='dt_only', y='count', color='category',
                                color_discrete_map=col_map,
                                labels={'dt_only': 'תאריך', 'count': 'מספר', 'category': 'סוג'},
                                height=320)
                    ft.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                     font=dict(color=TEXT),
                                     legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
                                     margin=dict(l=20, r=20, t=40, b=20), xaxis_title=None)
                    st.plotly_chart(ft, use_container_width=True, config={'displayModeBar': False})
            except Exception:
                pass

    if all_scans:
        st.markdown("---")
        st.markdown("#### 🕐 יומן סריקות מפורט")

        f1, f2, f3 = st.columns([2, 2, 3])
        all_sc = sorted(set(s.get('scanned_by') or '(לא ידוע)' for s in all_scans))
        sel_s = f1.selectbox("👤 סנן לפי נציג", ["כל הנציגים"] + all_sc, key="dsc_f")
        sel_st = f2.selectbox("סטטוס", ["הכל", "✅ תקין בלבד", "⚠️ לא תקין בלבד"], key="dsc_st")
        cs = f3.text_input("🔍 חיפוש מצלמה", "", key="dsc_cam")

        fs = all_scans
        if sel_s != "כל הנציגים":
            if sel_s == '(לא ידוע)':
                fs = [s for s in fs if not s.get('scanned_by')]
            else:
                fs = [s for s in fs if s.get('scanned_by') == sel_s]
        if sel_st == "✅ תקין בלבד":
            fs = [s for s in fs if (s.get('status') or 'ok') != 'issue']
        elif sel_st == "⚠️ לא תקין בלבד":
            fs = [s for s in fs if s.get('status') == 'issue']
        if cs.strip():
            q = cs.strip().lower()
            fs = [s for s in fs if q in (s.get('camera_name') or '').lower()]

        ss = sorted(fs, key=lambda x: x.get('scanned_at') or x.get('scheduled_hour', ''), reverse=True)

        rows = []
        for s in ss[:100]:
            status = s.get('status') or 'ok'
            scheduled = s.get('scheduled_hour', '')
            scanned_at = s.get('scanned_at') or ''
            tdd = '-'
            if scheduled and scanned_at:
                try:
                    sd = datetime.strptime(scheduled, "%Y-%m-%d %H:%M")
                    ad = datetime.strptime(scanned_at[:19], "%Y-%m-%d %H:%M:%S")
                    dm = int((ad - sd).total_seconds() / 60)
                    if dm < 0: tdd = f"⏰ {abs(dm)} דק' מוקדם"
                    elif dm < 15: tdd = f"✅ בזמן ({dm} דק')"
                    elif dm < 60: tdd = f"🟡 {dm} דק' באיחור"
                    else: tdd = f"🔴 {dm // 60}:{dm % 60:02d} באיחור"
                except (ValueError, TypeError):
                    tdd = '-'
            rows.append({
                "שעה מתוזמנת": scheduled,
                "בוצע בפועל": scanned_at[:19] if scanned_at else '-',
                "פער זמן": tdd,
                "שם המצלמה": s.get('camera_name', '-'),
                "סטטוס": "⚠️ לא תקין" if status == 'issue' else "✅ תקין",
                "נציג": s.get('scanned_by') or '-',
                "פירוט": s.get('event_details') or '-',
            })

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    try:
        cc_data = db.get_comm_checks_in_date_range(str(start_date), str(end_date))
    except Exception:
        cc_data = []

    if cc_data:
        st.markdown("---")
        st.markdown("#### 🌙 בדיקות קשר במשמרות לילה")
        total_c = len(cc_data)
        done_c = sum(1 for c in cc_data if c.get('actual_time'))
        missed_c = 0
        ns = now_il().strftime("%Y-%m-%d %H:%M")
        for c in cc_data:
            if not c.get('actual_time') and c['scheduled_time'] < ns:
                missed_c += 1
        comp_pct = round((done_c / total_c * 100), 1) if total_c > 0 else 0
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("סה\"כ מתוזמנות", total_c)
        c2.metric("שבוצעו", done_c)
        c3.metric("שהוחמצו", missed_c)
        c4.metric("אחוז עמידה", f"{comp_pct}%")

    st.markdown("---")
    st.markdown("#### 📥 ייצוא נתונים")
    ec1, ec2 = st.columns(2)
    if all_scans:
        df_e = pd.DataFrame(all_scans)
        if not df_e.empty:
            csv = df_e.to_csv(index=False).encode('utf-8-sig')
            ec1.download_button("📥 ייצא סריקות (CSV)", csv,
                                 f"scans_{start_date}_to_{end_date}.csv", "text/csv",
                                 use_container_width=True)
    if all_faults_list:
        df_ef = pd.DataFrame(all_faults_list)
        csv_f = df_ef.to_csv(index=False).encode('utf-8-sig')
        ec2.download_button("📥 ייצא תקלות (CSV)", csv_f,
                             f"faults_{start_date}_to_{end_date}.csv", "text/csv",
                             use_container_width=True)


elif page == "לוז סריקות":
    if st.session_state.get('user_role') != 'manager':
        st.error("עמוד זה זמין למנהלת בלבד")
        st.stop()

    st.header("📅 לו״ז סריקות")
    st.caption("הגדרת חלונות זמן קבועים · הלו״ז מוצג למוקדן בזמן אמת")

    all_plans = db.get_all_scheduled_plans(active_only=True)
    all_cams_p = db.get_all_cameras()

    editing_id = st.session_state.get('editing_plan_id')
    adding_new = st.session_state.get('adding_new_plan', False)

    if editing_id or adding_new:
        plan = next((p for p in all_plans if p['id'] == editing_id), None) if editing_id else {}
        title = f"✏️ עריכת תוכנית: {plan.get('name', '')}" if editing_id else "➕ הוספת תוכנית לו״ז"
        st.markdown(f"### {title}")

        with st.form(f"plan_form_{editing_id or 'new'}", clear_on_submit=False):
            name = st.text_input("שם התוכנית *", value=plan.get('name', ''))
            description = st.text_area("תיאור", value=plan.get('description', ''), height=60)

            tc1, tc2 = st.columns(2)
            start_time_val = tc1.text_input("שעת התחלה (HH:MM) *", value=plan.get('start_time', '07:00'))
            end_time_val = tc2.text_input("שעת סיום (HH:MM) *", value=plan.get('end_time', '09:00'))

            priority = st.selectbox("עדיפות", ['high', 'medium', 'low'],
                format_func=lambda x: {'high': '🔴 גבוהה', 'medium': '🟠 בינונית', 'low': '🟢 נמוכה'}[x],
                index=['high', 'medium', 'low'].index(plan.get('priority', 'medium')))

            st.markdown("**📆 ימי פעילות**")
            days_str = plan.get('days_of_week', 'all')
            all_ds = (days_str == 'all')
            sel_ds_set = set() if all_ds else set(days_str.split(','))

            all_dc = st.checkbox("פעיל בכל ימי השבוע", value=all_ds)
            sel_ds = []
            if not all_dc:
                dc1, dc2, dc3, dc4, dc5, dc6, dc7 = st.columns(7)
                day_map = [('6', 'א׳', dc1), ('0', 'ב׳', dc2), ('1', 'ג׳', dc3),
                            ('2', 'ד׳', dc4), ('3', 'ה׳', dc5), ('4', 'ו׳', dc6), ('5', 'ש׳', dc7)]
                for dn, dl, col in day_map:
                    if col.checkbox(dl, value=dn in sel_ds_set, key=f"day_{editing_id}_{dn}"):
                        sel_ds.append(dn)

            st.markdown("**🎥 מצלמות בתוכנית**")
            all_areas_p = sorted(set(c.get('area', '') for c in all_cams_p if c.get('area')))
            sel_area_b = st.selectbox("💡 מלא לפי אזור",
                                        ["-- בחר אזור --"] + all_areas_p,
                                        key=f"area_bulk_{editing_id or 'new'}")

            cd = {f"{c['name']} ({c.get('area', '') or 'לא ידוע'})": c['id'] for c in all_cams_p}
            cci = set(plan.get('camera_ids', []))
            if sel_area_b != "-- בחר אזור --":
                ac = {c['id'] for c in all_cams_p if c.get('area') == sel_area_b}
                cci = cci | ac
            ccl = [l for l, cid in cd.items() if cid in cci]

            scl = st.multiselect(f"בחר מצלמות ({len(ccl)} נבחרו)", list(cd.keys()), default=ccl)
            sci = [cd[l] for l in scl]

            bc1, bc2 = st.columns(2)
            save = bc1.form_submit_button("💾 שמור", type="primary", use_container_width=True)
            cancel = bc2.form_submit_button("↩️ ביטול", use_container_width=True)

            if save:
                if not name.strip():
                    st.error("יש למלא שם")
                elif not re.match(r'^\d{2}:\d{2}$', start_time_val.strip()) or not re.match(r'^\d{2}:\d{2}$', end_time_val.strip()):
                    st.error("פורמט זמן שגוי - HH:MM")
                else:
                    dv = 'all' if all_dc else (','.join(sel_ds) if sel_ds else 'all')
                    if editing_id:
                        db.update_scheduled_plan(editing_id,
                            name=name.strip(), description=description.strip(),
                            start_time=start_time_val.strip(), end_time=end_time_val.strip(),
                            days_of_week=dv, priority=priority, camera_ids=sci)
                        st.success("עודכנה")
                    else:
                        db.add_scheduled_plan(name=name.strip(), description=description.strip(),
                            start_time=start_time_val.strip(), end_time=end_time_val.strip(),
                            days_of_week=dv, priority=priority, camera_ids=sci)
                        st.success("נוספה")
                    st.session_state.pop('editing_plan_id', None)
                    st.session_state.pop('adding_new_plan', None)
                    st.rerun()

            if cancel:
                st.session_state.pop('editing_plan_id', None)
                st.session_state.pop('adding_new_plan', None)
                st.rerun()

        st.stop()

    if st.button("➕ הוסף תוכנית לו״ז חדשה", type="primary"):
        st.session_state['adding_new_plan'] = True; st.rerun()

    if not all_plans:
        st.info("אין תוכניות לו״ז מוגדרות עדיין.")
    else:
        st.markdown(f"### 📋 תוכניות פעילות · {len(all_plans)}")
        pi = {'high': '🔴', 'medium': '🟠', 'low': '🟢'}
        pl = {'high': 'גבוהה', 'medium': 'בינונית', 'low': 'נמוכה'}
        dlm = {'6': 'א׳', '0': 'ב׳', '1': 'ג׳', '2': 'ד׳', '3': 'ה׳', '4': 'ו׳', '5': 'ש׳'}

        for plan in all_plans:
            icon = pi.get(plan.get('priority', 'medium'), '⚪')
            plabel = pl.get(plan.get('priority', 'medium'), '')
            ds = plan.get('days_of_week', 'all')
            dd = 'כל ימי השבוע' if ds == 'all' else ' · '.join([dlm.get(d, d) for d in ds.split(',')])
            cc = len(plan.get('camera_ids', []))

            with st.container(border=True):
                st.markdown(f"### {icon} {plan['name']}")
                st.caption(f"⏰ {plan.get('start_time', '?')} - {plan.get('end_time', '?')}  ·  📆 {dd}  ·  עדיפות: {plabel}  ·  🎥 {cc} מצלמות")
                if plan.get('description'):
                    st.markdown(f"**📝 תיאור:** {plan.get('description')}")

                ac1, ac2, _ = st.columns([1, 1, 4])
                if ac1.button("✏️ ערוך", key=f"edit_plan_{plan['id']}"):
                    st.session_state['editing_plan_id'] = plan['id']; st.rerun()
                if ac2.button("🗑️ הסר", key=f"del_plan_{plan['id']}"):
                    db.delete_scheduled_plan(plan['id']); st.rerun()


elif page == "נקודות חמות":
    _im_hs = st.session_state.get('user_role') == 'manager'
    st.header("🔥 נקודות חמות")
    st.caption("ניהול נקודות חמות" if _im_hs else "צפייה בלבד")

    all_hs = db.get_all_hotspots(active_only=True)

    if _im_hs:
        ei = st.session_state.get('editing_hotspot_id')
        an = st.session_state.get('adding_new_hotspot', False)

        if ei or an:
            hs = next((h for h in all_hs if h['id'] == ei), None) if ei else {}
            title = f"✏️ עריכה: {hs.get('name', '')}" if ei else "➕ הוספה"
            st.markdown(f"### {title}")

            with st.form(f"hotspot_form_{ei or 'new'}", clear_on_submit=False):
                fc1, fc2 = st.columns(2)
                name = fc1.text_input("שם *", value=hs.get('name', ''))
                area = fc2.text_input("אזור", value=hs.get('area', ''))
                priority = st.selectbox("עדיפות", ['high', 'medium', 'low'],
                    format_func=lambda x: {'high': '🔴 גבוהה', 'medium': '🟠 בינונית', 'low': '🟢 נמוכה'}[x],
                    index=['high', 'medium', 'low'].index(hs.get('priority', 'medium')))
                wf = st.text_area("מה מחפשים?", value=hs.get('watching_for', ''), height=80)

                st.markdown("**⏰ שעות פעילות**")
                tw = [("07:00-09:00", "בוקר מוקדם"), ("09:00-11:00", "עומס בוקר"),
                      ("11:00-13:00", "צהריים"), ("13:00-16:00", "אחר צהריים"),
                      ("16:00-20:00", "אחרי הצהריים"), ("20:00-23:00", "ערב"),
                      ("23:00-05:00", "לילה"), ("05:00-07:00", "שחר")]
                cw = set(hs.get('active_hours', []))
                sw = []
                tc1, tc2 = st.columns(2)
                for i, (w, l) in enumerate(tw):
                    col = tc1 if i % 2 == 0 else tc2
                    if col.checkbox(f"{w} · {l}", value=w in cw, key=f"win_{ei}_{w}"):
                        sw.append(w)

                st.markdown("**🎥 שיוך מצלמות**")
                cfh = db.get_all_cameras()
                cd = {f"{c['name']} ({c.get('area', '') or 'לא ידוע'})": c['id'] for c in cfh}
                cci = set(hs.get('camera_ids', []))
                ccl = [l for l, cid in cd.items() if cid in cci]
                scl = st.multiselect("בחר מצלמות", list(cd.keys()), default=ccl)
                sci = [cd[l] for l in scl]

                notes = st.text_area("הערות", value=hs.get('notes', ''), height=60)

                bc1, bc2 = st.columns(2)
                save = bc1.form_submit_button("💾 שמור", type="primary", use_container_width=True)
                cancel = bc2.form_submit_button("↩️ ביטול", use_container_width=True)

                if save:
                    if not name.strip():
                        st.error("יש למלא שם")
                    else:
                        if ei:
                            db.update_hotspot(ei, name=name.strip(), area=area.strip(),
                                priority=priority, watching_for=wf.strip(), notes=notes.strip(),
                                active_hours=sw, camera_ids=sci)
                            st.success("עודכן")
                        else:
                            ni = db.add_hotspot(name=name.strip(), area=area.strip(), priority=priority,
                                watching_for=wf.strip(), notes=notes.strip(),
                                active_hours=sw, camera_ids=sci)
                            st.success("נוסף") if ni else st.error("שם כפול")
                        st.session_state.pop('editing_hotspot_id', None)
                        st.session_state.pop('adding_new_hotspot', None)
                        st.rerun()
                if cancel:
                    st.session_state.pop('editing_hotspot_id', None)
                    st.session_state.pop('adding_new_hotspot', None)
                    st.rerun()
            st.stop()

        if st.button("➕ הוסף נקודה חמה חדשה", type="primary"):
            st.session_state['adding_new_hotspot'] = True; st.rerun()

    if not all_hs:
        st.info("אין נקודות חמות מוגדרות")
    else:
        st.markdown(f"### 📋 פעילות · {len(all_hs)}")
        pim = {'high': '🔴', 'medium': '🟠', 'low': '🟢'}
        plm = {'high': 'גבוהה', 'medium': 'בינונית', 'low': 'נמוכה'}
        for hs in all_hs:
            p = hs.get('priority', 'medium')
            hd = ' · '.join(hs.get('active_hours', [])) if hs.get('active_hours') else 'לא הוגדר'
            cc = len(hs.get('camera_ids', []))
            ad = hs.get('area', '') or 'לא הוגדר'
            wd = hs.get('watching_for') or 'לא הוגדר'
            with st.container(border=True):
                st.markdown(f"### {pim.get(p, '⚪')} {hs['name']}")
                st.caption(f"🗂️ {ad}  ·  עדיפות: {plm.get(p, p)}  ·  {cc} מצלמות")
                st.markdown(f"**⏰ שעות פעילות:** {hd}")
                st.markdown(f"**👁️ מה מחפשים:** {wd}")
                if hs.get('notes'):
                    st.markdown(f"**📝 הערות:** {hs.get('notes')}")

                if _im_hs:
                    ac1, ac2, _ = st.columns([1, 1, 4])
                    if ac1.button("✏️ ערוך", key=f"edit_hs_{hs['id']}"):
                        st.session_state['editing_hotspot_id'] = hs['id']; st.rerun()
                    if ac2.button("🗑️ הסר", key=f"del_hs_{hs['id']}"):
                        db.delete_hotspot(hs['id']); st.rerun()


elif page == "אתרי בנייה":
    _im_cs = st.session_state.get('user_role') == 'manager'
    st.header("🏗️ אתרי בנייה")
    st.caption("ניהול" if _im_cs else "צפייה בלבד")

    all_st = db.get_all_construction_sites(active_only=True)

    if _im_cs:
        ei = st.session_state.get('editing_site_id')
        an = st.session_state.get('adding_new_site', False)

        if ei or an:
            site = next((s for s in all_st if s['id'] == ei), None) if ei else {}
            title = f"✏️ עריכה: {site.get('name', '')}" if ei else "➕ הוספה"
            st.markdown(f"### {title}")

            with st.form(f"site_form_{ei or 'new'}", clear_on_submit=False):
                name = st.text_input("שם *", value=site.get('name', ''))
                address = st.text_input("כתובת", value=site.get('address', ''))

                sc1, sc2 = st.columns(2)
                sd = sc1.text_input("תאריך התחלה (YYYY-MM-DD)", value=site.get('start_date', '') or '')
                ed = sc2.text_input("תאריך סיום (YYYY-MM-DD)", value=site.get('end_date', '') or '')

                st.markdown("**🎥 מצלמות משויכות**")
                cfs = db.get_all_cameras()
                cd = {f"{c['name']} ({c.get('area', '') or 'לא ידוע'})": c['id'] for c in cfs}
                cci = set(site.get('camera_ids', []))
                ccl = [l for l, cid in cd.items() if cid in cci]
                scl = st.multiselect("בחר מצלמות", list(cd.keys()), default=ccl)
                sci = [cd[l] for l in scl]

                notes = st.text_area("הערות", value=site.get('notes', ''), height=80)

                bc1, bc2 = st.columns(2)
                save = bc1.form_submit_button("💾 שמור", type="primary", use_container_width=True)
                cancel = bc2.form_submit_button("↩️ ביטול", use_container_width=True)

                if save:
                    if not name.strip():
                        st.error("יש למלא שם")
                    else:
                        if ei:
                            db.update_construction_site(ei, name=name.strip(), address=address.strip(),
                                notes=notes.strip(), start_date=sd.strip() or None,
                                end_date=ed.strip() or None, camera_ids=sci)
                            st.success("עודכן")
                        else:
                            ni = db.add_construction_site(name=name.strip(), address=address.strip(),
                                notes=notes.strip(), camera_ids=sci)
                            if ni and (sd.strip() or ed.strip()):
                                db.update_construction_site(ni, start_date=sd.strip() or None,
                                    end_date=ed.strip() or None)
                            st.success("נוסף") if ni else st.error("שם כפול")
                        st.session_state.pop('editing_site_id', None)
                        st.session_state.pop('adding_new_site', None)
                        st.rerun()
                if cancel:
                    st.session_state.pop('editing_site_id', None)
                    st.session_state.pop('adding_new_site', None)
                    st.rerun()
            st.stop()

        if st.button("➕ הוסף אתר בנייה חדש", type="primary"):
            st.session_state['adding_new_site'] = True; st.rerun()

    if not all_st:
        st.info("אין אתרי בנייה מוגדרים")
    else:
        st.markdown(f"### 📋 פעילים · {len(all_st)}")
        for site in all_st:
            cc = len(site.get('camera_ids', []))
            dr = ''
            if site.get('start_date') and site.get('end_date'):
                dr = f"{site['start_date']} → {site['end_date']}"
            elif site.get('start_date'):
                dr = f"החל מ-{site['start_date']}"
            elif site.get('end_date'):
                dr = f"עד {site['end_date']}"

            with st.container(border=True):
                st.markdown(f"### 🏗️ {site['name']}")
                cp = []
                if site.get('address'):
                    cp.append(f"📍 {site.get('address')}")
                cp.append(f"{cc} מצלמות")
                if dr: cp.append(f"📅 {dr}")
                st.caption("  ·  ".join(cp))
                if site.get('notes'):
                    st.markdown(f"**📝 הערות:** {site.get('notes')}")

                if _im_cs:
                    ac1, ac2, _ = st.columns([1, 1, 4])
                    if ac1.button("✏️ ערוך", key=f"edit_site_{site['id']}"):
                        st.session_state['editing_site_id'] = site['id']; st.rerun()
                    if ac2.button("🗑️ הסר", key=f"del_site_{site['id']}"):
                        db.delete_construction_site(site['id']); st.rerun()


elif page == "תקלות":
    st.header("⚠️ תקלות במצלמות")
    _im_f = st.session_state.get('user_role') == 'manager'
    all_f = db.get_active_faults()

    if _im_f:
        with st.expander("➕ הוסף תקלה חדשה"):
            afc = db.get_all_cameras()
            cfd = {c['name']: c['id'] for c in afc}
            with st.form("add_fault_form"):
                sc = st.selectbox("בחר מצלמה", list(cfd.keys()))
                d = st.text_area("תיאור התקלה", height=80)
                if st.form_submit_button("שמור", type="primary"):
                    if d.strip():
                        db.add_fault(cfd[sc], now_il().isoformat(sep=' ', timespec='seconds'),
                                     d.strip(), reported_by=st.session_state.get('user_name', ''))
                        st.success("נוסף"); st.rerun()

    if not all_f:
        st.success("אין תקלות פעילות 🎉")
    else:
        st.markdown(f"### 📋 תקלות פעילות · {len(all_f)}")
        for f in all_f:
            with st.container(border=True):
                st.markdown(f"### 🚫 {f['camera_name']}")
                st.caption(f"📅 {f['fault_datetime']} · דווח ע\"י: {f.get('reported_by') or '-'}")
                st.markdown(f"**תיאור:** {f['description']}")
                if _im_f:
                    fc1, fc2, _ = st.columns([1, 1, 4])
                    if fc1.button("✅ פתור", key=f"resolve_{f['id']}"):
                        db.resolve_fault(f['id'], resolved_by=st.session_state.get('user_name', ''))
                        st.rerun()
                    if fc2.button("🗑️ מחק", key=f"del_fault_{f['id']}"):
                        db.delete_fault(f['id']); st.rerun()


elif page == "מפה":
    st.header("🗺️ מפת מצלמות")
    try:
        import folium
        from streamlit_folium import st_folium
    except ImportError:
        st.error("חסרות ספריות מפה")
        st.stop()

    mt, at, ct = st.tabs(["🗺️ תצוגת מפה", "📍 אזורים", "📤 יבוא CSV"])
    all_c = db.get_all_cameras()
    fi = db.get_faulty_camera_ids()
    ac = _get_area_coords()

    rs = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:00")
    re_ = now.strftime("%Y-%m-%d %H:00")
    ri = db.get_issue_scans_in_range(rs, re_)
    rii = set(i['camera_id'] for i in ri)

    pos = []
    unp = []
    for cam in all_c:
        p = _camera_map_position(cam, ac)
        if p:
            pos.append((cam, p))
        else:
            unp.append(cam)

    with mt:
        total = len(all_c)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("במפה", f"{len(pos)} / {total}")
        m2.metric("תקולות", sum(1 for c, _ in pos if c['id'] in fi))
        m3.metric("אירועים 24ש'", sum(1 for c, _ in pos if c['id'] in rii))
        m4.metric("ללא מיקום", len(unp))

        if not pos:
            st.info("אין מצלמות עם מיקום")
        else:
            fmap = folium.Map(location=TIRAT_CARMEL_CENTER, zoom_start=14, tiles='OpenStreetMap')
            for cam, (lat, lng) in pos:
                if cam['id'] in fi: col = 'red'
                elif cam['id'] in rii: col = 'orange'
                else: col = 'green'
                folium.Marker(location=[lat, lng], tooltip=cam['name'],
                              icon=folium.Icon(color=col, icon='video-camera', prefix='fa')).add_to(fmap)
            st_folium(fmap, width=None, height=650, returned_objects=[], key="main_map")

    with at:
        st.markdown("### 📍 עריכת קואורדינטות אזורים")
        areas = db.get_all_areas()
        st.caption("מרכז טירת כרמל: **32.7602, 34.9702**")
        with st.form("area_coords_form"):
            for area in areas:
                curr = ac.get(area, {})
                cols = st.columns([2, 1, 1])
                cols[0].markdown(f"**{area}**")
                cols[1].text_input("קו רוחב",
                                    value=str(curr.get('lat', '')) if curr.get('lat') else "",
                                    key=f"area_lat_{area}", label_visibility="collapsed")
                cols[2].text_input("קו אורך",
                                    value=str(curr.get('lng', '')) if curr.get('lng') else "",
                                    key=f"area_lng_{area}", label_visibility="collapsed")
            if st.form_submit_button("💾 שמור", type="primary"):
                nc = {}
                for area in areas:
                    ls = st.session_state.get(f"area_lat_{area}", "").strip()
                    ns = st.session_state.get(f"area_lng_{area}", "").strip()
                    if ls and ns:
                        try:
                            nc[area] = {'lat': float(ls), 'lng': float(ns)}
                        except ValueError:
                            pass
                _save_area_coords(nc)
                st.success(f"נשמרו {len(nc)} אזורים"); st.rerun()

    with ct:
        st.markdown("### 📤 יבוא קואורדינטות")
        up = st.file_uploader("CSV", type=['csv'], key="coord_csv")
        if up is not None:
            try:
                du = pd.read_csv(up)
                if st.button("✅ אשר ייבא", type="primary"):
                    cams = db.get_all_cameras()
                    u = 0
                    for _, row in du.iterrows():
                        try:
                            n = int(row['camera_number'])
                            lat = float(row['latitude'])
                            lng = float(row['longitude'])
                            pf = f"#{n} - "
                            m = [c for c in cams if c['name'].startswith(pf)]
                            if m:
                                db.update_camera_location(m[0]['id'], lat, lng)
                                u += 1
                        except (ValueError, TypeError):
                            pass
                    st.success(f"עודכנו {u}"); st.rerun()
            except Exception as e:
                st.error(f"שגיאה: {e}")


elif page == "מצלמות":
    st.header("ניהול מצלמות")
    tab1, tab2, tab3 = st.tabs(["רשימה", "הוספה", "יבוא מרובה"])

    with tab1:
        cams = db.get_all_cameras()
        st.markdown(f"סה\"כ: **{len(cams)}**")
        mc1, mc2 = st.columns([1, 1])
        search = mc1.text_input("🔍 חיפוש", "")
        aa = db.get_all_areas()
        sma = mc2.selectbox("🗂️ אזור", ["כל האזורים"] + aa)

        f = cams
        if search:
            f = [c for c in f if search.lower() in c['name'].lower()]
        if sma != "כל האזורים":
            f = [c for c in f if c.get('area') == sma]

        st.caption(f"מציג {len(f)}")
        if f:
            fim = db.get_faulty_camera_ids()
            for cam in f:
                isf = cam['id'] in fim
                cols = st.columns([3, 2, 2, 1])
                ind = f' <span style="color:{RED};">⚠</span>' if isf else ''
                cols[0].markdown(f'<span class="camera-name">{cam["name"]}</span>{ind}',
                                  unsafe_allow_html=True)
                ad = cam.get('area', '') or '-'
                cols[1].markdown(f'<span style="color:{MUTED}; font-size:0.8rem;">🗂️ {ad}</span>',
                                  unsafe_allow_html=True)
                nc = cols[2].checkbox("בכל שעה", value=bool(cam['is_central']),
                                        key=f"central_{cam['id']}")
                if nc != bool(cam['is_central']):
                    db.update_camera(cam['id'], is_central=nc); st.rerun()
                if cols[3].button("🗑️", key=f"del_{cam['id']}"):
                    db.delete_camera(cam['id']); st.rerun()

    with tab2:
        with st.form("add_camera"):
            name = st.text_input("שם המצלמה")
            ic = st.checkbox("נסרקת בכל שעה")
            if st.form_submit_button("הוסף", type="primary"):
                if name:
                    if db.add_camera(name.strip(), ic):
                        st.success(f"נוסף"); st.rerun()
                    else:
                        st.error("שם כפול")

    with tab3:
        b = st.text_area("שמות (שם בכל שורה)", height=250)
        bc = st.checkbox("הכל כקבועות")
        if st.button("ייבא", type="primary"):
            names = [n for n in b.split("\n") if n.strip()]
            if names:
                a = db.bulk_add_cameras(names, bc)
                st.success(f"נוספו {a}/{len(names)}"); st.rerun()


elif page == "היסטוריה":
    st.header("היסטוריית סריקות")
    c1, c2 = st.columns(2)
    sdh = c1.date_input("מתאריך", value=date.today() - timedelta(days=1))
    edh = c2.date_input("עד תאריך", value=date.today())
    scans = db.get_scans_in_range(f"{sdh} 00:00", f"{edh} 23:00")

    if scans:
        fs = st.radio("סנן:", ["הכל", "רק תקינות", "רק תקלות"], horizontal=True)
        if fs == "רק תקינות":
            scans = [s for s in scans if (s.get('status') or 'ok') == 'ok']
        elif fs == "רק תקלות":
            scans = [s for s in scans if s.get('status') == 'issue']

        data = []
        for s in scans:
            status = s.get('status') or 'ok'
            data.append({
                "שעה מתוזמנת": s['scheduled_hour'],
                "מצלמה": s['camera_name'],
                "בוצע בפועל": s['scanned_at'],
                "נציג": s['scanned_by'] or "-",
                "סטטוס": "⚠️ תקלה" if status == 'issue' else "✅ תקין",
                "פירוט": s.get('event_details') or "-",
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 הורד CSV", csv, "history.csv", "text/csv")
    else:
        st.info("אין נתונים בטווח")


elif page == "הגדרות":
    st.header("הגדרות")

    st.markdown("### הגדרות סריקה")
    with st.form("scan_settings"):
        rc = st.number_input("מקסימום סריקות בשעה", min_value=1, max_value=200,
                              value=int(db.get_setting('rotating_count', '30')))
        g = st.number_input("זמן חסד להתראה (דקות)", min_value=0, max_value=59,
                             value=int(db.get_setting('alert_grace_minutes', '15')))
        if st.form_submit_button("שמור", type="primary"):
            db.set_setting('rotating_count', rc)
            db.set_setting('alert_grace_minutes', g)
            st.success("נשמר")

    st.markdown("### שעות משמרות")
    with st.form("shift_settings"):
        c1, c2, c3 = st.columns(3)
        ms = c1.number_input("בוקר", 0, 23, int(db.get_setting('shift_morning_start', '7')))
        es = c2.number_input("ערב", 0, 23, int(db.get_setting('shift_evening_start', '15')))
        ns = c3.number_input("לילה", 0, 23, int(db.get_setting('shift_night_start', '23')))
        if st.form_submit_button("שמור משמרות", type="primary"):
            db.set_setting('shift_morning_start', ms)
            db.set_setting('shift_evening_start', es)
            db.set_setting('shift_night_start', ns)
            st.success("נשמר")

    st.markdown("### רענון תצוגה")
    ar = st.checkbox("רענון אוטומטי כל 30 שניות",
                      value=st.session_state.get('auto_refresh', False))
    st.session_state['auto_refresh'] = ar

    with st.expander("🔧 כלי עזר"):
        st.markdown("**מצלמות אמיתיות - טירת כרמל (191 מצלמות)**")
        cr = st.checkbox("אני מאשר החלפה", key="confirm_load_real")
        if st.button("🔄 טען 191 מצלמות", disabled=not cr, key="load_real_btn"):
            try:
                import real_cameras
                db.reset_all_data()
                a = db.bulk_add_cameras_structured(real_cameras.get_camera_data_for_import())
                st.session_state.pop("confirm_load_real", None)
                st.success(f"הוחלפו {a}"); st.rerun()
            except ImportError:
                st.error("real_cameras.py לא נמצא")

        st.markdown("---")
        st.markdown("**איפוס סריקות ותקלות**")
        ca = st.checkbox("אני מאשר מחיקה", key="confirm_reset_activity")
        if st.button("🧹 מחק סריקות + תקלות", disabled=not ca, key="reset_activity_btn"):
            db.reset_scans_and_faults()
            st.session_state.pop("confirm_reset_activity", None)
            st.success("נמחק"); st.rerun()

        st.markdown("---")
        st.markdown("**איפוס מלא**")
        cf = st.checkbox("אני מאשר מחיקת הכל", key="confirm_reset_full")
        if st.button("💥 מחק הכל", disabled=not cf, key="reset_full_btn"):
            db.reset_all_data()
            st.session_state.pop("confirm_reset_full", None)
            st.success("נמחק"); st.rerun()


if st.session_state.get('auto_refresh', False):
    st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)
