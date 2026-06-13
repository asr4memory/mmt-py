export interface EtaLabel {
    key: string;
    params?: Record<string, number>;
}

/**
 * Map remaining seconds onto a coarse, low-jitter label descriptor.
 * Returns a vue-i18n key (and params) for the caller to translate, or null
 * when the ETA is not estimable yet.
 */
export default function formatEta(seconds: number | null): EtaLabel | null {
    if (seconds === null || !Number.isFinite(seconds)) return null;
    if (seconds < 45) return { key: "queue.eta_seconds" };
    if (seconds < 90) return { key: "queue.eta_one_minute" };
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return { key: "queue.eta_minutes", params: { minutes } };
    const hours = Math.round(seconds / 3600);
    return { key: "queue.eta_hours", params: { hours } };
}
