<script setup lang="ts">
import { storeToRefs } from "pinia";
import {
    computed,
    nextTick,
    onBeforeUnmount,
    onMounted,
    ref,
    watch,
} from "vue";

import type { SegmentBox } from "./minimap_geometry";
import {
    measureSegments,
    minimapSpans,
    scrollTargetForFraction,
    viewportBand,
} from "./minimap_geometry";
import { useTranscriptStore } from "./transcript_store";

// The element that holds the rendered segments. Its children are measured in
// order, so child n belongs to segment n.
const props = defineProps<{ contentEl: HTMLElement | null }>();

const store = useTranscriptStore();
const { segments, speakers } = storeToRefs(store);

const boxes = ref<SegmentBox[]>([]);
const documentHeight = ref(0);
const viewportHeight = ref(0);
const scrollY = ref(0);

let observer: ResizeObserver | null = null;

const speakerColors = computed(() => {
    const colors: Record<string, string> = {};
    for (const speaker of speakers.value) {
        colors[speaker.id] = speaker.color;
    }
    return colors;
});

const spans = computed(() => minimapSpans(boxes.value, documentHeight.value));

const bands = computed(() =>
    spans.value.bands.map((share, index) => {
        const segment = segments.value[index];
        const speakerId = segment?.speakerId;
        return {
            id: segment?.id ?? `band_${index}`,
            share,
            color: speakerId ? (speakerColors.value[speakerId] ?? null) : null,
        };
    }),
);

const viewport = computed(() =>
    viewportBand(scrollY.value, viewportHeight.value, documentHeight.value),
);

// The bands are laid out as a flex column, so each one takes its share of the
// strip through flex-grow instead of being positioned on its own. Consecutive
// bands then share an edge exactly, with no rounding of a position and a
// height against each other.
function bandStyle(band: { share: number; color: string | null }) {
    return {
        backgroundColor: band.color ?? undefined,
        flexGrow: band.share,
    };
}

const viewportStyle = computed(() => ({
    height: `${viewport.value.height}%`,
    top: `${viewport.value.top}%`,
}));

// Reading the layout is the expensive part, so it happens on mount, on resize
// and when the transcript changes, never on scroll.
function measure() {
    documentHeight.value = document.documentElement.scrollHeight;
    viewportHeight.value = window.innerHeight;
    scrollY.value = window.scrollY;
    const content = props.contentEl;
    if (!content) {
        boxes.value = [];
        return;
    }
    boxes.value = measureSegments(
        Array.from(content.children) as HTMLElement[],
        window.scrollY,
    );
}

function handleScroll() {
    scrollY.value = window.scrollY;
}

function handleClick(event: MouseEvent) {
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    if (rect.height <= 0) return;
    const fraction = (event.clientY - rect.top) / rect.height;
    window.scrollTo({
        behavior: "smooth",
        top: scrollTargetForFraction(
            fraction,
            documentHeight.value,
            viewportHeight.value,
        ),
    });
}

function observe(content: HTMLElement | null) {
    observer?.disconnect();
    if (!content || typeof ResizeObserver === "undefined") return;
    observer = new ResizeObserver(() => measure());
    observer.observe(content);
}

// The segments are rendered by the parent, so a new or deleted segment changes
// the layout after the next render.
watch(
    () => segments.value.length,
    () => nextTick(measure),
);

watch(
    () => props.contentEl,
    (content) => {
        observe(content);
        nextTick(measure);
    },
);

onMounted(() => {
    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", measure);
    observe(props.contentEl);
    nextTick(measure);
});

onBeforeUnmount(() => {
    window.removeEventListener("scroll", handleScroll);
    window.removeEventListener("resize", measure);
    observer?.disconnect();
});
</script>

<template>
    <div
        class="transcript-minimap"
        :title="$t('transcript_minimap')"
        @click="handleClick"
    >
        <div
            class="transcript-minimap__spacer"
            :style="{ flexGrow: spans.leading }"
        ></div>
        <div
            v-for="band in bands"
            :key="band.id"
            class="transcript-minimap__band"
            :style="bandStyle(band)"
        ></div>
        <div
            class="transcript-minimap__spacer"
            :style="{ flexGrow: spans.trailing }"
        ></div>
        <div class="transcript-minimap__viewport" :style="viewportStyle"></div>
    </div>
</template>
