export default function playTimeRange(mediaElement: HTMLMediaElement, start: number, end: number): void {
    mediaElement.currentTime = start;

    let rafId: number;

    const check = () => {
        if (mediaElement.currentTime >= end) {
            mediaElement.pause();
            mediaElement.currentTime = end;
            cancelAnimationFrame(rafId);
            return;
        }
        rafId = requestAnimationFrame(check);
    };

    mediaElement.play().then(() => {
        rafId = requestAnimationFrame(check);
    });

    mediaElement.addEventListener("pause", () => cancelAnimationFrame(rafId), {
        once: true,
    });
}
