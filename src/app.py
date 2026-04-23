import streamlit as st
import sys
import os

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


st.set_page_config(page_title="B2B License Manager", page_icon="🔐", layout="wide")

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
        font-family: 'Public Sans', sans-serif !important; 
        color: #0F172A;
    }
    
    /* Headers Typography */
    h1 { font-size: 30px !important; font-weight: 700 !important; line-height: 38px !important; letter-spacing: -0.02em !important; color: #0F172A !important; }
    h2 { font-size: 24px !important; font-weight: 600 !important; line-height: 32px !important; letter-spacing: -0.01em !important; color: #0F172A !important; }
    h3 { font-size: 20px !important; font-weight: 600 !important; line-height: 28px !important; color: #0F172A !important; }
    
    /* Form & Input Styles */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="textarea"] > div { 
        border-radius: 4px !important; 
        border: 1px solid #c6c6cd !important;
        background-color: #ffffff !important;
        transition: all 0.2s ease;
    }
    div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within, div[data-baseweb="textarea"] > div:focus-within {
        border-color: #0EA5E9 !important;
        box-shadow: 0 0 0 1px #0EA5E9 !important;
    }
    
    /* Buttons */
    [data-testid="stButton"] button { 
        border-radius: 4px !important; 
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    [data-testid="stButton"] button[kind="primary"] {
        background-color: #0F172A !important;
        color: white !important;
        border: none !important;
    }
    [data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #1E293B !important;
        box-shadow: 0 4px 6px rgba(15, 23, 42, 0.1) !important;
    }
    
    /* Cards and Containers */
    .section-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02);
        transition: all 0.2s ease;
    }
    .section-card:hover {
        box-shadow: 0px 4px 12px rgba(15, 23, 42, 0.05);
        border-color: #CBD5E1;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .badge-idle    { background:#F1F5F9; color:#64748B; border: 1px solid #E2E8F0; }
    .badge-pending { background:#FEF3C7; color:#92400E; border: 1px solid #FDE68A; }
    .badge-active  { background:#DCFCE7; color:#166534; border: 1px solid #BBF7D0; }
    .badge-approved{ background:#DBEAFE; color:#1E40AF; border: 1px solid #BFDBFE; }
    .badge-rejected{ background:#FEE2E2; color:#991B1B; border: 1px solid #FECACA; }
    
    /* Login Box */
    .login-box {
        background: white;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0px 8px 24px rgba(15, 23, 42, 0.06);
        border: 1px solid #E2E8F0;
        margin-top: 50px;
        margin-bottom: 50px;
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-family: 'Inter', monospace !important;
        color: #0F172A !important;
    }
    [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)


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
    'ACTIVE': '사용 중', 'APPROVED': '승인됨', 'REJECTED': '취소/반려됨'
}

def dot(status):
    c = STATUS_COLOR.get(status, '#94A3B8')
    return f'<span style="width:9px;height:9px;border-radius:50%;background:{c};display:inline-block;"></span>'


def badge(status):
    cls = STATUS_BADGE.get(status, 'idle')
    text = STATUS_KOR.get(status, status)
    return f'<span class="badge badge-{cls}">{text}</span>'


def render_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #0F172A; margin-bottom: 8px;'>Institutional Integrity</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #475569; margin-bottom: 24px; font-weight: 500;'>B2B License Manager Login</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user_key = st.text_input("접속 키 (ID/Key)", type="password", placeholder="키를 입력하세요")
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("보안 접속", use_container_width=True, type="primary")
            
            if submitted:
                if user_key == INAVI_SECRET_KEY:
                    st.session_state.role = 'INAVI'
                    st.rerun()
                elif user_key == ADMIN_SECRET_KEY:
                    st.session_state.role = 'EGIS'
                    st.rerun()
                else:
                    st.error("유효하지 않은 키입니다.")
        st.markdown("</div>", unsafe_allow_html=True)


def main():
    if "role" not in st.session_state:
        st.session_state.role = None

    if "popup_msg" in st.session_state:
        st.warning(f"⚠️ {st.session_state.popup_msg}")
        del st.session_state.popup_msg

    if "toast_msg" in st.session_state:
        st.toast(st.session_state.toast_msg)
        del st.session_state.toast_msg

    # 로그아웃 및 새로고침 버튼 (로그인 상태일 때 상단 우측)
    if st.session_state.role is not None:
        c1, c2, c3 = st.columns([7, 1, 1])
        with c1:
            st.markdown("<h1 style='color: #0F172A; padding-top: 10px; margin-bottom: 24px;'>XD RoadMap 라이센스 관리</h1>", unsafe_allow_html=True)
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄", use_container_width=True):
                st.rerun()
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("로그아웃", use_container_width=True):
                st.session_state.role = None
                st.rerun()
    else:
        st.markdown("<h1 style='text-align: center; color: #0F172A; padding-top: 40px;'>XD RoadMap 라이센스 관리</h1>", unsafe_allow_html=True)

    if not is_db_configured():
        st.warning("⚙️ **Supabase 환경변수가 설정되지 않았습니다.**")
        with st.expander("설정 방법 보기"):
            st.code(
                "SUPABASE_URL=https://xxxx.supabase.co\n"
                "SUPABASE_ANON_KEY=eyJ...\n"
                "RESEND_API_KEY=re_xxxx\n"
                "ADMIN_SECRET_KEY=egisadmin\n"
                "INAVI_SECRET_KEY=inaviadmin\n"
                "EGIS_ADMIN_EMAIL=admin@egis.com",
                language="bash"
            )
        return

    if st.session_state.role is None:
        render_login()
        return

    # ── 데이터 조회 ────────────────────────────────────────────
    pool     = get_asset_pool()
    licenses = get_licenses() or []
    requests = get_requests() or []

    if not pool:
        st.error("자산 풀 정보를 불러올 수 없습니다. DB 초기화를 확인하세요.")
        return

    remaining_months = pool.get('remaining_months', 0)
    total_months     = pool.get('total_months', 34)
    pending_requests = [r for r in requests if r['status'] == 'PENDING']

    role = st.session_state.role
    is_inavi = (role == 'INAVI')
    is_egis = (role == 'EGIS')

    # ══════════════════════════════════════════════════════════
    # 상단 레이아웃: INAVI는 요청폼+현황, EGIS는 현황 전체차지
    # ══════════════════════════════════════════════════════════
    if is_inavi:
        col_left, col_right = st.columns([1, 1], gap="large")

        # ── 좌: 라이센스 활성화 요청 (INAVI 전용) ─────────────────
        with col_left:
            st.subheader("라이센스 활성화 요청")
            with st.form("request_form"):
                idle_ids = [l['id'] for l in licenses if l['status'] == 'IDLE']
                if idle_ids:
                    license_id = st.selectbox("라이센스 번호", options=idle_ids)
                else:
                    st.info("현재 사용 가능한(대기 중) 라이센스가 없습니다.")
                    license_id = None

                # 2~12개월 고정 선택
                request_months = st.selectbox(
                    "요청 개월 수", 
                    options=list(range(2, 13)),
                    format_func=lambda x: f"{x}개월"
                )

                memo = st.text_area("요청 메시지 / 메모 (선택)", placeholder="여기에 남길 메모를 입력하세요.")

                submitted = st.form_submit_button(
                    "요청하기",
                    use_container_width=True,
                    type="primary",
                )

            if submitted:
                email = "system@inavi.com"  # 이메일 칸 제거로 인한 기본값
                if license_id is None:
                    st.error("선택 가능한 라이센스가 없습니다.")
                elif request_months > remaining_months:
                    st.error(f"요청하신 개월 수({request_months}개월)가 현재 잔여 자산({remaining_months}개월)보다 많습니다. 다시 선택해주세요.")
                else:
                    with st.spinner("요청을 처리 중입니다..."):
                        req = create_request(email, license_id, request_months)
                        if req:
                            send_approval_request_email(
                                email, license_id, request_months, req['approval_token'], memo
                            )
                            st.success(f"License {license_id} 요청이 등록되었습니다.")
                            st.rerun()
                        else:
                            st.error("요청 처리에 실패했습니다.")
    else:
        # EGIS는 전체 너비로 라이센스 현황 표시
        col_right = st.container()

    # ── 라이센스 현황 (공통) ────────────────────────────────────
    with col_right:
        st.subheader("라이센스 현황" if is_inavi else "현재 활성화된 라이센스 상태")
        for lic in licenses:
            s  = lic['status']
            ex = ""
            if s == 'ACTIVE' and lic.get('current_expiry_date'):
                date_str = lic['current_expiry_date'][:10]
                year, month, _ = date_str.split('-')
                ex = f"<span style='color:#94A3B8;font-size:12px;'>만료일 {year}년 {month}월</span>"
            st.markdown(
                f"""<div style="display:flex;align-items:center;gap:10px;padding:14px 18px;margin-bottom:8px;border-radius:8px;border:1px solid #E2E8F0;background:white;">
{dot(s)}
<span style="font-weight:600;color:#1E293B;flex:1;">License {lic['id']}</span>
{badge(s)}
{ex}
</div>""",
                unsafe_allow_html=True,
            )
            if is_inavi and s == 'ACTIVE':
                with st.expander("⏳ 라이센스 연장하기"):
                    with st.form(f"extend_form_{lic['id']}"):
                        ext_months = st.selectbox("연장 개월 수", options=list(range(1, 13)), format_func=lambda x: f"{x}개월", key=f"ext_m_{lic['id']}")
                        ext_memo = st.text_area("연장 사유 / 메모 (선택)", key=f"ext_memo_{lic['id']}")
                        ext_submitted = st.form_submit_button("연장 요청하기", use_container_width=True)
                        if ext_submitted:
                            email = "system@inavi.com"
                            if ext_months > remaining_months:
                                st.error(f"잔여 자산({remaining_months}개월)이 부족합니다.")
                            else:
                                with st.spinner("연장 요청 중..."):
                                    req = create_request(email, lic['id'], ext_months)
                                    if req:
                                        send_approval_request_email(email, lic['id'], ext_months, req['approval_token'], ext_memo)
                                        st.success("연장 요청이 등록되었습니다.")
                                        st.rerun()
                                    else:
                                        st.error("요청 처리에 실패했습니다.")

    # ══════════════════════════════════════════════════════════
    # 중단: 요청 현황 및 승인/취소 처리
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    badge_html = f"<span style='background:#EF4444;color:white;border-radius:999px;padding:2px 9px;font-size:13px;margin-left:8px;'>{len(pending_requests)}</span>" if pending_requests else ""
    st.markdown(f"### 📋 요청 현황 {badge_html}", unsafe_allow_html=True)

    if not requests:
        st.caption("아직 접수된 요청이 없습니다.")
    else:
        for req in requests:
            s = req['status']
            is_pending = (s == 'PENDING')

            with st.expander(
                f"{'🟡' if is_pending else ('✅' if s == 'APPROVED' else '❌')}  "
                f"License {req['license_id']}  ·  "
                f"{req['requested_months']}개월  ·  "
                f"{req['created_at'][:10]}",
                expanded=is_pending,
            ):
                info_col, action_col = st.columns([1, 1])

                with info_col:
                    req_mail_text = f"""<p style="margin:4px 0;color:#64748B;font-size:13px;">요청 메일 발송일</p>
<p style="margin:0 0 10px;font-weight:600;">{req.get('request_mail_date') or '미입력'}</p>""" if is_inavi else ""
                    
                    app_mail_text = f"""<p style="margin:4px 0;color:#64748B;font-size:13px;">승인 메일 발송일</p>
<p style="margin:0;font-weight:600;">{req.get('approval_date') or '미입력'}</p>""" if is_egis else ""
                    
                    st.markdown(
                        f"""<div class="section-card">
<p style="margin:4px 0;color:#64748B;font-size:13px;">라이센스</p>
<p style="margin:0 0 10px;font-weight:600;">License {req['license_id']}</p>
<p style="margin:4px 0;color:#64748B;font-size:13px;">요청 기간</p>
<p style="margin:0 0 10px;font-weight:600;">{req['requested_months']}개월</p>
<p style="margin:4px 0;color:#64748B;font-size:13px;">요청일</p>
<p style="margin:0 0 10px;font-weight:600;">{req['created_at'][:10]}</p>
{req_mail_text}
{app_mail_text}
</div>""",
                        unsafe_allow_html=True,
                    )

                with action_col:
                    if is_pending:
                        if is_inavi:
                            # 아이나비: 요청 취소 버튼
                            st.markdown(
                                "<div style='padding:12px 0 4px;'>"
                                "<p style='color:#64748B;font-size:13px;margin:0 0 6px;'>요청 취소 (아이나비 전용)</p>"
                                "</div>",
                                unsafe_allow_html=True,
                            )
                            if st.button("❌ 요청 취소", key=f"cancel_{req['id']}", use_container_width=True):
                                with st.spinner("취소 중..."):
                                    if cancel_request(req['id']):
                                        st.success("요청이 취소되었습니다.")
                                        st.rerun()
                                    else:
                                        st.error("취소에 실패했습니다.")
                        elif is_egis:
                            # EGIS: 수락/반려 버튼
                            st.markdown(
                                "<div style='padding:12px 0 4px;'>"
                                "<p style='color:#64748B;font-size:13px;margin:0 0 6px;'>요청 승인/반려 (EGIS 관리자 전용)</p>"
                                "</div>",
                                unsafe_allow_html=True,
                            )
                            a_col, r_col = st.columns(2)
                            a_col.button(
                                "✅ 수락", 
                                key=f"approve_{req['id']}", 
                                use_container_width=True, 
                                type="primary",
                                on_click=handle_egis_action,
                                args=("approve", req['id'], req['approval_token'], req['license_id'])
                            )
                            r_col.button(
                                "❌ 반려", 
                                key=f"reject_{req['id']}",  
                                use_container_width=True,
                                on_click=handle_egis_action,
                                args=("reject", req['id'], req['approval_token'], req['license_id'])
                            )
                    else:
                        st.markdown(
                            f"""<div style="padding:20px;border-radius:8px;border:1px solid #E2E8F0;background:#F8FAFC;text-align:center;">
{badge(s)}
<p style="margin:8px 0 0;color:#94A3B8;font-size:13px;">처리 완료</p>
</div>""",
                            unsafe_allow_html=True,
                        )
                        
                # 메일 날짜 수동 입력 영역
                st.markdown("---")
                st.markdown("<p style='font-size:13px;font-weight:600;margin-bottom:8px;'>📧 메일 수발신 날짜 기록 (수동 입력)</p>", unsafe_allow_html=True)
                
                c_m1, c_m2, c_btn = st.columns([2, 2, 1])
                
                from datetime import datetime
                def parse_date(d_str):
                    if d_str: return datetime.strptime(d_str[:10], "%Y-%m-%d").date()
                    return None
                
                cur_rmd = parse_date(req.get('request_mail_date'))
                cur_amd = parse_date(req.get('approval_date'))
                
                new_rmd = cur_rmd
                new_amd = cur_amd
                
                with c_m1:
                    if is_inavi:
                        new_rmd = st.date_input("요청 메일 발송일", value=cur_rmd if cur_rmd else None, key=f"d_req_{req['id']}")
                with c_m2:
                    if is_egis:
                        new_amd = st.date_input("승인 메일 발송일", value=cur_amd if cur_amd else None, key=f"d_app_{req['id']}")
                    
                with c_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("날짜 저장", key=f"save_dates_{req['id']}", use_container_width=True):
                        from api.supabase_db import update_request_dates
                        ok = update_request_dates(
                            req['id'], 
                            new_rmd.isoformat() if new_rmd else None, 
                            new_amd.isoformat() if new_amd else None
                        )
                        if ok:
                            st.session_state.toast_msg = "✅ 날짜가 저장되었습니다."
                            st.rerun()
                        else:
                            st.error("저장 실패")

    # ══════════════════════════════════════════════════════════
    # 하단: 자산 풀 현황 (공통)
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("📊 34개월 통합 자산 풀 현황")

    m1, m2, m3 = st.columns(3)
    used = total_months - remaining_months
    m1.metric("전체 풀",  f"{total_months}개월")
    m2.metric("잔여",     f"{remaining_months}개월")
    m3.metric("사용됨",   f"{used}개월",
              delta=f"-{used}" if used > 0 else None,
              delta_color="off")

    bar_fig = get_usage_bar_chart(remaining_months, total_months)
    st.plotly_chart(bar_fig, use_container_width=True, config={'displayModeBar': False})

    # ══════════════════════════════════════════════════════════
    # 최하단: 이력 (Logs)
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("📋 전체 처리 이력")
    
    from api.supabase_db import get_logs
    logs = get_logs()
    
    if logs:
        # 이력이 많을 수 있으므로 스크롤 가능한 컨테이너 사용
        with st.container(height=300):
            for log in logs:
                time_str = log['timestamp'][:16].replace('T', ' ')
                st.markdown(
                    f"""<div style="font-size: 13px; color: #475569; padding: 8px 12px; margin-bottom: 6px; background: white; border-radius: 6px; border: 1px solid #F1F5F9;">
                        <span style="color: #94A3B8; margin-right: 12px; font-family: monospace;">{time_str}</span>
                        <strong style="color: #1E293B; margin-right: 8px;">[{log['event_type']}]</strong> 
                        {log['description']}
                    </div>""",
                    unsafe_allow_html=True
                )
    else:
        st.caption("기록된 이력이 없습니다.")


if __name__ == "__main__":
    main()
