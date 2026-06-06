import { defineComponent, ref } from "vue";
import MediaPlayer from "./media_player";
import WaveformComponent from "./waveform_component";

export default defineComponent({
    name: "MediaBar",
    components: { MediaPlayer, WaveformComponent },
    props: {
        transcriptId: { type: Number, required: true },
        uploadedFileId: { type: Number, required: true },
        activeSegmentIdx: { type: Number, required: true },
        showWaveform: { type: Boolean, required: true },
        src: { type: String, required: true },
        mediaType: { type: String, required: true },
    },
    emits: ["close-panel", "timeupdate"],
    setup(_, { emit }) {
        const playerRef = ref<InstanceType<typeof MediaPlayer> | null>(null);

        function onTimeUpdate(time: number) {
            emit("timeupdate", time);
        }

        return { playerRef, onTimeUpdate };
    },
    template: `
    <div class="media-bar">
        <MediaPlayer ref="playerRef"
            class="media-bar__player"
            :src="src"
            :mediaType="mediaType"
            @timeupdate="onTimeUpdate" />
        <WaveformComponent v-if="showWaveform"
            class="media-bar__waveform"
            :transcriptId="transcriptId"
            :uploadedFileId="uploadedFileId"
            :activeSegmentIdx="activeSegmentIdx"
            :mediaElement="playerRef?.mediaElement"
            @close-panel="$emit('close-panel')" />
    </div>
    `,
});
