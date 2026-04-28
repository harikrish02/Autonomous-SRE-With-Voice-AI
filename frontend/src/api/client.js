const ADMIN_URL = '/api';
const SERVICE_A_URL = '/service-a';

export async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || res.statusText);
    }
    return res.json();
}

// --- Logs ---
export const getLogs = (params = '') => fetchJson(`${ADMIN_URL}/logs/${params ? '?' + params : ''}`);
export const getLogStats = () => fetchJson(`${ADMIN_URL}/logs/stats`);

// --- Incidents ---
export const getIncidents = (params = '') => fetchJson(`${ADMIN_URL}/incidents/${params ? '?' + params : ''}`);
export const getIncident = (id) => fetchJson(`${ADMIN_URL}/incidents/${id}`);

// --- Service Status ---
export const getAllStatuses = () => fetchJson(`${ADMIN_URL}/infra/status`);
export const getServiceStatus = (name) => fetchJson(`${ADMIN_URL}/infra/status/${name}`);

// --- Infra Actions ---
export const restartService = (name, incidentId) =>
    fetchJson(`${ADMIN_URL}/infra/restart/${name}${incidentId ? '?incident_id=' + incidentId : ''}`, { method: 'POST' });
export const scaleService = (name, replicas = 2, incidentId) =>
    fetchJson(`${ADMIN_URL}/infra/scale/${name}?replicas=${replicas}${incidentId ? '&incident_id=' + incidentId : ''}`, { method: 'POST' });
export const stopService = (name) =>
    fetchJson(`${ADMIN_URL}/infra/stop/${name}`, { method: 'POST' });

// --- Simulation ---
export const simulateHighLatency = (name) =>
    fetchJson(`${ADMIN_URL}/infra/simulate/high-latency/${name}`, { method: 'POST' });
export const simulatePythonError = (name) =>
    fetchJson(`${ADMIN_URL}/infra/simulate/python-error/${name}`, { method: 'POST' });

// --- Approval ---
export const approveIncident = (id) => fetchJson(`${ADMIN_URL}/approval/approve/${id}`, { method: 'POST' });
export const rejectIncident = (id) => fetchJson(`${ADMIN_URL}/approval/reject/${id}`, { method: 'POST' });
export const notifyIncident = (id) => fetchJson(`${ADMIN_URL}/approval/notify/${id}`, { method: 'POST' });
export const resolveIncident = (id) => fetchJson(`${ADMIN_URL}/approval/resolve/${id}`, { method: 'POST' });

// --- Legacy Simulation ---
export const triggerProcess = (fail, failAt) => {
    let url = `${SERVICE_A_URL}/process`;
    const params = [];
    if (fail) params.push(`fail=${fail}`);
    if (failAt) params.push(`fail_at=${failAt}`);
    if (params.length) url += '?' + params.join('&');
    return fetch(url).then(r => r.json().catch(() => r.text()));
};

// --- Health ---
export const checkHealth = (port) => fetch(`http://localhost:${port}/health`).then(r => r.json()).catch(() => null);