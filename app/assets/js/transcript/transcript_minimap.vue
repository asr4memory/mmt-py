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
    minimapBands,
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

const bands = computed(() =>
    minimapBands(boxes.value, documentHeight.value).map((band, index) => {
        const segment = segments.value[index];
        const speakerId = segment?.speakerId;
        return {
            id: segment?.id ?? `band_${index}`,
            top: band.top,
            height: band.height,
            color: speakerId ? (speakerColors.value[speakerId] ?? null) : null,
        };
    }),
);

const viewport = computed(() =>
    viewportBand(scrollY.value, viewportHeight.value, documentHeight.value),
);

function bandStyle(band: {
    top: number;
    height: number;
    color: string | null;
}) {
    return {
        backgroundColor: band.color ?? undefined,
        height: `${band.height}%`,
        top: `${band.top}%`,
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
            v-for="band in bands"
            :key="band.id"
            class="transcript-minimap__band"
            :style="bandStyle(band)"
        ></div>
        <div class="transcript-minimap__viewport" :style="viewportStyle"></div>
    </div>
</template>
