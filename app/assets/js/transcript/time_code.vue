<script setup lang="ts">
import TimecodeValue from "./timecode_value.vue";

defineProps<{ start: number; end: number }>();
</script>

<template>
    <span class="timecode-range">
        <TimecodeValue class="timecode-range__start" :seconds="start" />
        <span class="timecode-range__separator">–</span>
        <TimecodeValue class="timecode-range__end" :seconds="end" />
    </span>
</template>
