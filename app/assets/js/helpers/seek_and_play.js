/**
 * Seeks a media element to a given time and plays it once seeking is complete.
 *
 * @param {HTMLMediaElement} mediaElement - The media element to seek and play (e.g. `<audio>` or `<video>`).
 * @param {number} time - The time in seconds to seek to.
 */
export default function seekAndPlay(mediaElement, time) {
    const startPlayback = () => {
        mediaElement.currentTime = time;
        mediaElement.addEventListener('seeked', () => {
            mediaElement.play();
        }, { once: true });
    };

    if (mediaElement.readyState >= 1) {
        startPlayback();
    } else {
        mediaElement.addEventListener('loadedmetadata', startPlayback, { once: true });
    }
}
