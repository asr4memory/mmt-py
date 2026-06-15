export default function formatEta(seconds: number | null): string | null {
    if (seconds === null || !Number.isFinite(seconds)) return null;
    const s = Math.round(seconds);
    if (s < 60) return `${s}s`;
    if (s < 3600) {
        const m = Math.floor(s / 60);
        const rem = s % 60;
        return rem === 0 ? `${m}m` : `${m}m ${rem}s`;
    }
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return m === 0 ? `${h}h` : `${h}h ${m}m`;
}
