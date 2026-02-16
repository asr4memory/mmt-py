export default {
    props: ["seconds"],
    computed: {
        timecode() {
            const hours = Math.floor(this.seconds / 3600);
            const minutes = Math.floor((this.seconds % 3600) / 60);
            const seconds = this.seconds % 60;
            const roundedSeconds = Math.floor(seconds);
            return `${hours}:${minutes.toString().padStart(2, "0")}:${roundedSeconds.toString().padStart(2, "0")}`;
        },
        milliseconds() {
            const seconds = this.seconds % 60;
            return seconds.toFixed(3).split(".")[1];
        },
    },
    template: `
    <span class="timecode">
        <span class="timecode__timecode">{{timecode}}</span>
        <span class="timecode__milliseconds">.{{milliseconds}}</span>
    </span>
    `,
};
