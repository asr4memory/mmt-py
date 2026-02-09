export default function formatTimecode(d) {
    const hours = Math.floor(d / 3600);
    const minutes = Math.floor((d % 3600) / 60);
    const seconds = d % 60;
    const roundedSeconds = Math.floor(seconds);
    const millisecondsStr = seconds.toFixed(3).split('.')[1];

    return `${hours}:${minutes.toString().padStart(2, "0")}:${roundedSeconds.toString().padStart(2, "0")}.${millisecondsStr}`;
}
