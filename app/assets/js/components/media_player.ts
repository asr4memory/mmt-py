import { defineComponent, ref, computed } from "vue";

const SEEK_TIME = 5;

export default defineComponent({
    name: "MediaPlayer",
    props: {
        src: { type: String, required: true },
        mediaType: { type: String, required: true },
    },
    emits: ["timeupdate"],
    setup(props, { emit, expose }) {
        const mediaRef = ref<HTMLMediaElement | null>(null);
        const isVideo = computed(() => props.mediaType.startsWith("video"));

        function onTimeUpdate() {
            if (mediaRef.value) emit("timeupdate", mediaRef.value.currentTime);
        }

        function seekLeft() {
            if (!mediaRef.value) return;
            mediaRef.value.currentTime -= SEEK_TIME;
            mediaRef.value.play();
        }

        function seekRight() {
            if (!mediaRef.value) return;
            mediaRef.value.currentTime += SEEK_TIME;
            mediaRef.value.play();
        }

        expose({
            get mediaElement() { return mediaRef.value; },
        });

        return { mediaRef, isVideo, onTimeUpdate, seekLeft, seekRight };
    },
    template: `
    <div>
        <video v-if="isVideo" id="media-player" ref="mediaRef" controls
            width="240" class="transcript__media" @timeupdate="onTimeUpdate">
            <source :src="src" :type="mediaType" />
        </video>
        <audio v-else id="media-player" ref="mediaRef" controls
            width="240" class="transcript__media" @timeupdate="onTimeUpdate">
            <source :src="src" :type="mediaType" />
        </audio>
        <div>
            <button type="button" @click="seekLeft">&#9194;</button>
            <button type="button" @click="seekRight">&#9193;</button>
        </div>
    </div>
    `,
});
