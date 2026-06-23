<script setup lang="ts">
import { storeToRefs } from "pinia";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import beforeUnloadHandler from "../shared/before_unload_handler";
import addIDsToTranscript from "./add_ids_to_transcript";
import cleanTranscript from "./clean_transcript";
import findPlaybackPosition from "./find_playback_position";
import MediaBar from "./media_bar.vue";
import removeIDsFromTranscript from "./remove_ids_from_transcript";
import TranscriptSegment from "./transcript_segment.vue";
import TranscriptSidebar from "./transcript_sidebar.vue";
import { useTranscriptStore } from "./transcript_store";
import TranscriptSubhead from "./transcript_subhead.vue";
import updateTranscript from "./update_transcript";

const props = defineProps<{
    id: number;
    label: string;
    mediaType: string;
    language: string;
    duration: string;
    uploadedFile: string;
    uploadedFileId: number;
    projectId: number;
}>();

const store = useTranscriptStore();
const { segments, transcriptIsDirty } = storeToRefs(store);

const activeSegmentIdx = ref(0);
const currentSegmentIdx = ref(-1);
const currentWordIdx = ref(-1);
const transcriptLoaded = ref(false);
const showConfidence = ref(false);
const showEntities = ref(true);
const showEdits = ref(true);
const autoScroll = ref(false);
const showWaveform = ref(true);

const mediaFileURL = `/uploaded-files/${props.uploadedFileId}/stream/`;

watch(transcriptIsDirty, (newValue, oldValue) => {
    if (newValue === true && oldValue === false) {
        window.addEventListener("beforeunload", beforeUnloadHandler);
    }
    if (newValue === false && oldValue === true) {
        window.removeEventListener("beforeunload", beforeUnloadHandler);
    }
});

onMounted(async () => {
    await loadTranscript();
});

onBeforeUnmount(() => {
    window.removeEventListener("beforeunload", beforeUnloadHandler);
});

async function loadTranscript() {
    const path = `/transcripts/${props.id}/json/`;
    const result = await fetch(path);
    const json = await result.json();
    segments.value = addIDsToTranscript(json.segments);
    store.extractSpeakers();
    transcriptLoaded.value = true;
}

async function discardTranscript() {
    transcriptLoaded.value = false;
    await loadTranscript();
}

function updateActiveSegment(newIndex: number) {
    activeSegmentIdx.value = newIndex;
    showWaveform.value = true;
}

function handleCloseWaveformPanel() {
    showWaveform.value = false;
}

function handleTimeUpdate(time: number) {
    const { segmentIdx, wordIdx } = findPlaybackPosition(segments.value, time);
    currentSegmentIdx.value = segmentIdx;
    currentWordIdx.value = wordIdx;
}

async function saveTranscript() {
    const cleanedTranscript = cleanTranscript(segments.value);
    try {
        await updateTranscript(props.id, {
            segments: removeIDsFromTranscript(cleanedTranscript),
        });
        // Only clear the dirty state once the server has accepted the save.
        segments.value = cleanedTranscript;
    } catch (err) {
        console.error(err);
    }
}
</script>

<template>
    <div class="container u-mt">
        <h1 class="u-mt-none u-mb-none">
            <b>{{ label }}</b>
        </h1>
        <TranscriptSubhead
            :label="uploadedFile"
            :language="language"
            :duration="duration"
            @save="saveTranscript"
            @discard="discardTranscript"
        />
    </div>

    <MediaBar
        :transcriptId="id"
        :uploadedFileId="uploadedFileId"
        :activeSegmentIdx="activeSegmentIdx"
        :src="mediaFileURL"
        :mediaType="mediaType"
        :showWaveform="transcriptLoaded && showWaveform"
        @timeupdate="handleTimeUpdate"
        @close-panel="handleCloseWaveformPanel"
    />

    <div class="container u-mt u-mb-large">
        <div class="layout layout--transcript transcript">
            <div v-if="transcriptLoaded" spellcheck="false">
                <TranscriptSegment
                    v-for="(segment, index) in segments"
                    @activate-segment="updateActiveSegment"
                    :key="segment.id"
                    :segment="segment"
                    :index="index"
                    :active="activeSegmentIdx === index"
                    :isCurrent="currentSegmentIdx === index"
                    :currentWordIdx="
                        currentSegmentIdx === index ? currentWordIdx : -1
                    "
                    :showConfidence="showConfidence"
                    :showEntities="showEntities"
                    :showEdits="showEdits"
                    :autoScroll="autoScroll"
                />
            </div>
            <p v-else>{{ $t("loading_transcript") }}</p>
            <div class="transcript__media-column">
                <TranscriptSidebar
                    v-model:showConfidence="showConfidence"
                    v-model:showEntities="showEntities"
                    v-model:showEdits="showEdits"
                    v-model:autoScroll="autoScroll"
                />
            </div>
        </div>
    </div>
</template>
