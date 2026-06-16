export default function seekAndPlay(mediaElement: HTMLMediaElement, time: number): void {
    const startPlayback = () => {
        mediaElement.currentTime = time;
        mediaElement.addEventListener(
            "seeked",
            () => {
                mediaElement.play();
            },
            { once: true },
        );
    };

    if (mediaElement.readyState >= 1) {
        startPlayback();
    } else {
        mediaElement.addEventListener("loadedmetadata", startPlayback, {
            once: true,
        });
    }
}
