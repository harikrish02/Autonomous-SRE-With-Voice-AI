import { useState } from 'react';
import { restartService, scaleService } from '../api/client';

export default function ActionPanel({ onAction }) {
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const exec = async (label, fn) => {
        setLoading(true);
        setResult(null);
        try {
            const r = await fn();
            setResult({ ok: true, text: `${label}: ${r.message || JSON.stringify(r).substring(0, 150)}` });
        } catch (e) {
            setResult({ ok: false, text: `${label}: ${e.message?.substring(0, 150)}` });
        }
        setLoading(false);
        if (onAction) onAction();
    };

    return (
        <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
                {['service-a', 'service-b', 'service-c'].map(s => (
                    <button key={s} disabled={loading} onClick={() => exec(`Restart ${s}`, () => restartService(s))}
                        className="px-3 py-1.5 text-xs rounded bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50">
                        🔄 Restart {s}
                    </button>
                ))}
                {['service-a', 'service-b', 'service-c'].map(s => (
                    <button key={`scale-${s}`} disabled={loading} onClick={() => exec(`Scale ${s}`, () => scaleService(s, 3))}
                        className="px-3 py-1.5 text-xs rounded bg-teal-600 hover:bg-teal-700 text-white disabled:opacity-50">
                        ⬆️ Scale {s}
                    </button>
                ))}
            </div>
            {result && (
                <div className={`text-xs p-2 rounded ${result.ok ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>
                    {result.text}
                </div>
            )}
        </div>
    );
}