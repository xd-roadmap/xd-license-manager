import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.api.supabase_db import get_supabase_client
from src.api.mail_service import send_status_notification_email

load_dotenv()

def check_and_expire_licenses():
    """
    만료일이 지난 라이센스를 찾아 IDLE 상태로 변경하고 알림 메일을 발송합니다.
    """
    supabase = get_supabase_client()
    now = datetime.now()
    
    print(f"[{now.isoformat()}] Running auto-expire check...")
    
    # 활성 상태인 라이센스 조회
    response = supabase.table("licenses").select("*").eq("status", "ACTIVE").execute()
    active_licenses = response.data
    
    if not active_licenses:
        print("No active licenses found.")
        return
        
    for lic in active_licenses:
        expiry_str = lic.get("current_expiry_date")
        if not expiry_str:
            continue
            
        # Supabase ISO 8601 파싱
        try:
            # Python 3.11+ 에서는 fromisoformat이 Z를 지원하지만 그 이하 버전을 위해 처리
            expiry_str_clean = expiry_str.replace("Z", "+00:00")
            expiry_date = datetime.fromisoformat(expiry_str_clean)
            
            # UTC 시간 비교 방지를 위해 단순화하거나, 시스템 로컬/UTC 매칭 필요 (여기서는 단순 비교)
            # tzinfo가 있으면 timezone aware, 없으면 naive
            if expiry_date.tzinfo is not None:
                now_aware = now.astimezone(expiry_date.tzinfo)
                is_expired = now_aware > expiry_date
            else:
                is_expired = now > expiry_date
                
            if is_expired:
                print(f"License {lic['id']} expired on {expiry_str}. Expiring now...")
                
                # 1. 상태 변경
                supabase.table("licenses").update({
                    "status": "IDLE",
                    "current_expiry_date": None
                }).eq("id", lic['id']).execute()
                
                # 2. 로그 기록
                log_data = {
                    "event_type": "EXPIRE",
                    "description": f"License {lic['id']} automatically expired."
                }
                supabase.table("logs").insert(log_data).execute()
                
                # 3. 알림 발송 (EGIS 관리자)
                admin_email = os.getenv("EGIS_ADMIN_EMAIL")
                if admin_email:
                    subject = f"[만료 알림] 라이센스 {lic['id']}가 만료되었습니다."
                    msg = f"라이센스 {lic['id']}의 사용 기간이 종료되어 자동으로 회수(IDLE) 처리되었습니다."
                    send_status_notification_email(admin_email, subject, msg)
            else:
                # 만료일이 안 지났다면, 7일 전인지 체크 (오차 범위 1일 내외로 체크)
                from datetime import timedelta
                time_diff = expiry_date - (now_aware if expiry_date.tzinfo else now)
                
                if timedelta(days=6) <= time_diff <= timedelta(days=7):
                    print(f"License {lic['id']} expires in 7 days. Sending warning email...")
                    from src.api.mail_service import send_release_warning_email
                    send_release_warning_email(lic['id'], expiry_str)
                    
        except Exception as e:
            print(f"Error processing license {lic['id']}: {e}")

if __name__ == "__main__":
    check_and_expire_licenses()
