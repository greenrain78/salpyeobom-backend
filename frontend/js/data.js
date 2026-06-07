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
    listPatients:         (limit=100)     => apiRequest('GET', `/patients?limit=${limit}`),
    getPatientDetails:    (patientId)     => apiRequest('GET', `/patients/${patientId}/details`),

    // 조치 등록
    createAction: (situationId, actionType, actionNote, statusUpdate) =>
        apiRequest('POST', `/situations/${situationId}/actions`, {
            action_type:   actionType,
            action_note:   actionNote || null,
            status_update: statusUpdate,
        }),
};
