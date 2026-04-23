import os
import uuid
from datetime import datetime
from dateutil.relativedelta import relativedelta
import importlib
from dotenv import load_dotenv

# 환경변수 로드 (.env 파일을 프로젝트 루트에서 검색)
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(os.path.dirname(_here))
load_dotenv(os.path.join(_root, ".env"))

url: str = os.getenv("SUPABASE_URL", "")
key: str = os.getenv("SUPABASE_ANON_KEY", "")

_supabase_client = None


def get_supabase_client():
    """지연 초기화: 클라이언트를 처음 필요할 때 생성합니다."""
    global _supabase_client
    if _supabase_client is None:
        if not url or not key:
            raise ValueError("Supabase 환경변수가 설정되지 않았습니다. .env 파일에 SUPABASE_URL과 SUPABASE_ANON_KEY를 입력해 주세요.")
        # 런타임 임포트로 경로 충돌 방지
        supabase_mod = importlib.import_module("supabase")
        _supabase_client = supabase_mod.create_client(url, key)
    return _supabase_client


def is_db_configured() -> bool:
    return bool(url and key)


def get_asset_pool():
    supabase = get_supabase_client()
    response = supabase.table("asset_pool").select("*").execute()
    if response.data:
        return response.data[0]
    return None


def get_licenses():
    supabase = get_supabase_client()
    response = supabase.table("licenses").select("*").order("id").execute()
    return response.data


def get_requests():
    supabase = get_supabase_client()
    response = supabase.table("requests").select("*").order("created_at", desc=True).execute()
    return response.data


def get_request_by_token(token: str):
    supabase = get_supabase_client()
    response = supabase.table("requests").select("*").eq("approval_token", token).execute()
    if response.data:
        return response.data[0]
    return None


def create_request(email: str, license_id: int, months: int) -> dict:
    supabase = get_supabase_client()
    token = str(uuid.uuid4())
    data = {
        "requester_email": email,
        "license_id": license_id,
        "requested_months": months,
        "status": "PENDING",
        "approval_token": token
    }
    response = supabase.table("requests").insert(data).execute()

    # 해당 라이센스의 상태를 IDLE인 경우에만 PENDING으로 업데이트 (ACTIVE인 경우 유지)
    lic_res = supabase.table("licenses").select("status").eq("id", license_id).execute()
    if lic_res.data and lic_res.data[0]['status'] == 'IDLE':
        supabase.table("licenses").update({"status": "PENDING"}).eq("id", license_id).execute()

    # 로그 기록
    log_data = {
        "event_type": "REQUEST",
        "description": f"{email} requested license {license_id} for {months} months."
    }
    supabase.table("logs").insert(log_data).execute()

    return response.data[0] if response.data else None


def approve_request(token: str) -> bool:
    supabase = get_supabase_client()
    request_data = get_request_by_token(token)
    if not request_data or request_data['status'] != 'PENDING':
        return False

    months = request_data['requested_months']
    license_id = request_data['license_id']

    # 1. 잔여 풀 확인 및 차감
    pool = get_asset_pool()
    if not pool or pool['remaining_months'] < months:
        return False

    new_remaining = pool['remaining_months'] - months
    supabase.table("asset_pool").update({"remaining_months": new_remaining}).eq("id", pool['id']).execute()

    # 2. 요청 상태 변경
    supabase.table("requests").update({"status": "APPROVED"}).eq("id", request_data['id']).execute()

    # 3. 라이센스 정보 조회 후 상태 및 만료일 변경
    lic_res = supabase.table("licenses").select("*").eq("id", license_id).execute()
    lic_data = lic_res.data[0] if lic_res.data else None
    
    now = datetime.now()
    base_date = now
    if lic_data and lic_data.get('current_expiry_date'):
        curr_exp = datetime.fromisoformat(lic_data['current_expiry_date'].replace('Z', '+00:00'))
        if curr_exp.tzinfo is not None:
            now_aware = now.astimezone(curr_exp.tzinfo)
            if curr_exp > now_aware:
                base_date = curr_exp.replace(tzinfo=None)
        else:
            if curr_exp > now:
                base_date = curr_exp

    expiry_date = base_date + relativedelta(months=months)
    import calendar
    last_day = calendar.monthrange(expiry_date.year, expiry_date.month)[1]
    expiry_date = datetime(expiry_date.year, expiry_date.month, last_day, 23, 59, 59)

    supabase.table("licenses").update({
        "status": "ACTIVE",
        "current_expiry_date": expiry_date.isoformat()
    }).eq("id", license_id).execute()

    # 4. 로그 기록
    log_data = {
        "event_type": "APPROVAL",
        "description": f"Request {request_data['id']} approved. License {license_id} active until {expiry_date.strftime('%Y-%m-%d')}."
    }
    supabase.table("logs").insert(log_data).execute()

    return True


def cancel_request(request_id: str) -> bool:
    supabase = get_supabase_client()
    # 1. PENDING 상태인 요청인지 확인 (보안 차원)
    res = supabase.table("requests").select("*").eq("id", request_id).eq("status", "PENDING").execute()
    if not res.data:
        return False
        
    req = res.data[0]
    
    # 2. 라이센스 상태 롤백 (해당 라이센스가 PENDING인 경우에만 IDLE로 변경)
    lic_res = supabase.table("licenses").select("status").eq("id", req['license_id']).execute()
    if lic_res.data and lic_res.data[0]['status'] == 'PENDING':
        supabase.table("licenses").update({"status": "IDLE"}).eq("id", req['license_id']).execute()
    
    # 3. 요청 상태 변경 (삭제 대신 REJECTED 처리하여 UI에서 확인 가능하게 유지)
    supabase.table("requests").update({"status": "REJECTED"}).eq("id", request_id).execute()
    
    # 4. 로그 기록
    supabase.table("logs").insert({
        "event_type": "REJECT",
        "description": f"Request {request_id} cancelled by INAVI user."
    }).execute()
    
    return True


def get_logs():
    supabase = get_supabase_client()
    response = supabase.table("logs").select("*").order("timestamp", desc=True).execute()
    return response.data


def update_request_dates(req_id: str, request_mail_date: str = None, approval_date: str = None) -> bool:
    supabase = get_supabase_client()
    update_data = {}
    if request_mail_date:
        update_data["request_mail_date"] = request_mail_date
    if approval_date:
        update_data["approval_date"] = approval_date
        
    if not update_data:
        return False
        
    try:
        supabase.table("requests").update(update_data).eq("id", req_id).execute()
        return True
    except Exception as e:
        print(f"Error updating dates: {e}")
        return False

