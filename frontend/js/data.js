/**
 * 살펴봄 API 클라이언트
 */

// 현재 접속한 호스트의 :8000 백엔드를 가리킨다.
//   - 로컬 개발: http://localhost:3000 → http://localhost:8000/api/v1
//   - 운영(kro.kr): http://salpyeobom.kro.kr → http://salpyeobom.kro.kr:8000/api/v1
const API_BASE = `http://${location.hostname}:8000/api/v1`;

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
