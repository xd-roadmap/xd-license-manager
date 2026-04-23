// app.js - 전체 로직
var db;
var role = null;
var pool = null;
var licenses = [];
var requests = [];
var modalReqId = null, modalLicId = null, modalToken = null;
var extendLicId = null;

window.addEventListener('load', function () {
    if (!window.supabase) { alert('Supabase 라이브러리 로드 실패'); return; }
    db = window.supabase.createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_ANON_KEY);

    // ─── DOM refs ───
    var loginOverlay  = document.getElementById('loginOverlay');
    var appContent    = document.getElementById('appContent');
    var loginKey      = document.getElementById('loginKey');
    var loginError    = document.getElementById('loginError');

    // 이벤트 바인딩
    document.getElementById('loginBtn').addEventListener('click', handleLogin);
    loginKey.addEventListener('keypress', function (e) { if (e.key === 'Enter') handleLogin(); });
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    document.getElementById('refreshBtn').addEventListener('click', loadAll);

    // 비밀번호 토글
    document.getElementById('togglePw').addEventListener('click', function () {
        var inp = document.getElementById('loginKey');
        var icon = document.getElementById('togglePwIcon');
        if (inp.type === 'password') {
            inp.type = 'text';
            icon.className = 'ph ph-eye-slash';
        } else {
            inp.type = 'password';
            icon.className = 'ph ph-eye';
        }
    });

    // 네비게이션
    document.querySelectorAll('.nav-item[data-page]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            e.preventDefault();
            switchPage(this.dataset.page);
        });
    });

    // 요청 폼
    document.getElementById('btnSubmitRequest').addEventListener('click', handleSubmitRequest);

    // 승인 모달
    document.getElementById('closeModalBtn').addEventListener('click', function () { closeOverlay('approvalModal'); });
    document.getElementById('approveBtn').addEventListener('click', function () { processApproval('approve'); });
    document.getElementById('rejectBtn').addEventListener('click', function () { processApproval('reject'); });

    // 연장 모달
    document.getElementById('closeExtendModalBtn').addEventListener('click', function () { closeOverlay('extendModal'); });
    document.getElementById('cancelExtendBtn').addEventListener('click', function () { closeOverlay('extendModal'); });
    document.getElementById('submitExtendBtn').addEventListener('click', handleSubmitExtend);

    // ─── 로그인 ───
    function handleLogin() {
        var key = loginKey.value.trim();
        loginError.textContent = '';
        if (key === CONFIG.INAVI_SECRET_KEY) {
            role = 'INAVI';
            document.getElementById('userNameDisplay').textContent = '아이나비';
            document.getElementById('userRoleDisplay').textContent = '요청자';
            document.getElementById('roleBadgeHeader').innerHTML = '<span class="role-badge-pill role-inavi">INAVI</span>';
        } else if (key === CONFIG.ADMIN_SECRET_KEY) {
            role = 'EGIS';
            document.getElementById('userNameDisplay').textContent = '이지스';
            document.getElementById('userRoleDisplay').textContent = '관리자';
            document.getElementById('roleBadgeHeader').innerHTML = '<span class="role-badge-pill role-egis">EGIS</span>';
        } else {
            loginError.textContent = '유효하지 않은 접속 키입니다.';
            return;
        }
        loginOverlay.classList.remove('active');
        appContent.style.display = 'flex';
        loadAll();
    }

    function handleLogout() {
        role = null; loginKey.value = '';
        appContent.style.display = 'none';
        loginOverlay.classList.add('active');
    }

    // ─── 데이터 로드 ───
    async function loadAll() {
        try {
            var r1 = await db.from('asset_pool').select('*').limit(1);
            pool = r1.data && r1.data[0] ? r1.data[0] : { total_months: 36, remaining_months: 36 };

            var r2 = await db.from('licenses').select('*').order('id');
            licenses = r2.data || [];

            var r3 = await db.from('requests').select('*').order('created_at', { ascending: false });
            requests = r3.data || [];

            renderDashboard();
            renderRequests();
            renderPool();
            renderLogs();
        } catch (err) { console.error('loadAll error:', err); }
    }

    // ─── 대시보드 렌더 ───
    function renderDashboard() {
        var pending = requests.filter(function (r) { return r.status === 'PENDING'; });
        var badge = document.getElementById('navPendingBadge');
        badge.textContent = pending.length;
        badge.style.display = pending.length > 0 ? '' : 'none';

        if (role === 'INAVI') {
            document.getElementById('inaviLayout').style.display = '';
            document.getElementById('egisLayout').style.display = 'none';
            renderInaviForm();
            renderLicenseList('licenseListInavi', true);
        } else {
            document.getElementById('inaviLayout').style.display = 'none';
            document.getElementById('egisLayout').style.display = '';
            renderLicenseList('licenseListEgis', false);
            var active = licenses.filter(function (l) { return l.status === 'ACTIVE'; }).length;
            document.getElementById('egisLicSummary').textContent = '활성: ' + active + ' / 전체: ' + licenses.length;
        }
    }

    function renderInaviForm() {
        // 대기 중 라이선스만 표시
        var idleIds = licenses.filter(function (l) { return l.status === 'IDLE'; }).map(function (l) { return l.id; });
        var sel = document.getElementById('selectLicenseId');
        sel.innerHTML = '';
        if (idleIds.length === 0) {
            sel.innerHTML = '<option value="">사용 가능한 라이선스 없음</option>';
            document.getElementById('btnSubmitRequest').disabled = true;
        } else {
            idleIds.forEach(function (id) {
                var opt = document.createElement('option');
                opt.value = id; opt.textContent = 'License ' + id;
                sel.appendChild(opt);
            });
            document.getElementById('btnSubmitRequest').disabled = false;
        }

        // 개월 수 (2~12)
        var msel = document.getElementById('selectMonths');
        msel.innerHTML = '';
        for (var i = 2; i <= 12; i++) {
            var opt = document.createElement('option');
            opt.value = i; opt.textContent = i + '개월';
            msel.appendChild(opt);
        }

        // 연장 모달 개월 수 (1~12)
        var esel = document.getElementById('selectExtendMonths');
        esel.innerHTML = '';
        for (var j = 1; j <= 12; j++) {
            var opt2 = document.createElement('option');
            opt2.value = j; opt2.textContent = j + '개월';
            esel.appendChild(opt2);
        }

        var rem = pool ? pool.remaining_months : 0;
        var warn = document.getElementById('requestAssetWarning');
        warn.textContent = '현재 잔여 자산: ' + rem + '개월';
        warn.style.display = '';
    }

    function renderLicenseList(containerId, showExtend) {
        var c = document.getElementById(containerId);
        c.innerHTML = '';
        if (licenses.length === 0) {
            c.innerHTML = '<p class="empty-state">라이선스 정보가 없습니다.</p>';
            return;
        }
        licenses.forEach(function (lic) {
            var dotCls = 'dot-' + lic.status.toLowerCase();
            var badgeHtml = statusBadge(lic.status);
            var expiry = (lic.status === 'ACTIVE' && lic.current_expiry_date)
                ? '<span class="license-expiry">만료: ' + lic.current_expiry_date.substring(0, 7) + '</span>'
                : '';
            var extBtn = (showExtend && lic.status === 'ACTIVE')
                ? '<button class="btn-extend" data-lic="' + lic.id + '">⏳ 연장 요청</button>'
                : '';
            var div = document.createElement('div');
            div.className = 'license-item';
            div.innerHTML =
                '<span class="dot-status ' + dotCls + '"></span>' +
                '<span class="license-id">License ' + lic.id + '</span>' +
                expiry + badgeHtml + extBtn;
            c.appendChild(div);
        });
        // 연장 버튼 이벤트
        c.querySelectorAll('.btn-extend').forEach(function (btn) {
            btn.addEventListener('click', function () { openExtendModal(this.dataset.lic); });
        });
    }

    // ─── 요청 현황 렌더 ───
    function renderRequests() {
        var pending = requests.filter(function (r) { return r.status === 'PENDING'; });
        var cb = document.getElementById('requestsCountBadge');
        if (pending.length > 0) {
            cb.textContent = pending.length + '건 대기중';
            cb.style.display = '';
        } else { cb.style.display = 'none'; }

        var c = document.getElementById('requestsList');
        c.innerHTML = '';
        if (requests.length === 0) {
            c.innerHTML = '<p class="empty-state">아직 접수된 요청이 없습니다.</p>';
            return;
        }
        requests.forEach(function (req) {
            c.appendChild(buildReqItem(req));
        });
    }

    function buildReqItem(req) {
        var isPending = req.status === 'PENDING';
        var icon = isPending ? '🟡' : (req.status === 'APPROVED' ? '✅' : '❌');
        var item = document.createElement('div');
        item.className = 'req-item';
        item.dataset.id = req.id;

        // 메일 날짜 표시 (저장된 날짜가 있을 때)
        var mailDateDisplayHtml = '';
        if (role === 'INAVI' && req.request_mail_date) {
            mailDateDisplayHtml = '<div class="req-info-box"><div class="label">요청 메일 발신일</div><div class="value">' + req.request_mail_date + '</div></div>';
        } else if (role === 'EGIS' && req.approval_date) {
            mailDateDisplayHtml = '<div class="req-info-box"><div class="label">승인 메일 발신일</div><div class="value">' + req.approval_date + '</div></div>';
        }

        // 메일 날짜 입력 열 (역할별 분기)
        var mailDateHtml = '';
        if (role === 'INAVI') {
            mailDateHtml =
                '<div class="form-group" style="margin-bottom:0;">' +
                '<label>요청 메일 발송일</label>' +
                '<input type="date" class="mail-req-date" value="' + (req.request_mail_date || '') + '">' +
                '</div>';
        } else {
            mailDateHtml =
                '<div class="form-group" style="margin-bottom:0;">' +
                '<label>승인 메일 발송일</label>' +
                '<input type="date" class="mail-app-date" value="' + (req.approval_date || '') + '">' +
                '</div>';
        }

        // 액션 버튼
        var actionHtml = '';
        if (isPending) {
            if (role === 'INAVI') {
                actionHtml = '<button class="btn-danger btn-sm cancel-btn" data-id="' + req.id + '" data-lic="' + req.license_id + '">❌ 요청 취소</button>';
            } else {
                actionHtml =
                    '<button class="btn-danger btn-sm" onclick="openApprovalModal(\'' + req.id + '\',' + req.license_id + ',\'' + req.approval_token + '\')">❌ 반려</button>' +
                    '<button class="btn-success btn-sm" onclick="openApprovalModal(\'' + req.id + '\',' + req.license_id + ',\'' + req.approval_token + '\')">✅ 승인</button>';
            }
        }

        item.innerHTML =
            '<div class="req-item-header">' +
              '<span class="dot-status dot-' + req.status.toLowerCase() + '"></span>' +
              '<span class="req-item-title">' + icon + ' License ' + req.license_id + '</span>' +
              '<span class="req-item-meta">' + req.requested_months + '개월 · ' + req.created_at.substring(0, 10) + '</span>' +
              statusBadge(req.status) +
              '<i class="ph ph-caret-down req-expand-icon"></i>' +
            '</div>' +
            '<div class="req-item-body">' +
              '<div class="req-info-grid">' +
                '<div class="req-info-box"><div class="label">라이선스</div><div class="value">License ' + req.license_id + '</div></div>' +
                '<div class="req-info-box"><div class="label">요청 기간</div><div class="value">' + req.requested_months + '개월</div></div>' +
                '<div class="req-info-box"><div class="label">요청일</div><div class="value">' + req.created_at.substring(0, 10) + '</div></div>' +
                '<div class="req-info-box"><div class="label">상태</div><div class="value">' + statusKor(req.status) + '</div></div>' +
                mailDateDisplayHtml +
              '</div>' +
              '<div class="mail-date-section">' +
                '<h4>📧 메일 발신 날짜</h4>' +
                '<div class="mail-date-grid">' +
                  mailDateHtml +
                  '<button class="btn-outline save-date-btn" data-id="' + req.id + '" style="align-self:end;">날짜 저장</button>' +
                '</div>' +
              '</div>' +
              (actionHtml ? '<div class="req-actions">' + actionHtml + '</div>' : '') +
            '</div>';

        // 토글
        item.querySelector('.req-item-header').addEventListener('click', function () {
            item.classList.toggle('open');
        });

        // 취소 버튼
        var cancelBtn = item.querySelector('.cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                handleCancelRequest(this.dataset.id, this.dataset.lic);
            });
        }

        // 날짜 저장
        item.querySelector('.save-date-btn').addEventListener('click', function (e) {
            e.stopPropagation();
            handleSaveDates(req, item);
        });

        return item;
    }

    // ─── 자산 풀 렌더 ───
    function renderPool() {
        if (!pool) return;
        var total = pool.total_months, remain = pool.remaining_months, used = total - remain;
        document.getElementById('metricTotal').textContent = total;
        document.getElementById('metricRemain').textContent = remain;
        document.getElementById('metricUsed').textContent = used;
        var pct = total > 0 ? (used / total * 100).toFixed(1) : 0;
        document.getElementById('poolBarFill').style.width = pct + '%';
        document.getElementById('poolBarUsedLabel').textContent = used + '개월 사용 (' + pct + '%)';
        document.getElementById('poolBarTotalLabel').textContent = '전체 ' + total + '개월';
    }

    // ─── 이력 로그 렌더 ───
    async function renderLogs() {
        var res = await db.from('logs').select('*').order('timestamp', { ascending: false }).limit(100);
        var logs = res.data || [];
        var c = document.getElementById('logsList');
        c.innerHTML = '';
        if (logs.length === 0) {
            c.innerHTML = '<p class="empty-state">기록된 이력이 없습니다.</p>';
            return;
        }
        logs.forEach(function (log) {
            var time = log.timestamp.substring(0, 16).replace('T', ' ');
            var desc = translateLogDesc(log.event_type, log.description);
            var div = document.createElement('div');
            div.className = 'log-item';
            div.innerHTML =
                '<span class="log-time">' + time + '</span>' +
                '<span class="log-type log-type-' + log.event_type + '">' + logTypeKor(log.event_type) + '</span>' +
                '<span class="log-desc">' + desc + '</span>';
            c.appendChild(div);
        });
    }

    // ─── 요청 제출 ───
    async function handleSubmitRequest() {
        var licId = parseInt(document.getElementById('selectLicenseId').value);
        var months = parseInt(document.getElementById('selectMonths').value);
        var memo = document.getElementById('requestMemo').value.trim();
        var rem = pool ? pool.remaining_months : 0;

        if (!licId) { showToast('선택 가능한 라이선스가 없습니다.'); return; }
        if (months > rem) { showToast('잔여 자산(' + rem + '개월)이 부족합니다.'); return; }

        var token = generateToken();
        var res = await db.from('requests').insert({
            requester_email: 'system@inavi.com',
            license_id: licId,
            requested_months: months,
            status: 'PENDING',
            approval_token: token
        }).select();
        if (res.error) { showToast('요청 실패: ' + res.error.message); return; }

        await db.from('licenses').update({ status: 'PENDING' }).eq('id', licId);
        await db.from('logs').insert({ event_type: 'REQUEST', description: 'License ' + licId + ' 활성화 요청 (' + months + '개월)' });

        document.getElementById('requestMemo').value = '';
        showToast('✅ License ' + licId + ' 요청이 등록되었습니다.');
        loadAll();
    }

    // ─── 요청 취소 ───
    async function handleCancelRequest(reqId, licId) {
        var res = await db.from('requests').delete().eq('id', reqId);
        if (res.error) { showToast('취소 실패: ' + res.error.message); return; }
        await db.from('licenses').update({ status: 'IDLE' }).eq('id', licId);
        showToast('✅ 요청이 취소되었습니다.');
        loadAll();
    }

    // ─── 승인/반려 모달 ───
    window.openApprovalModal = function (reqId, licId, token) {
        modalReqId = reqId; modalLicId = licId; modalToken = token;
        var req = requests.find(function (r) { return r.id === reqId; });
        if (!req) return;
        document.getElementById('modalBody').innerHTML =
            '<div class="req-info-grid">' +
            '<div class="req-info-box"><div class="label">라이선스 ID</div><div class="value">License ' + licId + '</div></div>' +
            '<div class="req-info-box"><div class="label">요청 기간</div><div class="value">' + req.requested_months + '개월</div></div>' +
            '<div class="req-info-box"><div class="label">요청일</div><div class="value">' + req.created_at.substring(0, 10) + '</div></div>' +
            '<div class="req-info-box"><div class="label">현재 잔여 자산</div><div class="value">' + (pool ? pool.remaining_months : '-') + '개월</div></div>' +
            '</div>';
        openOverlay('approvalModal');
    };

    async function processApproval(action) {
        if (!modalReqId) return;
        var req = requests.find(function (r) { return r.id === modalReqId; });
        if (!req) return;

        if (action === 'approve') {
            var rem = pool ? pool.remaining_months : 0;
            if (req.requested_months > rem) {
                showToast('❌ 잔여 자산이 부족합니다.'); closeOverlay('approvalModal'); return;
            }
            // 만료일 계산
            var expiry = new Date();
            expiry.setMonth(expiry.getMonth() + req.requested_months);

            await db.from('requests').update({ status: 'APPROVED' }).eq('id', modalReqId);
            await db.from('licenses').update({ status: 'ACTIVE', current_expiry_date: expiry.toISOString() }).eq('id', modalLicId);
            await db.from('asset_pool').update({ remaining_months: rem - req.requested_months }).eq('id', pool.id);
            await db.from('logs').insert({ event_type: 'APPROVAL', description: 'License ' + modalLicId + ' 승인 (' + req.requested_months + '개월, 만료: ' + expiry.toISOString().substring(0, 10) + ')' });
            showToast('✅ 승인 완료!');
        } else {
            await db.from('requests').update({ status: 'REJECTED' }).eq('id', modalReqId);
            await db.from('licenses').update({ status: 'IDLE' }).eq('id', modalLicId);
            await db.from('logs').insert({ event_type: 'REJECT', description: 'Request ' + modalReqId + ' 반려됨.' });
            showToast('❌ 반려 처리되었습니다.');
        }
        closeOverlay('approvalModal');
        loadAll();
    }

    // ─── 연장 요청 모달 ───
    function openExtendModal(licId) {
        extendLicId = licId;
        document.getElementById('extendLicId').textContent = 'License ' + licId;
        document.getElementById('extendMemo').value = '';
        var rem = pool ? pool.remaining_months : 0;
        var warn = document.getElementById('extendAssetWarning');
        warn.textContent = '현재 잔여 자산: ' + rem + '개월';
        warn.style.display = '';
        openOverlay('extendModal');
    }

    async function handleSubmitExtend() {
        var months = parseInt(document.getElementById('selectExtendMonths').value);
        var rem = pool ? pool.remaining_months : 0;
        if (months > rem) { showToast('잔여 자산(' + rem + '개월)이 부족합니다.'); return; }

        var token = generateToken();
        var res = await db.from('requests').insert({
            requester_email: 'system@inavi.com',
            license_id: parseInt(extendLicId),
            requested_months: months,
            status: 'PENDING',
            approval_token: token
        }).select();
        if (res.error) { showToast('연장 요청 실패: ' + res.error.message); return; }

        await db.from('logs').insert({ event_type: 'REQUEST', description: 'License ' + extendLicId + ' 연장 요청 (' + months + '개월)' });
        closeOverlay('extendModal');
        showToast('✅ 연장 요청이 등록되었습니다.');
        loadAll();
    }

    // ─── 메일 날짜 저장 ───
    async function handleSaveDates(req, item) {
        var update = {};
        var reqDateEl = item.querySelector('.mail-req-date');
        var appDateEl = item.querySelector('.mail-app-date');
        if (reqDateEl) update.request_mail_date = reqDateEl.value || null;
        if (appDateEl) update.approval_date = appDateEl.value || null;

        var res = await db.from('requests').update(update).eq('id', req.id);
        if (res.error) { showToast('저장 실패: ' + res.error.message); return; }
        showToast('✅ 날짜가 저장되었습니다.');
        loadAll();
    }

    // ─── 페이지 전환 ───
    function switchPage(page) {
        document.querySelectorAll('.nav-item[data-page]').forEach(function (el) {
            el.classList.toggle('active', el.dataset.page === page);
        });
        document.querySelectorAll('.view-section').forEach(function (el) {
            el.classList.remove('active');
        });
        var target = document.getElementById('view-' + page);
        if (target) target.classList.add('active');
        document.getElementById('breadcrumb').textContent = { dashboard: '대시보드', requests: '요청 현황', pool: '자산 풀 현황', logs: '이력 로그' }[page] || page;
    }

    // ─── Helpers ───
    function openOverlay(id) { document.getElementById(id).classList.add('active'); }
    function closeOverlay(id) { document.getElementById(id).classList.remove('active'); }

    function showToast(msg) {
        var t = document.getElementById('toastMsg');
        t.textContent = msg; t.classList.add('show');
        setTimeout(function () { t.classList.remove('show'); }, 3000);
    }

    function generateToken() {
        return Math.random().toString(36).substring(2) + Date.now().toString(36);
    }

    function statusBadge(status) {
        var map = {
            IDLE: '<span class="badge badge-gray">대기 중</span>',
            PENDING: '<span class="badge badge-yellow">요청 대기</span>',
            ACTIVE: '<span class="badge badge-green">사용 중</span>',
            APPROVED: '<span class="badge badge-blue">승인됨</span>',
            REJECTED: '<span class="badge" style="background:#FEE2E2;color:#991B1B;border:1px solid #FECACA;">반려됨</span>'
        };
        return map[status] || '<span class="badge badge-gray">' + status + '</span>';
    }

    function statusKor(s) {
        return { IDLE: '대기 중', PENDING: '요청 대기', ACTIVE: '사용 중', APPROVED: '승인됨', REJECTED: '반려됨' }[s] || s;
    }

    function logTypeKor(t) {
        return { REQUEST: '요청', APPROVAL: '승인', REJECT: '반려', EXPIRE: '만료' }[t] || t;
    }

    function translateLogDesc(type, desc) {
        if (!desc) return '-';
        // License X 활성화 요청 (Y개월)
        var m1 = desc.match(/License (\d+) 활성화 요청 \((\d+)개월\)/);
        if (m1) return 'License ' + m1[1] + '번 라이선스 활성화 요청이 접수되었습니다. (요청 기간: ' + m1[2] + '개월)';
        // License X 연장 요청 (Y개월)
        var m2 = desc.match(/License (\d+) 연장 요청 \((\d+)개월\)/);
        if (m2) return 'License ' + m2[1] + '번 라이선스 연장 요청이 접수되었습니다. (요청 기간: ' + m2[2] + '개월)';
        // License X 승인
        var m3 = desc.match(/License (\d+) 승인 \((\d+)개월, 만료: ([\d\-]+)\)/);
        if (m3) return 'License ' + m3[1] + '번 라이선스가 승인되어 활성화되었습니다. (기간: ' + m3[2] + '개월, 만료일: ' + m3[3] + ')';
        // Request X 반려
        var m4 = desc.match(/Request .+ 반려됨/);
        if (m4) return '라이선스 요청이 반려 처리되었습니다.';
        // EGIS frontend 승인/반려
        var m5 = desc.match(/Request .+ (approve|reject) by EGIS frontend/);
        if (m5) return m5[1] === 'approve' ? '관리자(EGIS)가 요청을 승인했습니다.' : '관리자(EGIS)가 요청을 반려했습니다.';
        return desc;
    }
});
