import streamlit as st
import sys
import os
from datetime import datetime

_src_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_src_dir)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from api.supabase_db import (
    get_asset_pool, get_licenses, get_requests,
    create_request, approve_request, cancel_request, is_db_configured
)
from api.mail_service import send_approval_request_email
from components.charts import get_usage_bar_chart
from utils.validation import is_valid_inavi_email
from utils.constants import ADMIN_SECRET_KEY, INAVI_SECRET_KEY


st.set_page_config(page_title="XD RoadMap 라이선스 관리 시스템", page_icon="🔐", layout="wide")

def handle_egis_action(action, req_id, token, license_id):
    from api.supabase_db import get_supabase_client, approve_request
    supabase = get_supabase_client()
    res = supabase.table("requests").select("status").eq("id", req_id).execute()
    if res.data and res.data[0]['status'] != 'PENDING':
        st.session_state.popup_msg = "아이나비에서 요청을 취소하였습니다"
        return
        
    if action == "approve":
        ok = approve_request(token)
        if ok:
            st.session_state.toast_msg = "✅ 승인 완료!"
        else:
            st.session_state.popup_msg = "승인 실패 (자산 부족 또는 DB 오류)"
    elif action == "reject":
        supabase.table("requests").update({"status": "REJECTED"}).eq("id", req_id).execute()
        supabase.table("licenses").update({"status": "IDLE"}).eq("id", license_id).execute()
        supabase.table("logs").insert({
            "event_type": "REJECT",
            "description": f"Request {req_id} rejected by EGIS."
        }).execute()
        st.session_state.toast_msg = "❌ 반려 처리되었습니다."

# ── 공통 스타일 ─────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"], .stMarkdown, .stText { 
        font-family: 'Public Sans', 'Inter', sans-serif !important; 
        color: #0F172A;
    }
    
    /* Headers Typography */
    h1 { font-size: 28px !important; font-weight: 700 !important; color: #0F172A !important; }
    h2 { font-size: 22px !important; font-weight: 600 !important; color: #0F172A !important; }
    h3 { font-size: 18px !important; font-weight: 600 !important; color: #0F172A !important; }
    
    /* Login Box */
    .login-box {
        background: white;
        padding: 48px 40px;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(15,23,42,0.12);
        border: 1px solid #E2E8F0;
        text-align: center;
        margin-top: 10vh;
    }
    .login-box p {
        color: #0F172A;
        margin-bottom: 28px;
        font-size: 20px;
        font-weight: 600;
    }
    
    /* Buttons */
    [data-testid="stButton"] button { 
        border-radius: 6px !important; 
        font-weight: 600 !important;
        transition: all 0.15s ease;
        justify-content: center !important;
    }
    [data-testid="stButton"] button[kind="primary"] {
        background-color: #0F172A !important;
        color: white !important;
        border: none !important;
        width: 100% !important;
    }
    [data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #1E293B !important;
        box-shadow: 0 4px 12px rgba(15,23,42,0.15) !important;
    }
    
    /* Cards and Containers */
    .section-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(15,23,42,0.03);
    }
    
    /* Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-idle    { background:#F1F5F9; color:#64748B; border: 1px solid #E2E8F0; }
    .badge-pending { background:#FEF3C7; color:#92400E; border: 1px solid #FDE68A; }
    .badge-active  { background:#DCFCE7; color:#166534; border: 1px solid #BBF7D0; }
    .badge-approved{ background:#DBEAFE; color:#1E40AF; border: 1px solid #BFDBFE; }
    .badge-rejected{ background:#FEE2E2; color:#991B1B; border: 1px solid #FECACA; }
    
    /* Hide Streamlit elements for cleaner UI */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def translate_log_desc(event_type, desc):
    if not desc: return "-"
    if any(kor in desc for kor in ["요청했습니다", "승인되었습니다", "취소되었습니다", "반려했습니다", "반려되었습니다"]):
        return desc
    import re
    m1 = re.search(r"([\w@.]+) requested license (\d+) for (\d+) months", desc)
    if m1: return f"{m1.group(1)} 사용자가 License {m1.group(2)}번 활성화를 요청했습니다. ({m1.group(3)}개월)"
    m2 = re.search(r"Request (\d+) approved\. License (\d+) active until ([\d\-]+)", desc)
    if m2: return f"요청(ID: {m2.group(1)})이 승인되었습니다. License {m2.group(2)}번이 {m2.group(3)}까지 활성화되었습니다."
    if "cancelled by INAVI user" in desc:
        m3 = re.search(r"Request (\d+)", desc)
        id_str = f"(ID: {m3.group(1)})" if m3 else ""
        return f"아이나비 사용자에 의해 요청{id_str}이 취소되었습니다."
    if "rejected by EGIS" in desc:
        m4 = re.search(r"Request (\d+)", desc)
        id_str = f"(ID: {m4.group(1)})" if m4 else ""
        return f"관리자(EGIS)가 요청{id_str}을 반려했습니다."
    return desc

def log_type_kor(t):
    return { 'REQUEST': '요청', 'APPROVAL': '승인', 'REJECT': '반려', 'EXPIRE': '만료' }.get(t, t)

STATUS_COLOR = {
    'IDLE': '#94A3B8', 'PENDING': '#F59E0B',
    'ACTIVE': '#22C55E', 'APPROVED': '#3B82F6', 'REJECTED': '#EF4444'
}
STATUS_BADGE = {
    'IDLE': 'idle', 'PENDING': 'pending',
    'ACTIVE': 'active', 'APPROVED': 'approved', 'REJECTED': 'rejected'
}
STATUS_KOR = {
    'IDLE': '대기 중', 'PENDING': '요청 대기',
    'ACTIVE': '사용 중', 'APPROVED': '승인됨', 'REJECTED': '반려됨'
}

def dot(status):
    c = STATUS_COLOR.get(status, '#94A3B8')
    return f'<span style="width:9px;height:9px;border-radius:50%;background:{c};display:inline-block;margin-right:8px;"></span>'

def badge(status):
    cls = STATUS_BADGE.get(status, 'idle')
    text = STATUS_KOR.get(status, status)
    return f'<span class="badge badge-{cls}">{text}</span>'

def render_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""
        <div class="login-box">
            <p>XD RoadMap 라이선스 관리 시스템</p>
        </div>
        """, unsafe_allow_html=True)
        with st.container():
            with st.form("login_form", clear_on_submit=False):
                user_key = st.text_input("접속 키 (ID/Key) 입력", type="password", placeholder="키를 입력하세요")
                submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
                if submitted:
                    if user_key == INAVI_SECRET_KEY:
                        st.session_state.role = 'INAVI'
                        st.rerun()
                    elif user_key == ADMIN_SECRET_KEY:
                        st.session_state.role = 'EGIS'
                        st.rerun()
                    else:
                        st.error("유효하지 않은 접속 키입니다.")

def main():
    if "role" not in st.session_state:
        st.session_state.role = None
    if "popup_msg" in st.session_state:
        st.warning(f"⚠️ {st.session_state.popup_msg}")
        del st.session_state.popup_msg
    if "toast_msg" in st.session_state:
        st.toast(st.session_state.toast_msg)
        del st.session_state.toast_msg

    if st.session_state.role is None:
        render_login()
        return

    c1, c2, c3 = st.columns([7, 1, 1])
    with c1:
        st.markdown("<h1 style='margin-top:10px;'>XD RoadMap 라이선스 관리 시스템</h1>", unsafe_allow_html=True)
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("새로고침", use_container_width=True):
            st.rerun()
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("로그아웃", use_container_width=True):
            st.session_state.role = None
            st.rerun()

    pool     = get_asset_pool()
    licenses = get_licenses() or []
    requests = get_requests() or []
    if not pool:
        st.error("자산 정보를 불러올 수 없습니다.")
        return

    remaining_months = pool.get('remaining_months', 0)
    total_months     = pool.get('total_months', 34)
    pending_requests = [r for r in requests if r['status'] == 'PENDING']
    role = st.session_state.role
    is_inavi = (role == 'INAVI')
    is_egis = (role == 'EGIS')

    if is_inavi:
        col_left, col_right = st.columns([1, 1], gap="large")
        with col_left:
            st.subheader("라이선스 활성화 요청")
            with st.form("request_form"):
                idle_ids = [l['id'] for l in licenses if l['status'] == 'IDLE']
                license_id = st.selectbox("라이선스 번호", options=idle_ids) if idle_ids else None
                request_months = st.selectbox("요청 개월 수", options=list(range(2, 13)), format_func=lambda x: f"{x}개월")
                memo = st.text_area("메모 (선택)")
                submitted = st.form_submit_button("요청하기", use_container_width=True, type="primary")
            if submitted and license_id:
                if request_months > remaining_months:
                    st.error("잔여 자산이 부족합니다.")
                else:
                    req = create_request("system@inavi.com", license_id, request_months)
                    if req:
                        send_approval_request_email("system@inavi.com", license_id, request_months, req['approval_token'], memo)
                        st.success("요청 완료!")
                        st.rerun()
    else:
        col_right = st.container()

    with col_right:
        st.subheader("현재 라이선스 상태")
        for lic in licenses:
            s = lic['status']
            ex = ""
            if s == 'ACTIVE' and lic.get('current_expiry_date'):
                ex = f"<span style='color:#94A3B8;font-size:12px;'>만료: {lic['current_expiry_date'][:7]}</span>"
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:12px 16px;margin-bottom:8px;border-radius:8px;border:1px solid #E2E8F0;background:white;">
                {dot(s)} <span style="font-weight:600;flex:1;">License {lic['id']}</span> {badge(s)} {ex}
            </div>
            """, unsafe_allow_html=True)
            if is_inavi and s == 'ACTIVE':
                with st.expander("⏳ 연장 요청"):
                    with st.form(f"ext_{lic['id']}"):
                        m = st.selectbox("기간", options=list(range(1, 13)), format_func=lambda x: f"{x}개월")
                        if st.form_submit_button("요청하기", use_container_width=True):
                            req = create_request("system@inavi.com", lic['id'], m)
                            if req:
                                send_approval_request_email("system@inavi.com", lic['id'], m, req['approval_token'], "")
                                st.success("연장 요청 완료")
                                st.rerun()

    st.divider()
    st.subheader(f"📋 요청 현황 ({len(pending_requests)})")
    if not requests:
        st.caption("요청 내역이 없습니다.")
    else:
        for req in requests:
            is_pending = (req['status'] == 'PENDING')
            with st.expander(f"License {req['license_id']} ({req['requested_months']}개월) - {req['created_at'][:10]}", expanded=is_pending):
                c_info, c_action = st.columns([1, 1])
                with c_info:
                    st.markdown(f"""
                    <div class="section-card">
                        <p style="font-size:12px;color:#64748B;">라이선스: <b>License {req['license_id']}</b></p>
                        <p style="font-size:12px;color:#64748B;">기간: <b>{req['requested_months']}개월</b></p>
                        <p style="font-size:12px;color:#64748B;">상태: {badge(req['status'])}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with c_action:
                    if is_pending:
                        if is_inavi:
                            if st.button("❌ 요청 취소", key=f"can_{req['id']}", use_container_width=True):
                                if cancel_request(req['id']): st.rerun()
                        elif is_egis:
                            ca, cr = st.columns(2)
                            ca.button("✅ 승인", key=f"app_{req['id']}", type="primary", on_click=handle_egis_action, args=("approve", req['id'], req['approval_token'], req['license_id']))
                            cr.button("❌ 반려", key=f"rej_{req['id']}", on_click=handle_egis_action, args=("reject", req['id'], req['approval_token'], req['license_id']))
                st.markdown("<p style='font-size:13px;font-weight:600;margin-top:10px;'>📧 메일 발신 날짜</p>", unsafe_allow_html=True)
                cm1, cm2, cmb = st.columns([2, 2, 1])
                with cm1:
                    d_req = st.date_input("요청 메일 발송일", value=datetime.strptime(req['request_mail_date'][:10], "%Y-%m-%d").date() if req.get('request_mail_date') else None, key=f"dr_{req['id']}") if is_inavi else st.empty()
                with cm2:
                    d_app = st.date_input("승인 메일 발송일", value=datetime.strptime(req['approval_date'][:10], "%Y-%m-%d").date() if req.get('approval_date') else None, key=f"da_{req['id']}") if is_egis else st.empty()
                with cmb:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("날짜 저장", key=f"sd_{req['id']}", use_container_width=True):
                        from api.supabase_db import update_request_dates
                        update_request_dates(req['id'], d_req.isoformat() if is_inavi and d_req else req.get('request_mail_date'), d_app.isoformat() if is_egis and d_app else req.get('approval_date'))
                        st.rerun()

    st.divider()
    st.subheader("📊 34개월 통합 자산 풀 현황")
    m1, m2, m3 = st.columns(3)
    m1.metric("전체 풀", f"{total_months}개월")
    m2.metric("잔여", f"{remaining_months}개월")
    m3.metric("사용됨", f"{total_months - remaining_months}개월")
    st.plotly_chart(get_usage_bar_chart(remaining_months, total_months), use_container_width=True)

    st.divider()
    st.subheader("📋 전체 처리 이력")
    from api.supabase_db import get_logs
    logs = get_logs()
    if logs:
        with st.container(height=300):
            for log in logs:
                st.markdown(f"""
                <div style="font-size:13px;padding:8px;margin-bottom:6px;background:white;border:1px solid #F1F5F9;border-radius:6px;">
                    <span style="color:#94A3B8;font-family:monospace;">{log['timestamp'][:16]}</span>
                    <strong style="margin:0 8px;">[{log_type_kor(log['event_type'])}]</strong>
                    {translate_log_desc(log['event_type'], log['description'])}
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
