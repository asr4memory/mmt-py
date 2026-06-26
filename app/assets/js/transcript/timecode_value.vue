<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ seconds: number }>();

const hours = computed(() => Math.floor(props.seconds / 3600).toString());

const minutes = computed(() =>
    Math.floor((props.seconds % 3600) / 60)
        .toString()
        .padStart(2, "0"),
);

const seconds = computed(() =>
    Math.floor(props.seconds % 60)
        .toString()
        .padStart(2, "0"),
);

const milliseconds = computed(() => (props.seconds % 60).toFixed(3).split(".")[1]);
</script>

<template>
    <span class="timecode">
        <span class="timecode__hours">{{ hours }}</span>
        <span class="timecode__colon">:</span>
        <span class="timecode__minutes">{{ minutes }}</span>
        <span class="timecode__colon">:</span>
        <span class="timecode__seconds">{{ seconds }}</span>
        <span class="timecode__point">.</span>
        <span class="timecode__milliseconds">{{ milliseconds }}</span>
    </span>
</template>
