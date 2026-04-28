const STATUS_STYLE = {
    SUCCESS: 'text-green-400',
    ERROR: 'text-red-400',
    LATENCY: 'text-yellow-400',
};

const ROW_BG = {
    ERROR: 'bg-red-900/30 border-red-700',
    LATENCY: 'bg-yellow-900/20 border-yellow-800',
};

export default function LogsView({ logs }) {
    if (!logs || logs.length === 0) {
        return <p className="text-slate-500 text-sm">No logs yet. Trigger a request to generate logs.</p>;
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
                <thead className="text-slate-400 border-b border-slate-700">
                    <tr>
                        <th className="py-2 px-2">Time</th>
                        <th className="py-2 px-2">Service</th>
                        <th className="py-2 px-2">Status</th>
                        <th className="py-2 px-2">Message</th>
                        <th className="py-2 px-2">Duration</th>
                        <th className="py-2 px-2">Trace ID</th>
                    </tr>
                </thead>
                <tbody>
                    {logs.map((log) => {
                        const isError = log.status === 'ERROR' || log.status === 'LATENCY';
                        const rowClass = ROW_BG[log.status] || '';
                        return (
                            <tr key={log.id} className={`border-b border-slate-800 hover:bg-slate-800/50 ${rowClass}`}>
                                <td className="py-1.5 px-2 text-slate-500">{new Date(log.timestamp).toLocaleTimeString()}</td>
                                <td className="py-1.5 px-2 text-white font-mono">{log.service_name}</td>
                                <td className={`py-1.5 px-2 font-bold ${STATUS_STYLE[log.status] || 'text-slate-300'}`}>
                                    {isError ? '⚠️ ' : ''}{log.status}
                                </td>
                                <td className="py-1.5 px-2 text-slate-400 max-w-xs truncate">{log.message || log.error_type || '—'}</td>
                                <td className="py-1.5 px-2 text-slate-400">{log.duration_ms ? `${log.duration_ms}ms` : '—'}</td>
                                <td className="py-1.5 px-2 text-slate-600 font-mono">{log.trace_id?.substring(0, 8)}</td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}