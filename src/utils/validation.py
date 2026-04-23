import re

def is_valid_inavi_email(email: str) -> bool:
    """
    아이나비 도메인 이메일인지 검증합니다.
    """
    pattern = r"^[a-zA-Z0-9_.+-]+@inavi\.com$"
    if re.match(pattern, email):
        return True
    return False

def is_valid_request_months(months: int, remaining_months: int) -> bool:
    """
    요청 개월 수가 0보다 크고, 남은 풀 이하인지 확인합니다.
    """
    if months > 0 and months <= remaining_months:
        return True
    return False
