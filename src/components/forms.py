import streamlit as st

def render_request_form(available_licenses, remaining_months):
    """
    라이센스 활성화 요청 폼을 렌더링합니다.
    """
    st.subheader("라이센스 활성화 요청")
    
    with st.form("license_request_form"):
        email = st.text_input("담당자 이메일", placeholder="example@inavi.com")
        
        # 사용 가능한 라이센스 옵션 (IDLE 상태인 것만)
        license_options = [lic['id'] for lic in available_licenses if lic['status'] == 'IDLE']
        
        if not license_options:
            st.warning("현재 사용 가능한(IDLE) 라이센스가 없습니다.")
            license_id = None
        else:
            license_id = st.selectbox("라이센스 번호", options=license_options)
            
        # 요청 개월 수 (최대 잔여 풀)
        max_months = remaining_months if remaining_months > 0 else 0
        if max_months > 0:
            request_months = st.slider("요청 개월 수", min_value=1, max_value=max_months, value=1)
        else:
            st.error("잔여 자산이 없습니다.")
            request_months = 0
            
        submitted = st.form_submit_button("요청하기")
        
        return submitted, email, license_id, request_months

def render_admin_approval_form():
    """
    관리자 승인용 폼을 렌더링합니다.
    """
    st.subheader("라이센스 승인 (관리자 전용)")
    
    with st.form("admin_approval_form"):
        admin_key = st.text_input("Admin Key", type="password", placeholder="마스터 키를 입력하세요")
        submitted = st.form_submit_button("승인 확정")
        return submitted, admin_key
