"""
מודול הזדהות (Auth) - מוקד 106 טירת כרמל
Login מבוסס בחירת משתמש מרשימה + סיסמה משותפת מ-Streamlit Secrets.
"""
import streamlit as st
import database as db


def _get_password_for_role(role):
    """
    מחזיר את הסיסמה המתאימה לתפקיד מ-Streamlit Secrets.
    - מנהלת: MANAGER_PASSWORD (או APP_PASSWORD אם לא מוגדר)
    - מוקדן: OPERATOR_PASSWORD (או APP_PASSWORD אם לא מוגדר)
    """
    try:
        if role == 'manager':
            pw = st.secrets.get("MANAGER_PASSWORD")
            if pw:
                return pw
        else:
            pw = st.secrets.get("OPERATOR_PASSWORD")
            if pw:
                return pw
        return st.secrets.get("APP_PASSWORD")
    except Exception:
        return None


def is_authenticated():
    return bool(st.session_state.get('user_id'))


def current_user():
    if not is_authenticated():
        return None
    return {
        'id': st.session_state.get('user_id'),
        'username': st.session_state.get('username'),
        'name': st.session_state.get('user_name'),
        'role': st.session_state.get('user_role'),
    }


def is_manager():
    return st.session_state.get('user_role') == 'manager'


def is_operator():
    return st.session_state.get('user_role') == 'operator'


def logout():
    """יציאה נקייה - שומר על הנושא (theme) בלבד"""
    keys_to_keep = {'theme'}
    keys_to_pop = [k for k in st.session_state.keys() if k not in keys_to_keep]
    for k in keys_to_pop:
        del st.session_state[k]


def _login_screen(theme_colors):
    """מסך login - שם משתמש מרשימה + סיסמה"""
    TEXT, MUTED, BG, SURFACE = theme_colors

    st.markdown(f"""
    <div style="max-width: 480px; margin: 60px auto 20px; text-align: center;">
        <div style="font-size: 4rem; margin-bottom: 12px;">🎥</div>
        <h1 style="color: {TEXT}; margin: 0; font-size: 1.9rem;">מוקד רואה 106</h1>
        <p style="color: {MUTED}; margin-top: 8px; font-size: 1rem;">
            עיריית טירת כרמל - מערכת ניהול, תפעול ובקרה
        </p>
    </div>
    """, unsafe_allow_html=True)

    users = db.get_all_users(active_only=True)
    if not users:
        st.error("לא הוגדרו משתמשים במערכת. פנה למנהל המערכת.")
        st.stop()

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login_form"):
            st.markdown("**👤 בחר משתמש**")
            user_display = {f"{u['name']} ({'מנהלת' if u['role'] == 'manager' else 'מוקדן'})": u for u in users}
            selected_key = st.selectbox(
                "משתמש",
                list(user_display.keys()),
                label_visibility="collapsed",
            )

            st.markdown("**🔒 סיסמה**")
            password = st.text_input(
                "סיסמה",
                type="password",
                placeholder="הזן סיסמה",
                label_visibility="collapsed",
            )

            submitted = st.form_submit_button(
                "🔓 כניסה",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                expected = _shared_password()
                if not expected:
                    st.error("סיסמת המערכת לא הוגדרה ב-Secrets. פנה למנהל המערכת.")
                    st.stop()
                if password != expected:
                    st.error("סיסמה שגויה")
                else:
                    u = user_display[selected_key]
                    st.session_state['user_id'] = u['id']
                    st.session_state['username'] = u['username']
                    st.session_state['user_name'] = u['name']
                    st.session_state['user_role'] = u['role']
                    db.log_action(u['id'], 'login', 'user', u['id'])
                    st.rerun()

    st.stop()


def require_login(theme_colors):
    """שער login שחייב להתקיים לפני שאר האפליקציה"""
    if not is_authenticated():
        _login_screen(theme_colors)
