import { useState } from 'react';
import { approveIncident, rejectIncident, resolveIncident } from '../api/client';

const STATUS_COLORS = {
    DETECTED: 'bg-red-500',
    ANALYZED: 'bg-orange-500',
    USER_NOTIFIED: 'bg-yellow-500',
    APPROVED: 'bg-blue-500',
    ACTION_TAKEN: 'bg-indigo-500',
    TRANSFERRED: 'bg-purple-600',
    RESOLVED: 'bg-green-500',
    REJECTED: 'bg-gray-500',
};

export default function IncidentTimeline({ incidents, onAction }) {
    const [acting, setActing] = useState(null);

    const handle = async (id, action) => {
        setActing(id);
        try {
            if (action === 'approve') await approveIncident(id);
            else if (action === 'reject') await rejectIncident(id);
            else if (action === 'resolve') await resolveIncident(id);
            if (onAction) onAction();
        } catch (e) { /* ignore */ }
        setActing(null);
    };

    if (!incidents || incidents.length === 0) {
        return <p className="text-slate-500 text-sm">No incidents detected yet.</p>;
    }

    return (
        <div className="space-y-3">
            {incidents.map((inc) => (
                <div key={inc.id} className="border border-slate-700 rounded-lg p-4 bg-slate-800/50">
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 text-xs font-bold rounded text-white ${STATUS_COLORS[inc.status] || 'bg-gray-600'}`}>
                                {inc.status}
                            </span>
                            <span className="text-sm font-semibold text-white">#{inc.id}</span>
                            <span className="text-sm text-slate-400">{inc.service_name}</span>
                        </div>
                        <span className="text-xs text-slate-500">{inc.severity}</span>
                    </div>
                    <p className="text-sm text-slate-300 mb-2">{inc.error_summary?.substring(0, 150)}</p>
                    {inc.suggested_solution && (
                        <p className="text-xs text-cyan-400 mb-2">💡 {inc.suggested_solution.substring(0, 120)}</p>
                    )}
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-500">{new Date(inc.created_at).toLocaleString()}</span>

                        {inc.status === 'TRANSFERRED' && (
                            <button
                                onClick={() => handle(inc.id, 'resolve')}
                                disabled={acting === inc.id}
                                className="px-3 py-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-xs font-bold rounded shadow-lg transition-all"
                            >
                                {acting === inc.id ? '...' : 'Mark Resolved'}
                            </button>
                        )}

                        {inc.error_summary?.includes('APP_NPE_003') && !['RESOLVED', 'REJECTED', 'TRANSFERRED'].includes(inc.status) && (
                            <span className="text-xs text-yellow-400 italic">⚠️ App bug — no infra action</span>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}