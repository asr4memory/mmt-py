<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ seconds: number }>();

const timecode = computed(() => {
    const hours = Math.floor(props.seconds / 3600);
    const minutes = Math.floor((props.seconds % 3600) / 60);
    const secs = props.seconds % 60;
    const roundedSeconds = Math.floor(secs);
    return `${hours}:${minutes.toString().padStart(2, "0")}:${roundedSeconds.toString().padStart(2, "0")}`;
});

const milliseconds = computed(() => {
    const secs = props.seconds % 60;
    return secs.toFixed(3).split(".")[1];
});
</script>

<template>
    <span class="timecode">
        <span class="timecode__timecode">{{ timecode }}</span>
        <span class="timecode__milliseconds">.{{ milliseconds }}</span>
    </span>
</template>
