export interface Sample {
    time: number; // ms epoch
    bytes: number; // cumulative transferred
}

const WINDOW_MS = 5000;

/**
 * Remove, from the given array, the samples older than the rolling window
 * relative to the latest one. The array is modified in place, so a caller that
 * appends a sample per progress event and calls this after every append keeps
 * an array whose length is bounded by the window.
 *
 * Callers append samples in non-decreasing time order, so the samples to remove
 * are always a prefix of the array.
 */
export function trimToWindow(samples: Sample[]): void {
    if (samples.length === 0) return;
    const cutoff = samples[samples.length - 1].time - WINDOW_MS;
    let firstKept = 0;
    while (firstKept < samples.length && samples[firstKept].time < cutoff) {
        firstKept++;
    }
    samples.splice(0, firstKept);
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
