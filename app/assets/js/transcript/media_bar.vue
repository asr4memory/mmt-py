<script setup lang="ts">
import { computed } from "vue";

import { useMediaStore } from "./media_store";
import MediaPlayer from "./media_player.vue";
import WaveformComponent from "./waveform_component.vue";

defineProps<{
    transcriptId: number;
    uploadedFileId: number;
    activeSegmentIdx: number;
    showWaveform: boolean;
    src: string;
    mediaType: string;
}>();

const emit = defineEmits<{ "close-panel": []; timeupdate: [time: number] }>();

// The waveform draws the samples of the file the player has loaded, so it
// needs the element itself. It becomes available once the player has mounted
// and registered it.
const media = useMediaStore();
const mediaElement = computed(() => media.element ?? undefined);

function onTimeUpdate(time: number) {
    emit("timeupdate", time);
}
</script>

<template>
    <div class="media-bar">
        <MediaPlayer
            class="media-bar__player"
            :src="src"
            :mediaType="mediaType"
            @timeupdate="onTimeUpdate"
        />
        <WaveformComponent
            v-if="showWaveform && mediaElement"
            class="media-bar__waveform"
            :transcriptId="transcriptId"
            :uploadedFileId="uploadedFileId"
            :activeSegmentIdx="activeSegmentIdx"
            :mediaElement="mediaElement"
            @close-panel="$emit('close-panel')"
        />
    </div>
</template>
