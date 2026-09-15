<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ start: number; end: number }>();

interface TimecodeParts {
    hours: string;
    minutes: string;
    seconds: string;
    milliseconds: string;
}

function splitTimecode(total: number): TimecodeParts {
    return {
        hours: Math.floor(total / 3600).toString(),
        minutes: Math.floor((total % 3600) / 60)
            .toString()
            .padStart(2, "0"),
        seconds: Math.floor(total % 60)
            .toString()
            .padStart(2, "0"),
        milliseconds: (total % 60).toFixed(3).split(".")[1],
    };
}

const values = computed(() => [
    { modifier: "timecode__value--start", parts: splitTimecode(props.start) },
    { modifier: "timecode__value--end", parts: splitTimecode(props.end) },
]);
</script>

<template>
    <span class="timecode">
        <template v-for="(value, index) in values" :key="value.modifier">
            <span v-if="index > 0" class="timecode__separator">–</span>
            <span class="timecode__value" :class="value.modifier">
                <span class="timecode__hours">{{ value.parts.hours }}</span>
                <span class="timecode__colon">:</span>
                <span class="timecode__minutes">{{ value.parts.minutes }}</span>
                <span class="timecode__colon">:</span>
                <span class="timecode__seconds">{{ value.parts.seconds }}</span>
                <span class="timecode__point">.</span>
                <span class="timecode__milliseconds">{{
                    value.parts.milliseconds
                }}</span>
            </span>
        </template>
    </span>
</template>
