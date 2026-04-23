-- ============================================================
-- B2B License Manager - Supabase 초기화 SQL
-- 모든 테이블명은 소문자로 통일 (PostgreSQL 기본 규칙)
-- ============================================================

-- asset_pool: 34개월 통합 자산 풀
CREATE TABLE IF NOT EXISTS asset_pool (
    id SERIAL PRIMARY KEY,
    total_months INT NOT NULL DEFAULT 34,
    remaining_months INT NOT NULL DEFAULT 34,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 초기 데이터 (이미 있으면 건너뜀)
INSERT INTO asset_pool (total_months, remaining_months)
SELECT 34, 34
WHERE NOT EXISTS (SELECT 1 FROM asset_pool);

-- licenses: 라이센스 슬롯 3개
CREATE TABLE IF NOT EXISTS licenses (
    id INT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'IDLE'
        CHECK (status IN ('IDLE', 'PENDING', 'ACTIVE')),
    current_expiry_date TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 라이센스 3개 초기화 (이미 있으면 건너뜀)
INSERT INTO licenses (id, status)
SELECT * FROM (VALUES (1,'IDLE'),(2,'IDLE'),(3,'IDLE')) AS v(id, status)
WHERE NOT EXISTS (SELECT 1 FROM licenses WHERE id = v.id);

-- requests: 활성화 요청 내역
CREATE TABLE IF NOT EXISTS requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_email TEXT NOT NULL,
    license_id INT REFERENCES licenses(id),
    requested_months INT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    approval_token TEXT UNIQUE,
    request_mail_date DATE,
    approval_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- logs: 이벤트 감사 로그
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL
        CHECK (event_type IN ('REQUEST', 'APPROVAL', 'REJECT', 'EXPIRE')),
    description TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- RLS (Row Level Security) 비활성화
-- anon 키로 모든 테이블에 접근 허용 (내부 B2B 도구)
-- ============================================================
ALTER TABLE asset_pool DISABLE ROW LEVEL SECURITY;
ALTER TABLE licenses DISABLE ROW LEVEL SECURITY;
ALTER TABLE requests DISABLE ROW LEVEL SECURITY;
ALTER TABLE logs DISABLE ROW LEVEL SECURITY;
