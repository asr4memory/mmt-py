// Compact playback clock, e.g. "1:23" or "2:47:33". Milliseconds are left out
// on purpose; formatTimecode is the precise format used for editing.
export default function formatClockTime(seconds: number): string {
    const total =
        Number.isFinite(seconds) && seconds > 0 ? Math.floor(seconds) : 0;
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const secs = total % 60;
    const paddedSecs = secs.toString().padStart(2, "0");

    if (hours === 0) return `${minutes}:${paddedSecs}`;
    return `${hours}:${minutes.toString().padStart(2, "0")}:${paddedSecs}`;
}
