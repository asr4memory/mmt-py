export default function playSegment(video, start, end) {
    video.currentTime = start;

    let rafId;

    const check = () => {
        if (video.currentTime >= end) {
            video.pause();
            video.currentTime = end;
            cancelAnimationFrame(rafId);
            return;
        }
        rafId = requestAnimationFrame(check);
    };

    video.play().then(() => {
        rafId = requestAnimationFrame(check);
    });

    // Cleanup if Video is stopped from the outside.
    video.addEventListener('pause', () => cancelAnimationFrame(rafId), { once: true });
}
