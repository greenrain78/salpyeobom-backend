/**
 * 살펴봄 관제 시스템 메인 애플리케이션 로직
 */

// 로그인한 복지사 이메일 — 보고서 발송 시 기본 수신자로 제안한다.
let currentUserEmail = '';

// ── 스타일 설정 상수 ─────────────────────────────
const CATEGORY_BADGE = {
    '낙상': 'bg-red-100 text-red-600 border-red-200',
    '응급': 'bg-red-100 text-red-600 border-red-200',
    '미응답': 'bg-orange-100 text-orange-600 border-orange-200',
    '지연': 'bg-orange-100 text-orange-600 border-orange-200',
    '투약': 'bg-green-100 text-green-700 border-green-200',
};

const ALERT_THEMES = {
    emergency: {
        box:   'p-4 bg-orange-50 border border-orange-100 rounded-lg',
        icon:  'fa-solid fa-triangle-exclamation text-orange-600 text-sm',
        title: 'text-xs font-black text-orange-700',
    },
    warning: {
        box:   'p-4 bg-red-50 border border-red-100 rounded-lg',
        icon:  'fa-solid fa-circle-exclamation text-red-600 text-sm',
        title: 'text-xs font-black text-red-700',
    },
    normal: {
        box:   'p-4 bg-green-50 border border-green-100 rounded-lg',
        icon:  'fa-solid fa-circle-info text-green-600 text-sm',
        title: 'text-xs font-black text-green-700',
    },
};

const PAGE_TITLES = {
    dashboard: '실시간 취약계층 안전 확인 관제',
    patients:  '대상자 DB 관리',
    report:    '보고서 조회',
};

// ── 상태 ────────────────────────────────────────
let currentSituationId = null;
let pollingInterval    = null;

// ── 초기화 ───────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => initAuth());

// ══════════════════════════════════════════════════
// 인증
// ══════════════════════════════════════════════════

function initAuth() {
    if (sessionStorage.getItem('salpyobom_token')) {
        showDashboard();
        return;
    }

    on('btn-login',       'click',   handleLogin);
    on('login-id',        'keydown', e => e.key === 'Enter' && handleLogin());
    on('login-pw',        'keydown', e => e.key === 'Enter' && handleLogin());
    on('btn-signup',      'click',   handleSignup);
    on('btn-show-signup', 'click',   () => toggleForms(false));
    on('btn-show-login',  'click',   () => toggleForms(true));
}

function toggleForms(showLogin) {
    document.getElementById('login-form-wrap') .classList.toggle('hidden', !showLogin);
    document.getElementById('signup-form-wrap').classList.toggle('hidden',  showLogin);
}

async function handleLogin() {
    const username = val('login-id');
    const password = val('login-pw');
    const errorEl  = el('login-error');
    const btn      = el('btn-login');

    if (!username || !password) return showMsg(errorEl, '아이디와 비밀번호를 입력해주세요.');

    setBtn(btn, true, '로그인 중...');
    try {
        const res = await API.login(username, password);
        sessionStorage.setItem('salpyobom_token', res.access_token);
        showDashboard();
    } catch (err) {
        showMsg(errorEl, err?.data?.detail || '아이디 또는 비밀번호가 올바르지 않습니다.');
        setBtn(btn, false, '로그인');
    }
}

async function handleSignup() {
    const username  = val('signup-id');
    const email     = val('signup-email');
    const pw        = val('signup-pw');
    const pw2       = val('signup-pw2');
    const errorEl   = el('signup-error');
    const successEl = el('signup-success');
    const btn       = el('btn-signup');

    errorEl.classList.add('hidden');
    successEl.classList.add('hidden');

    if (!username || !email || !pw || !pw2) return showMsg(errorEl, '모든 항목을 입력해주세요.');
    if (pw !== pw2) return showMsg(errorEl, '비밀번호가 일치하지 않습니다.');

    setBtn(btn, true, '가입 중...');
    try {
        await API.register(username, email, pw);
        showMsg(successEl, '가입이 완료되었습니다. 로그인해주세요.');
        ['signup-id', 'signup-email', 'signup-pw', 'signup-pw2'].forEach(id => el(id).value = '');
        setTimeout(() => { toggleForms(true); successEl.classList.add('hidden'); }, 2000);
    } catch (err) {
        const detail = err?.data?.detail;
        const msg = Array.isArray(detail) ? detail.map(d => d.msg).join(', ') : (detail || '회원가입에 실패했습니다.');
        showMsg(errorEl, msg);
    } finally {
        setBtn(btn, false, '가입하기');
    }
}

function logout() {
    clearInterval(pollingInterval);
    sessionStorage.removeItem('salpyobom_token');
    location.reload();
}

function startPolling() {
    pollingInterval = setInterval(() => {
        loadActiveSituations();
        loadDashboardSummary();
    }, 30000);
}

function initSidebarToggle() {
    const sidebar = el('main-sidebar');
    const overlay = el('sidebar-overlay');

    const open  = () => { sidebar.classList.add('sidebar-open');    overlay.classList.add('active'); };
    const close = () => { sidebar.classList.remove('sidebar-open'); overlay.classList.remove('active'); };

    on('btn-menu', 'click', open);
    overlay?.addEventListener('click', close);
}

// ══════════════════════════════════════════════════
// 페이지 네비게이션
// ══════════════════════════════════════════════════

function navigateTo(page) {
    // 페이지 전환
    ['dashboard', 'patients', 'report'].forEach(p => {
        el(`page-${p}`)?.classList.toggle('hidden', p !== page);
    });

    // 헤더 타이틀 변경
    setText('page-title', PAGE_TITLES[page] || '');

    // 사이드바 활성 링크 갱신
    document.querySelectorAll('.nav-link').forEach(a => {
        const isActive = a.dataset.page === page;
        a.classList.toggle('text-white',       isActive);
        a.classList.toggle('bg-white/10',      isActive);
        a.classList.toggle('border-r-4',       isActive);
        a.classList.toggle('border-green-400', isActive);
        a.classList.toggle('font-medium',      isActive);
        a.classList.toggle('text-green-200',   !isActive);
        // 아이콘 색상
        const icon = a.querySelector('i');
        if (icon) icon.classList.toggle('text-green-300', isActive);
    });

    // 페이지별 데이터 로드
    if (page === 'patients') loadPatientsPage();
    if (page === 'report')   loadReportPage();
}

function initNavLinks() {
    document.querySelectorAll('.nav-link').forEach(a => {
        a.addEventListener('click', e => {
            e.preventDefault();
            navigateTo(a.dataset.page);
        });
    });
}

// ══════════════════════════════════════════════════
// 대시보드
// ══════════════════════════════════════════════════

async function showDashboard() {
    el('login-screen')   .style.display = 'none';
    el('dashboard-wrap') .style.display = 'flex';

    initClock();
    initSidebarToggle();
    initNavLinks();

    on('btn-logout',       'click', logout);
    on('btn-back-to-list', 'click', () => el('situations-panel')?.scrollIntoView({ behavior: 'smooth' }));

    try {
        const user = await API.me();
        setText('sidebar-username', user.username);
        setText('sidebar-email',    user.email);
        currentUserEmail = user.email || '';  // 보고서 발송 기본 수신자
    } catch (_) {}

    navigateTo('dashboard');
    loadDashboardSummary();
    loadActiveSituations();
    loadAllPatients();
    startPolling();
}

async function loadDashboardSummary() {
    try {
        const { data: d } = await API.getDashboardSummary();
        el('stat-emergency').textContent = String(d.emergency_count).padStart(2, '0');
        el('stat-warning')  .textContent = String(d.warning_count).padStart(2, '0');
        el('stat-normal')   .textContent = String(d.normal_count).padStart(2, '0');
        el('stat-total')    .textContent = d.total_monitoring_count;
    } catch (_) {}
}

async function loadActiveSituations() {
    try {
        const { data } = await API.getActiveSituations();
        renderSituationsTable(data.situations);
    } catch (_) {
        el('active-situations-tbody').innerHTML =
            '<tr><td colspan="5" class="px-6 py-8 text-center text-red-400 text-sm">데이터를 불러오지 못했습니다.</td></tr>';
    }
}

async function loadAllPatients() {
    try {
        const { data } = await API.listAllPatients();
        const sorted = [...data.patients].sort((a, b) => levelOrder(a.cross_verification_level) - levelOrder(b.cross_verification_level));
        renderPatientsTable(sorted);
    } catch (_) {
        el('patients-tbody').innerHTML =
            '<tr><td colspan="3" class="px-6 py-8 text-center text-red-400 text-sm">데이터를 불러오지 못했습니다.</td></tr>';
    }
}

function levelOrder(level) {
    if (!level) return 3;
    if (level.includes('A') || level.includes('긴급')) return 0;
    if (level.includes('B') || level.includes('높음')) return 1;
    return 2;
}

// ══════════════════════════════════════════════════
// 상황 테이블 렌더링 (대시보드)
// ══════════════════════════════════════════════════

function renderSituationsTable(situations) {
    const tbody = el('active-situations-tbody');
    if (!situations?.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-8 text-center text-slate-400 text-sm">현재 활성 상황이 없습니다.</td></tr>';
        return;
    }

    tbody.innerHTML = situations.map((s, idx) => situationRow(s, idx === 0)).join('');

    tbody.querySelectorAll('tr[data-patient-id]').forEach(row => {
        row.addEventListener('click', () => {
            tbody.querySelectorAll('tr').forEach(r => r.classList.remove('active-row'));
            row.classList.add('active-row');
            loadPatientDetail(row.dataset.patientId, +row.dataset.situationId);
            if (window.innerWidth < 1024) {
                el('detail-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

function situationRow(s, isFirst) {
    const badgeCls = getCategoryBadge(s.category);
    const rowCls   = isFirst
        ? 'active-row cursor-pointer transition-colors'
        : `hover:bg-slate-50 cursor-pointer transition-colors${s.action_status === '조치 완료' ? ' opacity-70' : ''}`;

    return `
    <tr class="${rowCls}" data-situation-id="${s.situation_id}" data-patient-id="${s.patient_id}">
        <td class="px-3 lg:px-6 py-3 lg:py-4">
            <div class="font-bold text-slate-800 text-sm">${s.name}</div>
            <div class="text-[10px] text-slate-500">${s.address_summary}</div>
        </td>
        <td class="px-3 lg:px-6 py-3 lg:py-4"><span class="px-2 py-0.5 ${badgeCls} text-[10px] font-black rounded border">${s.category}</span></td>
        <td class="hidden md:table-cell px-3 lg:px-6 py-3 lg:py-4 text-sm text-slate-600">${s.detail_reason || '-'}</td>
        <td class="hidden sm:table-cell px-3 lg:px-6 py-3 lg:py-4 text-xs font-mono text-slate-400">${formatTime(s.occurred_at)}</td>
        <td class="px-3 lg:px-6 py-3 lg:py-4 text-center">${getStatusCell(s.action_status)}</td>
    </tr>`;
}

function getCategoryBadge(category) {
    const match = Object.entries(CATEGORY_BADGE).find(([key]) => category.includes(key));
    return match ? match[1] : 'bg-slate-100 text-slate-600 border-slate-200';
}

function getStatusCell(status) {
    if (status === '조치 대기')
        return `<div class="flex items-center justify-center gap-1.5"><span class="w-1.5 h-1.5 bg-red-500 rounded-full pulse-red"></span><span class="text-[11px] font-bold text-red-600">조치 대기</span></div>`;
    if (status === '현장 출동')
        return `<div class="flex items-center justify-center gap-1.5"><span class="w-1.5 h-1.5 bg-green-500 rounded-full"></span><span class="text-[11px] font-bold text-green-600">현장 출동</span></div>`;
    return `<span class="text-[11px] font-bold text-slate-400">조치 완료</span>`;
}

function formatTime(iso) {
    if (!iso) return '--:--:--';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const p = n => String(n).padStart(2, '0');
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function formatDateTime(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

// ══════════════════════════════════════════════════
// 전체 환자 테이블 렌더링 (대시보드)
// ══════════════════════════════════════════════════

function renderPatientsTable(patients) {
    const tbody = el('patients-tbody');
    if (!patients?.length) {
        tbody.innerHTML = '<tr><td colspan="3" class="px-6 py-8 text-center text-slate-400 text-sm">대상자가 없습니다.</td></tr>';
        return;
    }

    tbody.innerHTML = patients.map((p, idx) => patientRow(p, idx === 0)).join('');

    tbody.querySelectorAll('tr[data-patient-id]').forEach(row => {
        row.addEventListener('click', () => {
            tbody.querySelectorAll('tr').forEach(r => r.classList.remove('active-row'));
            row.classList.add('active-row');
            loadPatientDetail(row.dataset.patientId, null);
            if (window.innerWidth < 1024) {
                el('detail-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    loadPatientDetail(patients[0].patient_id, null);
}

function patientRow(p, isFirst) {
    const lvlCls = getLevelBadge(p.cross_verification_level);
    const rowCls = isFirst
        ? 'active-row cursor-pointer transition-colors'
        : 'hover:bg-slate-50 cursor-pointer transition-colors';

    return `
    <tr class="${rowCls}" data-patient-id="${p.patient_id}">
        <td class="px-3 lg:px-6 py-3 lg:py-4">
            <div class="font-bold text-slate-800 text-sm">${p.name}</div>
            <div class="text-[10px] text-slate-500">${p.address_summary}</div>
        </td>
        <td class="px-3 lg:px-6 py-3 lg:py-4">
            <span class="px-2 py-0.5 ${lvlCls} text-[10px] font-black rounded border">${p.cross_verification_level || '-'}</span>
        </td>
        <td class="px-3 lg:px-6 py-3 lg:py-4 text-xs text-slate-500">${p.manager_name || '-'}</td>
    </tr>`;
}

function getLevelBadge(level) {
    if (!level) return 'bg-slate-100 text-slate-600 border-slate-200';
    if (level.includes('A') || level.includes('긴급')) return 'bg-red-100 text-red-600 border-red-200';
    if (level.includes('B') || level.includes('높음')) return 'bg-orange-100 text-orange-600 border-orange-200';
    return 'bg-green-100 text-green-700 border-green-200';
}

// ══════════════════════════════════════════════════
// 환자 상세 패널
// ══════════════════════════════════════════════════

async function loadPatientDetail(patientId, situationId) {
    currentSituationId = situationId;
    syncActionButton();
    const overlay = el('detail-loading-overlay');
    overlay?.classList.add('active');
    try {
        const { data } = await API.getPatientDetails(patientId);
        renderDetailPanel(data);
    } catch (_) {
    } finally {
        overlay?.classList.remove('active');
    }
}

function syncActionButton() {
    const btn = el('btn-action-call');
    if (!btn) return;
    btn.disabled = !currentSituationId;
    btn.title = currentSituationId ? '유선 연락 조치 등록' : '상황을 선택하면 활성화됩니다';
}

function renderDetailPanel(d) {
    // ai_analysis / 방문 일정 등 일부 필드는 백엔드 미구현(보류) — 누락 시 빈 객체로 폴백해 패널이 깨지지 않게 한다.
    const ai  = d.ai_analysis   || {};
    const adm = d.administration || {};

    setText('detail-doc-no',      `전자 문서 열람: No.${d.doc_no || '---'}`);
    setText('detail-name',        d.name);
    // 백엔드 age 는 이미 "만 N세" 문자열 → 그대로 괄호로 감싼다.
    setText('detail-age',         d.age ? `(${d.age})` : '');
    setText('detail-address',     d.address_full);
    setText('detail-alert-title', ai.alert_title);
    setText('detail-alert-desc',  ai.alert_desc);
    setText('detail-manager',     adm.manager_name);
    setText('detail-level',       adm.management_level);
    setText('detail-visit-time',  adm.next_visit_time);
    setText('detail-visit-plan',  adm.next_visit_plan);

    const imgEl         = el('detail-image');
    const placeholderEl = el('detail-image-placeholder');
    const showImg = (show) => {
        imgEl.style.display         = show ? 'block' : 'none';
        placeholderEl.style.display = show ? 'none'  : 'block';
    };
    imgEl.onerror = function() { showImg(false); this.onerror = null; };
    if (d.profile_image_url) {
        imgEl.src = d.profile_image_url;
        showImg(true);
    } else {
        imgEl.src = '';
        showImg(false);
    }

    const lvl  = ai.cross_verification_level || '';
    const type = lvl.includes('A') || lvl.includes('긴급') ? 'emergency'
               : lvl.includes('B') || lvl.includes('높음') ? 'warning'
               : 'normal';
    updateAlertTheme(type);
    renderDiseaseTags(adm.diseases || []);
}

function updateAlertTheme(type) {
    const theme = ALERT_THEMES[type] ?? ALERT_THEMES.normal;
    el('detail-alert-box')  .className = theme.box;
    el('detail-alert-icon') .className = theme.icon;
    el('detail-alert-title').className = theme.title;
}

function renderDiseaseTags(diseases) {
    el('detail-diseases').innerHTML = diseases
        .map(d => `<span class="px-2 py-0.5 bg-slate-100 text-[10px] font-bold rounded">${d}</span>`)
        .join('');
}

// ══════════════════════════════════════════════════
// 조치 버튼
// ══════════════════════════════════════════════════

on('btn-action-call', 'click', () => submitAction('유선 연락', null, '조치 완료'), true);

async function submitAction(actionType, note, statusUpdate) {
    if (!currentSituationId) return;
    try {
        await API.createAction(currentSituationId, actionType, note, statusUpdate);
        showToast('조치가 등록되었습니다.');
        loadActiveSituations();
        loadDashboardSummary();
    } catch (_) {
        showToast('등록에 실패했습니다. 다시 시도해주세요.', 'error');
    }
}

// ══════════════════════════════════════════════════
// 대상자 DB 페이지
// ══════════════════════════════════════════════════

async function loadPatientsPage() {
    const tbody = el('db-patients-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-12 text-center text-slate-400 text-sm">데이터를 불러오는 중...</td></tr>';

    try {
        const { data } = await API.listAllPatients();
        const sorted = [...data.patients].sort((a, b) => levelOrder(a.cross_verification_level) - levelOrder(b.cross_verification_level));

        setText('db-patient-count', `총 ${sorted.length}명`);

        if (!sorted.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-12 text-center text-slate-400 text-sm">등록된 대상자가 없습니다.</td></tr>';
            return;
        }

        tbody.innerHTML = sorted.map((p, i) => `
        <tr class="hover:bg-slate-50 transition-colors">
            <td class="px-6 py-3 text-xs text-slate-400 font-mono">${String(i + 1).padStart(3, '0')}</td>
            <td class="px-6 py-3 font-bold text-slate-800 text-sm">${p.name}</td>
            <td class="px-6 py-3 text-xs text-slate-500">${p.address_summary}</td>
            <td class="px-6 py-3">
                <span class="px-2 py-0.5 ${getLevelBadge(p.cross_verification_level)} text-[10px] font-black rounded border">
                    ${p.cross_verification_level || '-'}
                </span>
            </td>
            <td class="px-6 py-3 text-xs text-slate-500">${p.manager_name || '-'}</td>
        </tr>`).join('');
    } catch (_) {
        tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-12 text-center text-red-400 text-sm">데이터를 불러오지 못했습니다.</td></tr>';
    }
}

// ══════════════════════════════════════════════════
// 보고서 조회 페이지
// ══════════════════════════════════════════════════

async function loadReportPage() {
    el('report-output') .classList.add('hidden');
    el('report-loading').classList.remove('hidden');

    try {
        const { data } = await API.listReports();

        setText('report-today-count', data.today_count);

        // 요약 통계 (위험/주의/사망/전체 — 전 기간 이력 기준)
        el('report-stats').innerHTML = `
            <div class="bg-red-50 border border-red-100 rounded p-4 text-center">
                <p class="text-[10px] font-bold text-red-400 mb-1">위험</p>
                <p class="text-3xl font-black text-red-600">${data.risk_count}</p>
            </div>
            <div class="bg-orange-50 border border-orange-100 rounded p-4 text-center">
                <p class="text-[10px] font-bold text-orange-400 mb-1">주의</p>
                <p class="text-3xl font-black text-orange-600">${data.caution_count}</p>
            </div>
            <div class="bg-slate-100 border border-slate-200 rounded p-4 text-center">
                <p class="text-[10px] font-bold text-slate-500 mb-1">사망</p>
                <p class="text-3xl font-black text-slate-700">${data.death_count}</p>
            </div>
            <div class="bg-slate-50 border border-slate-200 rounded p-4 text-center">
                <p class="text-[10px] font-bold text-slate-400 mb-1">전체 보고서</p>
                <p class="text-3xl font-black text-slate-700">${data.total}</p>
            </div>`;

        // 일자별 그룹 목록 (전 기간, 최신일 우선)
        const wrap = el('report-list-wrap');
        if (!data.groups.length) {
            wrap.innerHTML = '<div class="bg-white rounded shadow-sm p-12 text-center text-slate-400 text-sm">생성된 보고서가 없습니다.</div>';
        } else {
            const now      = new Date();
            const pad      = n => String(n).padStart(2, '0');
            const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
            wrap.innerHTML = data.groups.map(g => reportDayGroup(g, g.date === todayStr)).join('');
            wrap.querySelectorAll('button[data-report-id]').forEach(btn => {
                btn.addEventListener('click', () => openReport(+btn.dataset.reportId));
            });
            wrap.querySelectorAll('button[data-email-id]').forEach(btn => {
                btn.addEventListener('click', () => sendReportEmail(btn));
            });
            wrap.querySelectorAll('button[data-more-day]').forEach(btn => {
                btn.addEventListener('click', () => expandReportDay(btn.dataset.moreDay));
            });
        }

        el('report-loading').classList.add('hidden');
        el('report-output') .classList.remove('hidden');

    } catch (_) {
        el('report-loading').innerHTML = '<p class="text-red-400 text-sm">보고서를 불러오지 못했습니다.</p>';
    }
}

// 일자 그룹당 처음 보여줄 보고서 행 수 (초과분은 '더보기'로 펼친다).
const REPORT_ROWS_PER_DAY = 5;

function reportDayGroup(g, isToday) {
    const day = g.date;  // data 속성 키 (그룹 식별용)
    // 처음 5개만 노출, 나머지는 숨김 행으로 미리 렌더해 '더보기' 클릭 시 펼친다.
    const rows = g.items
        .map((r, i) => reportRow(r, i >= REPORT_ROWS_PER_DAY ? day : null))
        .join('');
    const hidden = Math.max(0, g.count - REPORT_ROWS_PER_DAY);
    const moreRow = hidden
        ? `<tr data-more-row="${day}"><td colspan="5" class="px-4 py-2.5 text-center border-t border-slate-100">
                <button data-more-day="${day}" class="text-[11px] font-bold text-green-600 hover:text-green-700">
                    <i class="fa-solid fa-chevron-down mr-1"></i>더보기 (${hidden}건)
                </button>
            </td></tr>`
        : '';
    const todayBadge = isToday
        ? '<span class="ml-2 px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-black rounded">오늘</span>'
        : '';
    return `
    <div class="bg-white rounded shadow-sm overflow-hidden ${isToday ? 'ring-2 ring-green-300' : ''}">
        <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h4 class="text-xs font-bold text-slate-500 uppercase tracking-widest">${formatDate(g.date)}${todayBadge}</h4>
            <span class="text-[11px] font-bold text-slate-400">${g.count}건</span>
        </div>
        <table class="w-full text-left">
            <thead class="bg-slate-50">
                <tr class="text-[11px] text-slate-400 font-bold uppercase tracking-wider">
                    <th class="px-4 py-2.5">대상자</th>
                    <th class="px-4 py-2.5">위험도</th>
                    <th class="px-4 py-2.5">제목</th>
                    <th class="px-4 py-2.5">이메일 발송</th>
                    <th class="px-4 py-2.5 text-right">보고서</th>
                </tr>
            </thead>
            <tbody>${rows}${moreRow}</tbody>
        </table>
    </div>`;
}

// '더보기' 클릭 — 해당 일자의 숨김 행을 모두 펼치고 버튼 행을 제거한다.
function expandReportDay(day) {
    const esc = (window.CSS && CSS.escape) ? CSS.escape(day) : day;
    document.querySelectorAll(`tr[data-extra-row="${esc}"]`).forEach(tr => {
        tr.style.display = '';
    });
    document.querySelector(`tr[data-more-row="${esc}"]`)?.remove();
}

// hiddenDay 가 주어지면(처음 5건 초과) '더보기' 전까지 숨겨두는 행으로 렌더한다.
function reportRow(r, hiddenDay = null) {
    // 발송 버튼에 넘길 .docx 파일명 (저장된 file_name 은 PDF — 서버가 변환).
    const docxName = r.file_name.replace(/\.pdf$/i, '.docx');
    const hideAttr = hiddenDay ? ` data-extra-row="${hiddenDay}" style="display:none"` : '';
    const emailed = r.emailed_at
        ? `<span class="text-[11px] text-green-600 font-bold"><i class="fa-solid fa-circle-check mr-1"></i>발송 완료</span><span class="block text-[10px] text-slate-400 font-mono">${formatDateTime(r.emailed_at)}</span>`
        : `<button data-email-id="${r.id}" data-email-file="${docxName}" data-email-patient="${r.patient_name}"
                class="px-2.5 py-1 bg-white border border-green-300 text-green-600 hover:bg-green-50 text-[11px] font-bold rounded transition-colors">
                <i class="fa-solid fa-paper-plane mr-1"></i>발송
            </button>`;
    return `
    <tr class="border-t border-slate-100 hover:bg-slate-50"${hideAttr}>
        <td class="px-4 py-2.5 font-bold text-slate-800 text-sm">${r.patient_name}</td>
        <td class="px-4 py-2.5"><span class="px-2 py-0.5 ${getRiskBadge(r.risk_level)} text-[10px] font-black rounded border">${r.risk_level}</span></td>
        <td class="px-4 py-2.5 text-xs text-slate-600">${r.title}</td>
        <td class="px-4 py-2.5">${emailed}</td>
        <td class="px-4 py-2.5 text-right">
            <button data-report-id="${r.id}" class="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-[11px] font-bold rounded transition-colors">
                <i class="fa-solid fa-file-pdf mr-1"></i>PDF 보기
            </button>
        </td>
    </tr>`;
}

function getRiskBadge(risk) {
    if (risk === '위험') return 'bg-red-100 text-red-600 border-red-200';
    if (risk === '주의') return 'bg-orange-100 text-orange-600 border-orange-200';
    return 'bg-slate-200 text-slate-600 border-slate-300';  // 사망
}

function formatDate(iso) {
    if (!iso) return '-';
    const [y, m, d] = iso.split('-');
    return `${y}년 ${m}월 ${d}일`;
}

async function openReport(reportId) {
    try {
        await API.openReportPdf(reportId);
    } catch (_) {
        showToast('PDF 를 불러오지 못했습니다.', 'error');
    }
}

async function sendReportEmail(btn) {
    const { emailFile, emailPatient } = btn.dataset;
    const recipient = prompt(`${emailPatient} 보고서를 보낼 이메일 주소를 입력하세요.`, currentUserEmail);
    if (recipient === null) return;            // 취소
    if (!recipient.trim()) {
        showToast('이메일 주소를 입력하세요.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i>발송 중';
    try {
        await API.emailReport(emailFile, recipient.trim());
        showToast(`${recipient.trim()} 으로 발송했습니다.`, 'success');
        loadReportPage();                      // 발송 상태 갱신 (미발송 → 발송됨)
    } catch (_) {
        showToast('이메일 발송에 실패했습니다.', 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-paper-plane mr-1"></i>발송';
    }
}

// ══════════════════════════════════════════════════
// 실시간 시계
// ══════════════════════════════════════════════════

function initClock() {
    const update = () => {
        const now = new Date();
        const p   = n => String(n).padStart(2, '0');
        setText('current-time',
            `${now.getFullYear()}-${p(now.getMonth()+1)}-${p(now.getDate())} ${p(now.getHours())}:${p(now.getMinutes())}:${p(now.getSeconds())}`
        );
    };
    setInterval(update, 1000);
    update();
}

// ══════════════════════════════════════════════════
// DOM 유틸
// ══════════════════════════════════════════════════

function el(id)               { return document.getElementById(id); }
function val(id)              { return el(id).value.trim(); }
function setText(id, v)       { const e = el(id); if (e) e.textContent = v ?? '-'; }
function showMsg(el, msg)     { el.textContent = msg; el.classList.remove('hidden'); }
function setBtn(btn, disabled, text) { btn.disabled = disabled; btn.textContent = text; }
function on(id, event, handler, defer = false) {
    if (defer) {
        document.addEventListener(event, e => { if (e.target.closest(`#${id}`)) handler(e); });
    } else {
        const e = el(id);
        if (e) e.addEventListener(event, handler);
    }
}

function showToast(msg, type = 'success') {
    const container = el('toast-container');
    const palettes = {
        success: { bg: 'bg-green-600',  icon: 'fa-circle-check' },
        error:   { bg: 'bg-red-600',    icon: 'fa-circle-xmark' },
        info:    { bg: 'bg-gray-700',   icon: 'fa-circle-info'  },
    };
    const { bg, icon } = palettes[type] ?? palettes.info;

    const div = document.createElement('div');
    div.className = `flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-white text-sm font-bold ${bg} translate-x-full transition-transform duration-300 ease-out`;
    div.innerHTML = `<i class="fa-solid ${icon}"></i><span>${msg}</span>`;

    container.appendChild(div);
    requestAnimationFrame(() => requestAnimationFrame(() => div.classList.replace('translate-x-full', 'translate-x-0')));

    setTimeout(() => {
        div.classList.replace('translate-x-0', 'translate-x-full');
        div.addEventListener('transitionend', () => div.remove(), { once: true });
    }, 3000);
}
