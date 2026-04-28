export default function TrafficMetrics({ stats }) {
    if (!stats) return null;

    const { total, success, errors, latency, avg_duration, latency_threshold_ms, exception_threshold } = stats;
    const errorRate = total > 0 ? ((errors / total) * 100).toFixed(1) : 0;
    const isHighLatency = avg_duration >= latency_threshold_ms;
    const isHighErrorRate = errors >= exception_threshold;

    const metrics = [
        { label: 'Total Requests', value: total, color: 'text-blue-400' },
        { label: 'Success', value: success, color: 'text-green-400' },
        { label: 'Errors', value: errors, color: errors > 0 ? 'text-red-400' : 'text-green-400', sub: `threshold: ${exception_threshold}` },
        { label: 'Latency Issues', value: latency, color: latency > 0 ? 'text-yellow-400' : 'text-green-400' },
        { label: 'Avg Duration', value: `${avg_duration}ms`, color: isHighLatency ? 'text-red-400' : 'text-purple-400', sub: `threshold: ${latency_threshold_ms}ms` },
        { label: 'Error Rate', value: `${errorRate}%`, color: isHighErrorRate ? 'text-red-400' : 'text-green-400' },
    ];

    return (
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {metrics.map(m => (
                <div key={m.label} className="bg-slate-800/50 rounded-lg p-3 text-center border border-slate-700">
                    <p className={`text-xl font-bold ${m.color}`}>{m.value}</p>
                    <p className="text-xs text-slate-500">{m.label}</p>
                    {m.sub && <p className="text-[10px] text-slate-600 mt-0.5">{m.sub}</p>}
                </div>
            ))}
        </div>
    );
}