"""
מערכת מעקב סריקות מצלמות - אפליקציית Streamlit
Camera Scan Tracking System - Streamlit App
"""
from datetime import datetime, timedelta, date, time

import pandas as pd
import streamlit as st

import database as db
import scheduler as sch

# אתחול מסד נתונים
db.init_db()

st.set_page_config(
    page_title="מעקב סריקות מצלמות",
    page_icon="🎥",
    layout="wide",
)

# תמיכה ב-RTL
st.markdown("""
<style>
    .stApp, .stMarkdown, .stText, p, label,
    h1, h2, h3, h4, h5, h6 { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { direction: rtl; text-align: right; }
    div[data-testid="column"] { direction: rtl; text-align: right; }
    .stAlert { direction: rtl; text-align: right; }
    input, textarea { text-align: right; direction: rtl; }
    .stDataFrame { direction: rtl; }
    .stDataFrame table { direction: rtl; }
    /* קטגורית תווית לצ'קבוקסים ורדיו - יישור נכון */
    [data-testid="stRadio"] label, [data-testid="stCheckbox"] label { direction: rtl; }
</style>
""", unsafe_allow_html=True)

st.title("🎥 מערכת מעקב סריקות מצלמות")

# ================= סרגל צד =================
st.sidebar.title("ניווט")
page = st.sidebar.radio("בחר עמוד:", [
    "📊 לוח בקרה",
    "✅ סריקה שוטפת",
    "📋 לו\"ז סריקות",
    "🎥 ניהול מצלמות",
    "⚠️ מצלמות תקולות",
    "📈 היסטוריה",
    "⚙️ הגדרות",
])

now = datetime.now()
current_hour = now.replace(minute=0, second=0, microsecond=0)
current_hour_key = sch.hour_key(current_hour)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**שעה נוכחית:** {now.strftime('%H:%M:%S')}")
st.sidebar.markdown(f"**תאריך:** {now.strftime('%d/%m/%Y')}")
st.sidebar.markdown(f"**משמרת:** {sch.get_shift_name(now)}")

auto_refresh = st.sidebar.checkbox("רענון אוטומטי (30 שניות)")
if auto_refresh:
    st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)


# ================= לוח בקרה =================
if page == "📊 לוח בקרה":
    st.header("לוח בקרה")

    all_cameras = db.get_all_cameras()
    central_cameras = db.get_central_cameras()
    active_faults = db.get_active_faults()
    missed = sch.get_missed_scans(now, lookback_hours=8)

    # תקלות בסריקות ב-24 שעות אחרונות
    today_start = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:00")
    today_end = now.strftime("%Y-%m-%d %H:00")
    recent_issues = db.get_issue_scans_in_range(today_start, today_end)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("מצלמות פעילות", len(all_cameras))
    col2.metric("קבועות", len(central_cameras))
    col3.metric("מצלמות תקולות", len(active_faults))
    col4.metric("סריקות חסרות (8ש')", len(missed))
    col5.metric("אירועים בסריקה (24ש')", len(recent_issues))

    st.markdown("---")

    # אירועים אחרונים בסריקות
    if recent_issues:
        st.subheader("⚠️ אירועים בסריקות (24 שעות אחרונות)")
        issue_data = []
        for s in recent_issues:
            issue_data.append({
                "שעה": s['scheduled_hour'],
                "שם המצלמה": s['camera_name'],
                "פירוט האירוע": s['event_details'] or "-",
                "דווח ע\"י": s['scanned_by'] or "-",
            })
        st.dataframe(
            pd.DataFrame(issue_data),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("---")

    # התראות על סריקות חסרות
    if missed:
        st.error(f"⚠️ יש {len(missed)} סריקות חסרות!")
        missed_data = []
        for hour_k, cam in missed:
            missed_data.append({
                "שעה מתוזמנת": hour_k,
                "שם המצלמה": cam['name'],
                "סוג": "מרכזית" if cam['is_central'] else "רגילה",
            })
        st.dataframe(
            pd.DataFrame(missed_data),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("✅ כל הסריקות בוצעו לפי לוח הזמנים!")

    st.markdown("---")

    # טבלת מצלמות תקולות
    st.subheader("⚠️ מצלמות תקולות")
    if active_faults:
        fault_data = []
        for f in active_faults:
            fault_data.append({
                "שם המצלמה": f['camera_name'],
                "תאריך ושעת התקלה": f['fault_datetime'],
                "תיאור התקלה": f['description'],
            })
        st.dataframe(
            pd.DataFrame(fault_data),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("אין מצלמות תקולות כרגע")

    st.markdown("---")

    # תצוגה מקדימה של השעה הבאה
    next_hour = current_hour + timedelta(hours=1)
    st.subheader(f"⏭️ סריקה הבאה: {next_hour.strftime('%H:00')}")
    nc, nr = sch.get_cameras_for_hour(next_hour)
    st.write(f"מרכזיות: {len(nc)} | בסבב: {len(nr)}")


# ================= סריקה שוטפת =================
elif page == "✅ סריקה שוטפת":
    st.header("סריקה שוטפת")
    st.markdown(
        f"### שעה נוכחית: **{current_hour.strftime('%d/%m/%Y %H:00')}** | "
        f"משמרת: **{sch.get_shift_name(now)}**"
    )

    central, rotating = sch.get_cameras_for_hour(current_hour, include_faulty=False)
    scanned_now = db.get_scans_for_hour(current_hour_key)

    scanner_name = st.text_input(
        "שם הנציג המבצע:",
        value=st.session_state.get('scanner_name', ''),
    )
    st.session_state['scanner_name'] = scanner_name

    total = len(central) + len(rotating)
    completed = sum(1 for c in central + rotating if c['id'] in scanned_now)

    if total > 0:
        st.progress(completed / total, text=f"בוצעו {completed}/{total} סריקות")
    else:
        st.info("לא הוגדרו מצלמות. עבור לעמוד 'ניהול מצלמות' כדי להוסיף.")

    def render_scan_row(cam, prefix):
        """שורה של מצלמה בודדת עם כפתורי תקין/תקלה/ביטול"""
        is_scanned = cam['id'] in scanned_now
        if is_scanned:
            info = scanned_now[cam['id']]
            status = info.get('status') or 'ok'
            by = f" ({info['scanned_by']})" if info['scanned_by'] else ""

            if status == 'issue':
                label = f"**{cam['name']}** ⚠️ תקלה בסריקה • {info['scanned_at']}{by}"
                if info.get('event_details'):
                    label += f"  \n_📝 {info['event_details']}_"
            else:
                label = f"**{cam['name']}** ✅ תקין • {info['scanned_at']}{by}"

            cols = st.columns([4, 1])
            cols[0].markdown(label)
            if cols[1].button("↩️ בטל", key=f"unmark_{prefix}_{cam['id']}"):
                db.unmark_scan(cam['id'], current_hour_key)
                st.rerun()
        else:
            cols = st.columns([3, 1, 1])
            cols[0].markdown(f"**{cam['name']}**")

            if cols[1].button("✅ תקין", key=f"ok_{prefix}_{cam['id']}", type="primary"):
                db.mark_scan(cam['id'], current_hour_key, scanner_name, status='ok')
                st.rerun()

            # פופאובר עם טופס דיווח תקלה
            with cols[2].popover("⚠️ תקלה"):
                st.markdown(f"**דיווח אירוע בסריקה של {cam['name']}**")
                details = st.text_area(
                    "פרט את מהות האירוע/התקלה:",
                    key=f"details_{prefix}_{cam['id']}",
                    height=100,
                    placeholder="למשל: אדם חשוד באזור, תמונה מטושטשת, אזעקה, ...",
                )
                also_faulty = st.checkbox(
                    "🚫 סמן גם את המצלמה כתקולה (תוחרג מהסריקות)",
                    key=f"faulty_{prefix}_{cam['id']}",
                )
                if st.button(
                    "💾 שמור דיווח",
                    key=f"save_issue_{prefix}_{cam['id']}",
                    type="primary",
                ):
                    if not details.strip():
                        st.error("יש למלא פירוט")
                    else:
                        db.mark_scan(
                            cam['id'],
                            current_hour_key,
                            scanner_name,
                            status='issue',
                            event_details=details.strip(),
                        )
                        if also_faulty:
                            db.add_fault(
                                cam['id'],
                                datetime.now().isoformat(sep=' ', timespec='minutes'),
                                details.strip(),
                            )
                        st.rerun()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"🎯 מצלמות קבועות ({len(central)})")
        st.caption("נסרקות בכל שעה")
        if not central:
            st.info("לא הוגדרו מצלמות קבועות")
        for cam in central:
            render_scan_row(cam, "c")

    with col2:
        st.subheader(f"🔄 מצלמות מתחלפות ({len(rotating)})")
        st.caption("סבב שמתחלף בכל שעה")
        if not rotating:
            st.info("לא הוגדרו מצלמות מתחלפות")
        for cam in rotating:
            render_scan_row(cam, "r")

    st.markdown("---")
    if st.button("✅ סמן את כל הנותרות כתקינות", type="secondary"):
        for cam in central + rotating:
            if cam['id'] not in scanned_now:
                db.mark_scan(cam['id'], current_hour_key, scanner_name, status='ok')
        st.rerun()


# ================= לו"ז סריקות =================
elif page == "📋 לו\"ז סריקות":
    st.header("לוח זמנים לסריקות")

    hours = st.slider("מספר שעות להצגה", 4, 48, 24)
    schedule = sch.get_upcoming_schedule(now, hours)

    for slot in schedule:
        header_text = (
            f"🕐 {slot['datetime'].strftime('%d/%m %H:00')} - "
            f"משמרת {slot['shift']} "
            f"({len(slot['central']) + len(slot['rotating'])} מצלמות)"
        )
        with st.expander(header_text):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**מצלמות מרכזיות ({len(slot['central'])}):**")
                for cam in slot['central']:
                    st.markdown(f"- {cam['name']}")
            with col2:
                st.markdown(f"**מצלמות בסבב ({len(slot['rotating'])}):**")
                for cam in slot['rotating']:
                    st.markdown(f"- {cam['name']}")


# ================= ניהול מצלמות =================
elif page == "🎥 ניהול מצלמות":
    st.header("ניהול מצלמות")

    tab1, tab2, tab3 = st.tabs(["רשימת מצלמות", "הוספת מצלמה", "יבוא מרובה"])

    with tab1:
        cams = db.get_all_cameras()
        c_central = sum(1 for c in cams if c['is_central'])
        st.write(
            f"סה\"כ: **{len(cams)}** | "
            f"מרכזיות: **{c_central}** | "
            f"בסבב: **{len(cams) - c_central}**"
        )

        # סינון
        search = st.text_input("🔍 חיפוש לפי שם", "")
        filter_type = st.radio(
            "סנן לפי סוג:",
            ["הכל", "מרכזיות בלבד", "בסבב בלבד"],
            horizontal=True,
        )

        filtered = cams
        if search:
            filtered = [c for c in filtered if search.lower() in c['name'].lower()]
        if filter_type == "מרכזיות בלבד":
            filtered = [c for c in filtered if c['is_central']]
        elif filter_type == "בסבב בלבד":
            filtered = [c for c in filtered if not c['is_central']]

        st.write(f"מציג {len(filtered)} מצלמות")
        st.markdown("---")

        if filtered:
            faulty_ids = db.get_faulty_camera_ids()
            for cam in filtered:
                is_faulty = cam['id'] in faulty_ids
                cols = st.columns([3, 2, 1])
                indicator = " ⚠️ תקולה" if is_faulty else ""
                cols[0].markdown(f"**{cam['name']}**{indicator}")
                new_central = cols[1].checkbox(
                    "מרכזית",
                    value=bool(cam['is_central']),
                    key=f"central_{cam['id']}",
                )
                if new_central != bool(cam['is_central']):
                    db.update_camera(cam['id'], is_central=new_central)
                    st.rerun()
                if cols[2].button("🗑️ מחק", key=f"del_{cam['id']}"):
                    db.delete_camera(cam['id'])
                    st.rerun()
        else:
            if not cams:
                st.info("עדיין לא הוגדרו מצלמות. השתמש בלשוניות למעלה כדי להוסיף.")

    with tab2:
        with st.form("add_camera"):
            name = st.text_input("שם המצלמה")
            is_central = st.checkbox("מצלמה מרכזית (נסרקת בכל שעה)")
            submitted = st.form_submit_button("הוסף", type="primary")
            if submitted and name:
                if db.add_camera(name.strip(), is_central):
                    st.success(f"המצלמה '{name}' נוספה בהצלחה")
                    st.rerun()
                else:
                    st.error("מצלמה בשם זה כבר קיימת")

    with tab3:
        st.markdown("הכנס רשימת שמות מצלמות - שם אחד בכל שורה:")
        bulk_names = st.text_area(
            "שמות מצלמות",
            height=250,
            placeholder="מצלמה 1\nמצלמה 2\nמצלמה 3\n...",
        )
        bulk_central = st.checkbox("סמן את כולן כמצלמות מרכזיות")
        if st.button("ייבא מצלמות", type="primary"):
            names = [n for n in bulk_names.split("\n") if n.strip()]
            if names:
                added = db.bulk_add_cameras(names, bulk_central)
                st.success(f"נוספו {added} מצלמות חדשות מתוך {len(names)} שהוזנו")
                st.rerun()
            else:
                st.warning("אין שמות להוספה")


# ================= מצלמות תקולות =================
elif page == "⚠️ מצלמות תקולות":
    st.header("מצלמות תקולות")

    tab1, tab2, tab3 = st.tabs([
        "תקלות פעילות",
        "דיווח תקלה חדשה",
        "היסטוריית תקלות",
    ])

    with tab1:
        faults = db.get_active_faults()
        if faults:
            st.markdown(f"### סה\"כ תקלות פעילות: **{len(faults)}**")

            fault_data = []
            for f in faults:
                fault_data.append({
                    "מזהה": f['id'],
                    "שם המצלמה": f['camera_name'],
                    "תאריך ושעת התקלה": f['fault_datetime'],
                    "תיאור התקלה": f['description'],
                })
            st.dataframe(
                pd.DataFrame(fault_data),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")
            st.markdown("**סמן תקלה כטופלה:**")
            fault_options = {
                f"#{f['id']} - {f['camera_name']} ({f['fault_datetime']})": f['id']
                for f in faults
            }
            selected = st.selectbox("בחר תקלה", list(fault_options.keys()))
            col1, col2 = st.columns(2)
            if col1.button("✅ סמן כטופלה", type="primary"):
                db.resolve_fault(fault_options[selected])
                st.success("התקלה סומנה כטופלה")
                st.rerun()
            if col2.button("🗑️ מחק דיווח"):
                db.delete_fault(fault_options[selected])
                st.success("הדיווח נמחק")
                st.rerun()
        else:
            st.success("✅ אין תקלות פעילות")

    with tab2:
        cams = db.get_all_cameras()
        if not cams:
            st.warning("יש להוסיף מצלמות תחילה")
        else:
            with st.form("report_fault"):
                cam_options = {c['name']: c['id'] for c in cams}
                selected_cam = st.selectbox("בחר מצלמה", list(cam_options.keys()))

                col1, col2 = st.columns(2)
                fault_date = col1.date_input("תאריך התקלה", value=date.today())
                fault_time_val = col2.time_input(
                    "שעת התקלה",
                    value=time(now.hour, now.minute),
                )

                description = st.text_area(
                    "תיאור התקלה",
                    placeholder="פרט את מהות התקלה...",
                )

                submitted = st.form_submit_button("דווח תקלה", type="primary")
                if submitted:
                    if not description.strip():
                        st.error("יש למלא תיאור תקלה")
                    else:
                        fault_dt = datetime.combine(
                            fault_date, fault_time_val
                        ).isoformat(sep=' ', timespec='minutes')
                        db.add_fault(
                            cam_options[selected_cam],
                            fault_dt,
                            description.strip(),
                        )
                        st.success(f"התקלה במצלמה '{selected_cam}' נרשמה")
                        st.rerun()

    with tab3:
        all_faults = db.get_all_faults()
        if all_faults:
            data = []
            for f in all_faults:
                data.append({
                    "שם המצלמה": f['camera_name'],
                    "תאריך התקלה": f['fault_datetime'],
                    "תיאור": f['description'],
                    "סטטוס": "טופל" if f['resolved'] else "פעיל",
                    "טופל בתאריך": f['resolved_at'] or "-",
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 הורד היסטוריה כ-CSV",
                csv,
                "faults_history.csv",
                "text/csv",
            )
        else:
            st.info("אין היסטוריית תקלות")


# ================= היסטוריה =================
elif page == "📈 היסטוריה":
    st.header("היסטוריית סריקות")

    col1, col2 = st.columns(2)
    start_date = col1.date_input(
        "מתאריך",
        value=date.today() - timedelta(days=1),
    )
    end_date = col2.date_input("עד תאריך", value=date.today())

    start_key = f"{start_date} 00:00"
    end_key = f"{end_date} 23:00"

    scans = db.get_scans_in_range(start_key, end_key)

    if scans:
        filter_status = st.radio(
            "סנן לפי סטטוס:",
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
                "פירוט האירוע": s.get('event_details') or "-",
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 הורד כ-CSV",
            csv,
            "scan_history.csv",
            "text/csv",
        )

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("סיכום ע\"י נציג")
            by_scanner = df.groupby("בוצע ע\"י").size().reset_index(name="מס' סריקות")
            st.dataframe(by_scanner, use_container_width=True, hide_index=True)
        with col_b:
            st.subheader("סיכום לפי סטטוס")
            by_status = df.groupby("סטטוס").size().reset_index(name="מס' סריקות")
            st.dataframe(by_status, use_container_width=True, hide_index=True)
    else:
        st.info("אין נתוני סריקה בטווח זה")


# ================= הגדרות =================
elif page == "⚙️ הגדרות":
    st.header("הגדרות")

    st.subheader("הגדרות סריקה")
    with st.form("scan_settings"):
        rotating_count = st.number_input(
            "מספר מצלמות רגילות לסריקה בכל שעה",
            min_value=1,
            max_value=200,
            value=int(db.get_setting('rotating_count', '20')),
        )
        grace = st.number_input(
            "זמן חסד לפני התראה (בדקות)",
            min_value=0,
            max_value=59,
            value=int(db.get_setting('alert_grace_minutes', '15')),
            help="אחרי כמה דקות מתחילת השעה תופיע התראה על סריקה שלא בוצעה",
        )

        if st.form_submit_button("שמור", type="primary"):
            db.set_setting('rotating_count', rotating_count)
            db.set_setting('alert_grace_minutes', grace)
            st.success("ההגדרות נשמרו")

    st.markdown("---")
    st.subheader("הגדרות משמרות")
    with st.form("shift_settings"):
        col1, col2, col3 = st.columns(3)
        morning = col1.number_input(
            "שעת התחלת בוקר",
            0, 23,
            int(db.get_setting('shift_morning_start', '7')),
        )
        evening = col2.number_input(
            "שעת התחלת ערב",
            0, 23,
            int(db.get_setting('shift_evening_start', '15')),
        )
        night = col3.number_input(
            "שעת התחלת לילה",
            0, 23,
            int(db.get_setting('shift_night_start', '23')),
        )

        if st.form_submit_button("שמור משמרות", type="primary"):
            db.set_setting('shift_morning_start', morning)
            db.set_setting('shift_evening_start', evening)
            db.set_setting('shift_night_start', night)
            st.success("הגדרות משמרות נשמרו")

    st.markdown("---")
    st.subheader("ייצוא נתונים")
    cams = db.get_all_cameras()
    if cams:
        df = pd.DataFrame(cams)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 הורד רשימת מצלמות (CSV)",
            csv,
            "cameras.csv",
            "text/csv",
        )
