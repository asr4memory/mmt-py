<script setup lang="ts">
import { computed, useTemplateRef } from "vue";

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

const playerRef = useTemplateRef<InstanceType<typeof MediaPlayer>>("playerRef");

const mediaElement = computed(() => playerRef.value?.mediaElement ?? undefined);

function onTimeUpdate(time: number) {
    emit("timeupdate", time);
}
</script>

<template>
    <div class="media-bar">
        <MediaPlayer
            ref="playerRef"
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
