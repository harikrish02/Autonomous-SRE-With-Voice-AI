import { useState, useEffect, useCallback } from 'react';

export function usePolling(fetchFn, intervalMs = 5000) {
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    const refresh = useCallback(() => {
        fetchFn()
            .then((d) => { setData(d); setError(null); })
            .catch((e) => setError(e.message))
            .finally(() => setLoading(false));
    }, [fetchFn]);

    useEffect(() => {
        refresh();
        const id = setInterval(refresh, intervalMs);
        return () => clearInterval(id);
    }, [refresh, intervalMs]);

    return { data, error, loading, refresh };
}
