export interface Sample {
    time: number; // ms epoch
    bytes: number; // cumulative transferred
}

const WINDOW_MS = 5000;

/** Drop samples older than the rolling window relative to the latest one. */
export function trimToWindow(samples: Sample[]): Sample[] {
    if (samples.length === 0) return samples;
    const cutoff = samples[samples.length - 1].time - WINDOW_MS;
    return samples.filter((s) => s.time >= cutoff);
}

/** Bytes per second across the sample window; 0 until two samples exist. */
export function estimateSpeed(samples: Sample[]): number {
    if (samples.length < 2) return 0;
    const first = samples[0];
    const last = samples[samples.length - 1];
    const seconds = (last.time - first.time) / 1000;
    if (seconds <= 0) return 0;
    return (last.bytes - first.bytes) / seconds;
}

/** Seconds remaining; null when not yet estimable. */
export function estimateEta(
    remainingBytes: number,
    speed: number,
): number | null {
    if (speed <= 0) return null;
    return remainingBytes / speed;
}
