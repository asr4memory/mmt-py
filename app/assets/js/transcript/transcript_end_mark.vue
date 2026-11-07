<script setup lang="ts">
import { computed } from "vue";
import formatClockTime from "../shared/format_clock_time";
import type { TranscriptSegment } from "./types";

const props = defineProps<{
    segments: TranscriptSegment[];
}>();

// The duration is the end of the last segment.
const duration = computed(() =>
    formatClockTime(props.segments.at(-1)?.end ?? 0, true),
);
</script>

<template>
    <footer class="transcript-end-mark stack stack--small u-align-center u-color-muted u-mt-large">
        <div class="u-font-huge" aria-hidden="true">❦</div>
        <p class="u-font-small">
            {{ $t("transcript_end", { duration }) }}
        </p>
    </footer>
</template>
