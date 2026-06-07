/**
 * 살펴봄 API 클라이언트
 */

// API 베이스 주소를 접속 환경에 따라 결정한다.
//   - 로컬 개발(poe dev): localhost:3000 → 별도 백엔드 localhost:8000/api/v1
//   - 터널/배포: 백엔드가 정적 프론트까지 같이 서빙하므로 같은 origin 사용
//     (예: https://xxx.trycloudflare.com → https://xxx.trycloudflare.com/api/v1)
const API_BASE =
    location.hostname === 'localhost' || location.hostname === '127.0.0.1'
        ? `http://${location.hostname}:8000/api/v1`
        : `${location.origin}/api/v1`;

function getToken() {
    return sessionStorage.getItem('salpyobom_token');
}

function buildHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

async function apiRequest(method, path, body = null) {
    const res = await fetch(API_BASE + path, {
        method,
        headers: buildHeaders(),
        body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json();
    if (!res.ok) throw { status: res.status, data };
    return data;
}

const API = {
    // 인증
    login:    (username, password)        => apiRequest('POST', '/auth/login',    { username, password }),
    register: (username, email, password) => apiRequest('POST', '/auth/register', { username, email, password }),
    me:       ()                          => apiRequest('GET',  '/auth/me'),

    // 대시보드
    getDashboardSummary:  ()              => apiRequest('GET', '/dashboard/summary'),
    getActiveSituations:  (limit=50)      => apiRequest('GET', `/situations/active?limit=${limit}`),
    listPatients:         (page=1, limit=200) => apiRequest('GET', `/patients?page=${page}&limit=${limit}`),
    // 모든 페이지를 끝까지 받아 합친다 (대상자 100명 초과 시 누락 방지).
    listAllPatients: async (pageSize=200) => {
        const first = await API.listPatients(1, pageSize);
        const totalPages = first.data.total_pages || 1;
        if (totalPages <= 1) return first;
        const rest = await Promise.all(
            Array.from({ length: totalPages - 1 }, (_, i) =>
                API.listPatients(i + 2, pageSize))
        );
        const patients = rest.reduce(
            (acc, r) => acc.concat(r.data.patients),
            [...first.data.patients]
        );
        return { ...first, data: { ...first.data, patients } };
    },
    getPatientDetails:    (patientId)     => apiRequest('GET', `/patients/${patientId}/details`),

    // 보고서
    listReports:          (date=null)     => apiRequest('GET', `/reports${date ? `?date=${date}` : ''}`),

    // 보고서 PDF — 인증 헤더가 필요해 blob 으로 받아 새 탭에 연다 (a href 로는 토큰 전달 불가).
    openReportPdf: async (reportId) => {
        const res = await fetch(`${API_BASE}/reports/${reportId}/file`, { headers: buildHeaders() });
        if (!res.ok) throw { status: res.status };
        const url = URL.createObjectURL(await res.blob());
        window.open(url, '_blank');
        setTimeout(() => URL.revokeObjectURL(url), 60000);
    },

    // 조치 등록
    createAction: (situationId, actionType, actionNote, statusUpdate) =>
        apiRequest('POST', `/situations/${situationId}/actions`, {
            action_type:   actionType,
            action_note:   actionNote || null,
            status_update: statusUpdate,
        }),
};
