import os
import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY", "")

def send_approval_request_email(requester_email: str, license_id: int, months: int, approval_token: str, memo: str = ""):
    """
    요청 발생 시 관리자에게 발송되는 이메일
    """
    admin_email = os.getenv("EGIS_ADMIN_EMAIL")
    if not admin_email:
        print("Error: EGIS_ADMIN_EMAIL is not set.")
        return False

    # 실제 배포 시에는 고정된 웹 앱 URL로 변경되어야 합니다.
    # MVP에서는 텍스트 안내 및 파라미터 구조를 보여줍니다.
    # 앱이 띄워진 환경의 도메인 혹은 로컬 주소
    base_url = "http://localhost:8501" 
    approval_link = f"{base_url}/?page=approve&token={approval_token}"

    subject = f"[라이센스 요청] {requester_email}님이 라이센스 활성화를 요청했습니다."
    
    memo_html = f'<blockquote style="border-left: 4px solid #E2E8F0; padding-left: 16px; margin-left: 0; color: #475569; font-style: italic;">{memo}</blockquote><br>' if memo else ""

    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #F8FAFC; padding: 20px; border-bottom: 1px solid #E2E8F0;">
            <h2 style="margin: 0; color: #1E293B;">라이센스 활성화 요청</h2>
        </div>
        <div style="padding: 24px;">
            <p style="margin: 0 0 10px;"><strong>요청자:</strong> {requester_email}</p>
            <p style="margin: 0 0 10px;"><strong>라이센스 번호:</strong> License {license_id}</p>
            <p style="margin: 0 0 20px;"><strong>요청 기간:</strong> {months}개월</p>
            {memo_html}
            <p style="margin: 0 0 20px; color: #64748B;">아래 버튼을 클릭하여 관리자 승인 페이지로 이동하십시오:</p>
            <a href="{approval_link}" style="display: inline-block; padding: 12px 24px; background-color: #3B82F6; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold;">승인 페이지로 이동</a>
        </div>
        <div style="background-color: #F8FAFC; padding: 16px 24px; font-size: 12px; color: #94A3B8; border-top: 1px solid #E2E8F0;">
            ※ 승인을 위해서는 EGIS Admin Key가 필요합니다.
        </div>
    </div>
    """

    try:
        # Resend에서 인증된 도메인 이메일(sender email)이 필요합니다.
        # MVP 로컬 테스트 단계에서는 임의의 이메일이나 Onboarding 이메일을 사용합니다.
        r = resend.Emails.send({
            "from": f"{requester_email.split('@')[0]} <onboarding@resend.dev>",
            "to": admin_email,
            "subject": subject,
            "html": html_content
        })
        print(f"Email sent: {r}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_status_notification_email(to_email: str, subject: str, message: str):
    """
    범용 알림 발송용 메일 (만료 안내, 승인 완료 안내 등)
    """
    try:
        r = resend.Emails.send({
            "from": "License System <onboarding@resend.dev>",
            "to": to_email,
            "subject": subject,
            "html": f"<p>{message}</p>"
        })
        return True
    except Exception as e:
        print(f"Failed to send notification email: {e}")
        return False


def send_release_warning_email(license_id: int, expiry_date: str):
    """
    만료일 7일 전에 아이나비 담당자와 EGIS 관리자에게 발송되는 해제 경고 이메일
    """
    admin_email = os.getenv("EGIS_ADMIN_EMAIL")
    inavi_email = "system@inavi.com" # 실제 환경에서는 담당자 이메일을 동적으로 가져올 수 있습니다.
    
    if not admin_email:
        return False

    subject = f"[만료 임박 알림] License {license_id} 만료가 7일 남았습니다."
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #FEF2F2; padding: 20px; border-bottom: 1px solid #FECACA;">
            <h2 style="margin: 0; color: #991B1B;">라이센스 자동 해제 경고</h2>
        </div>
        <div style="padding: 24px;">
            <p style="margin: 0 0 10px;"><strong>라이센스 번호:</strong> License {license_id}</p>
            <p style="margin: 0 0 10px;"><strong>만료 예정일:</strong> {expiry_date[:10]}</p>
            <br>
            <p style="margin: 0 0 20px; color: #475569;">해당 라이센스는 만료일로부터 7일 뒤 자동으로 대기(IDLE) 상태로 전환됩니다.</p>
            <p style="margin: 0 0 20px; color: #475569; font-weight: bold;">계속 사용하시려면 기한 내에 관리 시스템에 접속하여 [연장하기]를 진행해 주시기 바랍니다.</p>
        </div>
    </div>
    """

    try:
        resend.Emails.send({
            "from": "License System <onboarding@resend.dev>",
            "to": [admin_email, inavi_email],
            "subject": subject,
            "html": html_content
        })
        return True
    except Exception as e:
        print(f"Failed to send warning email: {e}")
        return False
