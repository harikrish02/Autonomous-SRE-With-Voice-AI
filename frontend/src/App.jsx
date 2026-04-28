import { useCallback } from 'react';
import { usePolling } from './hooks/usePolling';
import { getAllStatuses, getLogs, getIncidents, getLogStats } from './api/client';
import ServiceCard from './components/ServiceCard';
import TrafficMetrics from './components/TrafficMetrics';
import IncidentTimeline from './components/IncidentTimeline';
import LogsView from './components/LogsView';
import ActionPanel from './components/ActionPanel';

const SERVICES = ['service-a', 'service-b', 'service-c'];

export default function App() {
    const fetchStatuses = useCallback(() => getAllStatuses(), []);
    const fetchLogs = useCallback(() => getLogs('limit=30'), []);
    const fetchIncidents = useCallback(() => getIncidents('limit=5'), []);
    const fetchStats = useCallback(() => getLogStats(), []);

    const statuses = usePolling(fetchStatuses, 5000);
    const logs = usePolling(fetchLogs, 4000);
    const incidents = usePolling(fetchIncidents, 5000);
    const stats = usePolling(fetchStats, 5000);

    const refreshAll = () => {
        statuses.refresh();
        logs.refresh();
        incidents.refresh();
        stats.refresh();
    };

    const getStatus = (name) => {
        if (!statuses.data) return { status: 'unknown', replicas: 0 };
        const found = statuses.data.find(s => s.service_name === name);
        return found || { status: 'unknown', replicas: 0 };
    };

    return (
        <div className="min-h-screen bg-slate-900 text-slate-200">
            {/* Header */}
            <header className="border-b border-slate-700 bg-slate-800/50 px-6 py-4">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-white">🛡️ Autonomous - Command Center</h1>
                        <p className="text-sm text-slate-400">AI-Powered Incident Detection & Auto-Remediation</p>
                    </div>
                    <button onClick={refreshAll} className="px-4 py-2 text-sm rounded bg-slate-700 hover:bg-slate-600 text-white">
                        🔄 Refresh
                    </button>
                </div>
            </header>

            <main className="max-w-7xl mx-auto p-6 space-y-6">
                {/* Service Status Cards */}
                <section>
                    <h2 className="text-lg font-semibold text-white mb-3">Service Status</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {SERVICES.map(name => {
                            const s = getStatus(name);
                            return <ServiceCard key={name} name={name} status={s.status} replicas={s.replicas} onAction={refreshAll} />;
                        })}
                    </div>
                </section>

                {/* Traffic Metrics */}
                <section>
                    <h2 className="text-lg font-semibold text-white mb-3">Traffic Metrics</h2>
                    <TrafficMetrics stats={stats.data} />
                </section>

                {/* Action Panel */}
                <section>
                    <h2 className="text-lg font-semibold text-white mb-3">Actions & Simulation</h2>
                    <ActionPanel onAction={refreshAll} />
                </section>

                {/* Incidents */}
                <section>
                    <h2 className="text-lg font-semibold text-white mb-3">
                        Incidents {incidents.data?.length > 0 && <span className="text-sm text-red-400">({incidents.data.length})</span>}
                    </h2>
                    <div className="max-h-[400px] overflow-y-auto pr-1">
                        <IncidentTimeline incidents={incidents.data} onAction={refreshAll} />
                    </div>
                </section>

                {/* Logs */}
                <section>
                    <h2 className="text-lg font-semibold text-white mb-3">
                        Logs {logs.data?.length > 0 && <span className="text-sm text-slate-500">({logs.data.length})</span>}
                    </h2>
                    <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4">
                        <LogsView logs={logs.data} />
                    </div>
                </section>
            </main>

            <footer className="border-t border-slate-700 text-center py-4 text-xs text-slate-600">
                DevOps Auto-Remediation Platform • Polling every 5s
            </footer>
        </div>
    );
}
