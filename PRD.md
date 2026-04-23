# 제품 요구사항 정의서 (PRD)

## 1. 제품 개요
- **제품명**: B2B 증거 기반 라이센스 관리 시스템 (Evidence-based License Manager)
- **한 줄 소개**: 아이나비시스템즈-EGIS 간의 라이센스 요청 및 승인 과정을 '메일 기록' 기반으로 공식화하고 자동화하는 자산 관리 솔루션
- **핵심 가치 제안**: 단순한 편의성을 넘어 "누가, 언제, 어떤 의도로 자산을 요청했는가"에 대한 디지털 서명(증거)을 남기고, 34개월 통합 풀(Pool)의 투명한 소진 상태를 관리합니다.
- **추천 기술 스택 및 선정 이유**:
    - **Frontend**: Streamlit (B2B 내부 도구 및 데이터 시각화에 최적화된 빠른 개발 속도)
    - **Backend/DB**: Supabase (PostgreSQL 기반의 실시간 데이터 처리 및 Edge Functions를 통한 자동화 구현 용이)
    - **Email API**: Resend (현대적인 API 구조와 높은 도달률, Sender Name 커스터마이징 최적화)
    - **Visualization**: Plotly (34개월 자산 소모 현황을 직관적인 Gauge Chart로 표현)

## 2. 사용자 정의

### 2.1 주요 사용자: 아이나비시스템즈 담당자
- **역할**: 라이센스 활성화 요청 및 잔여 자산 모니터링
- **목표**: 공식적인 절차를 통해 필요한 라이센스를 신속하게 확보
- **핵심 니즈**: 현재 가용 자산 확인 및 요청 프로세스의 투명성
- **유저 스토리**:
    - 아이나비 담당자로서, 시스템에 내 이메일 정보를 입력하고 라이센스 기간을 요청하고 싶다. 왜냐하면 EGIS에 공식적인 요청 기록을 남겨야 하기 때문이다.
    - 아이나비 담당자로서, 현재 34개월 중 남은 개월 수를 시각적으로 확인하고 싶다. 왜냐하면 향후 사업 계획에 따라 자산을 배분해야 하기 때문이다.
    - 아이나비 담당자로서, EGIS가 승인했을 때 즉시 알림 메일을 받고 싶다. 왜냐하면 라이센스 활성화 여부를 바로 확인하고 업무에 투입해야 하기 때문이다.

### 2.2 보조 사용자: EGIS 관리자
- **역할**: 라이센스 요청 검토, 승인 및 전체 풀 관리
- **목표**: 오남용 방지 및 정확한 자산 회수 관리
- **핵심 니즈**: 요청 내역의 무결성 확인 및 만료 처리 자동화
- **유저 스토리**:
    - EGIS 관리자로서, 메일로 받은 링크를 통해 즉시 승인 화면으로 접속하고 싶다. 왜냐하면 관리 대시보드를 찾아 들어가는 번거로움을 줄이고 싶기 때문이다.
    - EGIS 관리자로서, 승인 시 Admin Key를 입력하여 최종 확정하고 싶다. 왜냐하면 보안 사고 및 실수로 인한 승인을 방지해야 하기 때문이다.
    - EGIS 관리자로서, 기간이 만료된 라이센스가 자동으로 회수되길 원한다. 왜냐하면 일일이 만료일을 체크하여 수동으로 정지시키는 리소스를 절감해야 하기 때문이다.

## 3. 핵심 기능 명세 (MVP)

### 3.1 라이센스 활성화 요청 (Inavi) [P0]
- **설명**: 아이나비 담당자가 특정 라이센스 번호에 대해 사용 기간을 설정하여 요청을 생성함
- **사용자 흐름**: 메일 주소 입력 → 라이센스 번호 선택(1~3) → 요청 개월 수 입력 → [요청하기] 클릭
- **입력값**: `requester_email` (Domain Validation: `@inavi.com`), `license_id`, `request_months`
- **비즈니스 규칙**: 
    - 이미 `PENDING` 또는 `ACTIVE` 상태인 라이센스는 중복 요청 불가 (UI에서 Lock)
    - 요청 개월 수는 전체 잔여 풀(Remaining Months)을 초과할 수 없음

### 3.2 메일 기반 알림 및 승인 링크 (Resend) [P0]
- **설명**: 요청 발생 시 EGIS 담당자에게 상세 내역과 승인 페이지 딥링크가 담긴 메일 발송
- **입력값**: 요청 데이터, 승인용 고유 토큰
- **비즈니스 규칙**: 발신자 표시를 아이나비 담당자 이름으로 설정하여 '누가' 보냈는지 명확히 식별 가능하게 함

### 3.3 관리자 승인 대시보드 (EGIS) [P0]
- **설명**: 요청 내역을 검토하고 Admin Key 입력을 통해 승인 처리
- **사용자 흐름**: 메일 링크 클릭 → 상세 내역 확인 → Admin Key 입력 → [승인] 클릭
- **비즈니스 규칙**: 승인 즉시 전체 풀에서 개월 수 차감, `Expiry_Date` 계산 및 저장

### 3.4 자산 현황 시각화 [P1]
- **설명**: 34개월 통합 풀의 상태(가용, 소모 중, 소모 완료)를 Gauge Chart로 표시

### 3.5 만료 자동화 (Auto-Off) [P1]
- **설명**: `Expiry_Date` 도달 시 상태를 `IDLE`로 변경하고 양측에 알림 메일 발송
- **비즈니스 규칙**: Supabase Edge Functions를 활용해 매일 00시 스케줄링 실행

## 4. 페이지 목록 및 화면 구조

- **Main Dashboard**: 
    - **상단**: 34개월 자산 현황 (Plotly Gauge Chart)
    - **중단**: 라이센스 요청 폼 (이메일, 라이센스 선택, 개월 수 슬라이더)
    - **하단**: 현재 활성화된 라이센스 리스트 및 상태 현황
- **Admin Approval Page**:
    - 특정 요청에 대한 상세 정보 표시
    - Admin Key 입력 필드 및 승인/반려 버튼
- **History Page**: 
    - 과거 승인 및 만료 이력 리스트 (데이터 기록 증거)

## 5. 데이터 모델

- **Asset_Pool (Table)**: 
  - `total_months` (34), `remaining_months`, `updated_at`
- **Licenses (Table)**: 
  - `id` (1, 2, 3), `status` (IDLE, PENDING, ACTIVE), `current_expiry_date`
- **Requests (Table)**: 
  - `id`, `requester_email`, `license_id`, `requested_months`, `status` (PENDING, APPROVED, REJECTED), `approval_token`, `created_at`
- **Logs (Table)**: 
  - `id`, `event_type` (REQUEST, APPROVAL, EXPIRE), `description`, `timestamp`

## 6. API 설계

- **POST `/api/request`**: 라이센스 요청 생성 및 Resend 메일 발송 트리거
- **POST `/api/approve`**: Admin Key 검증 및 라이센스 활성화 (DB Transaction 처리)
- **GET `/api/status`**: 현재 자산 풀 및 라이센스 상태 조회
- **Edge Function (Daily)**: `check-expiration` 만료 체크 및 상태 업데이트

## 7. 인증 및 권한

- **Inavi**: 이메일 도메인 검증(`@inavi.com`)을 통한 간이 인증
- **EGIS (Admin)**: 사전 정의된 `Admin_Key` (환경변수 관리) 입력을 통한 승인 권한 부여

## 8. 프로젝트 구조

```text
src/
├── app.py              # Streamlit 메인 엔트리 및 UI 레이아웃
├── api/
│   ├── supabase_db.py  # Supabase CRUD 로직 및 트랜잭션
│   └── mail_service.py # Resend API 연동 및 메일 템플릿 구성
├── components/
│   ├── charts.py       # Plotly Gauge Chart 생성 함수
│   └── forms.py        # 요청 및 승인 입력 폼 컴포넌트
├── supabase/
│   └── functions/      # Edge Functions (Auto-off 스케줄러)
└── utils/
    ├── validation.py   # 이메일 도메인 및 입력값 검증 로직
    └── constants.py    # 설정값 및 환경변수 로더
```

## 9. 환경변수 및 외부 서비스

- `SUPABASE_URL`, `SUPABASE_ANON_KEY`: DB 연동
- `RESEND_API_KEY`: 메일 발송
- `ADMIN_SECRET_KEY`: 승인용 마스터 키
- `EGIS_ADMIN_EMAIL`: 알림 수신용 관리자 메일

## 10. 개발 태스크 (우선순위별)

### P0 태스크 (MVP 핵심)
- [ ] Supabase 테이블 스키마 설계 및 초기 데이터(34개월) 세팅
- [ ] Streamlit 기본 UI 및 라이센스 요청 폼 구현
- [ ] Resend API 연동을 통한 승인 요청 메일 발송 로직 개발
- [ ] Admin Key 기반 승인 처리 및 DB 트랜잭션(풀 차감) 구현

### P1 태스크 (사용성 및 자동화)
- [ ] Plotly를 이용한 자산 소모 현황 Gauge Chart 시각화
- [ ] Supabase Edge Functions를 활용한 만료(Auto-Off) 자동화 스케줄러 개발
- [ ] 이메일 도메인(`@inavi.com`) 유효성 검사 로직 추가

### P2 태스크 (고도화)
- [ ] 승인/만료 시 결과 안내 자동 메일 발송 기능
- [ ] 과거 이력 엑셀 다운로드 기능 추가
- [ ] 라이센스별 상세 사용 로그 뷰어 구현
