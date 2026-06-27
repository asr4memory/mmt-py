export default function seekMedia(mediaElement: HTMLMediaElement, time: number): void {
    const seek = () => {
        mediaElement.currentTime = time;
    };

    if (mediaElement.readyState >= 1) {
        seek();
    } else {
        mediaElement.addEventListener("loadedmetadata", seek, { once: true });
    }
}
