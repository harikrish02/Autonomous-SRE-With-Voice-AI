import { useState } from 'react';
import { stopService, simulateHighLatency, simulatePythonError } from '../api/client';

export default function ServiceCard({ name, status, replicas, onAction }) {
    const [simulating, setSimulating] = useState(false);
    const [result, setResult] = useState(null);
    const isUp = status === 'running' || status === 'healthy';
    const displayName = name.replace('service-', 'Service ').toUpperCase();

    const exec = async (label, fn) => {
        setSimulating(true);
        setResult(null);
        try {
            const r = await fn();
            setResult({ ok: true, text: `${label}: ${r.message || 'Done'}` });
        } catch (e) {
            setResult({ ok: false, text: `${label}: ${e.message?.substring(0, 100)}` });
        }
        setSimulating(false);
        if (onAction) onAction();
    };

    let errorLabel = "Python Error";
    if (name === "service-a") errorLabel = "Business Err.";
    if (name === "service-b") errorLabel = "Auth error";
    if (name === "service-c") errorLabel = "DB Deadlock";

    return (
        <div className={`rounded-xl border-2 p-5 ${isUp ? 'border-green-500 bg-green-500/10' : 'border-red-500 bg-red-500/10'}`}>
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-bold text-white">{displayName}</h3>
                <span className={`inline-block w-3 h-3 rounded-full ${isUp ? 'bg-green-400' : 'bg-red-400'} animate-pulse`} />
            </div>
            <p className="text-sm text-slate-400 mb-1">Status: <span className={isUp ? 'text-green-300' : 'text-red-300'}>{status}</span></p>
            <p className="text-sm text-slate-400 mb-4">Replicas: {replicas}</p>
            <div className="flex flex-wrap gap-2">
                <button disabled={simulating} onClick={() => exec('Service Down', () => stopService(name))}
                    className="px-3 py-1 text-xs rounded bg-red-600 hover:bg-red-700 text-white disabled:opacity-50">
                    ⛔ Service Down
                </button>
                <button disabled={simulating} onClick={() => exec('High Latency', () => simulateHighLatency(name))}
                    className="px-3 py-1 text-xs rounded bg-yellow-600 hover:bg-yellow-700 text-white disabled:opacity-50">
                    🐌 High Latency
                </button>
                <button disabled={simulating} onClick={() => exec(errorLabel, () => simulatePythonError(name))}
                    className="px-3 py-1 text-xs rounded bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-50">
                    🐛 {errorLabel}
                </button>
            </div>
            {result && (
                <p className={`text-xs mt-2 ${result.ok ? 'text-green-400' : 'text-red-400'}`}>{result.text}</p>
            )}
        </div>
    );
}