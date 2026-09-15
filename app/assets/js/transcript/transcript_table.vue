<script setup lang="ts">
import { storeToRefs } from "pinia";
import { onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from "vue";
import { useI18n } from "vue-i18n";
import beforeUnloadHandler from "../shared/before_unload_handler";
import MessageStack from "../shared/message_stack.vue";
import { useMessagesStore } from "../shared/messages_store";
import { routes } from "../shared/routes";
import cleanTranscript from "./clean_transcript";
import DocumentBar from "./document_bar.vue";
import findPlaybackPosition from "./find_playback_position";
import MediaBar from "./media_bar.vue";
import segmentIsInView from "./segment_is_in_view";
import TranscriptDrawer from "./transcript_drawer.vue";
import TranscriptSegment from "./transcript_segment.vue";
import TranscriptSidebar from "./transcript_sidebar.vue";
import { useTranscriptStore } from "./transcript_store";
import { useMediaShortcuts } from "./useMediaShortcuts";
import updateTranscript from "./update_transcript";

const props = defineProps<{
    id: number;
    label: string;
    mediaType: string;
    duration: string;
    uploadedFile: string;
    uploadedFileId: number;
    projectId: number;
}>();

const { t } = useI18n();
const messages = useMessagesStore();
const store = useTranscriptStore();
const {
    segments,
    speakers,
    mentions,
    entities,
    redactions,
    transcriptIsDirty,
} = storeToRefs(store);

// The language belongs to the content, so it is loaded from the fetched
// transcript and written back on save. The model name of the speech
// recognition that produced the transcript is carried the same way.
const language = ref<string | null>(null);
const model = ref<string | null>(null);
const activeSegmentIdx = ref(0);
const currentSegmentIdx = ref(-1);
const currentWordIdx = ref(-1);
const transcriptLoaded = ref(false);
const showConfidence = ref(false);
const showEntities = ref(true);
const showEdits = ref(true);
const autoScroll = ref(false);
const showWaveform = ref(true);
const isSaving = ref(false);

const mediaFileURL = routes.uploadedFileStream(props.uploadedFileId);

const headerRef = useTemplateRef<HTMLElement>("headerRef");
const mediaBarRef = useTemplateRef<InstanceType<typeof MediaBar>>("mediaBarRef");
const segmentRefs = useTemplateRef<InstanceType<typeof TranscriptSegment>[]>(
    "segmentRefs",
);
// Drives the jump button, which is only enabled while the segment being
// played is outside the visible part of the transcript.
const currentIsInView = ref(true);
// In the pause between two segments there is no current segment. The jump
// target is then the segment that was played last, so that the button does
// not turn itself off for the length of the pause.
const jumpSegmentIdx = ref(-1);

watch(transcriptIsDirty, (newValue, oldValue) => {
    if (newValue === true && oldValue === false) {
        window.addEventListener("beforeunload", beforeUnloadHandler);
    }
    if (newValue === false && oldValue === true) {
        window.removeEventListener("beforeunload", beforeUnloadHandler);
    }
});

onMounted(async () => {
    window.addEventListener("scroll", updateCurrentIsInView, { passive: true });
    window.addEventListener("resize", updateCurrentIsInView);
    await loadTranscript();
});

onBeforeUnmount(() => {
    window.removeEventListener("beforeunload", beforeUnloadHandler);
    window.removeEventListener("scroll", updateCurrentIsInView);
    window.removeEventListener("resize", updateCurrentIsInView);
});

function currentSegmentElement(): HTMLElement | null {
    if (jumpSegmentIdx.value < 0) return null;
    const segment = segmentRefs.value?.[jumpSegmentIdx.value];
    return (segment?.$el as HTMLElement) ?? null;
}

function updateCurrentIsInView() {
    const element = currentSegmentElement();
    if (!element) {
        currentIsInView.value = true;
        return;
    }
    const headerBottom =
        headerRef.value?.getBoundingClientRect().bottom ?? 0;
    currentIsInView.value = segmentIsInView(
        element.getBoundingClientRect(),
        headerBottom,
        window.innerHeight,
    );
}

function jumpToCurrentSegment() {
    currentSegmentElement()?.scrollIntoView({
        behavior: "smooth",
        block: "center",
    });
}

async function loadTranscript() {
    const path = `/transcripts/${props.id}/json/`;
    const result = await fetch(path);
    const json = await result.json();
    // Content is born/migrated normalized (mmt-transcript), so consume it
    // as-is: ids and speakers come straight from the file.
    segments.value = json.segments;
    speakers.value = json.speakers;
    mentions.value = json.mentions;
    entities.value = json.entities;
    redactions.value = json.redactions;
    language.value = json.language ?? null;
    model.value = json.model ?? null;
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
    if (segmentIdx >= 0) jumpSegmentIdx.value = segmentIdx;
    updateCurrentIsInView();
}

useMediaShortcuts({
    togglePlay: () => mediaBarRef.value?.togglePlay(),
    seekBackward: () => mediaBarRef.value?.seekBackward(),
    seekForward: () => mediaBarRef.value?.seekForward(),
    toggleMute: () => mediaBarRef.value?.toggleMute(),
    toggleFullscreen: () => mediaBarRef.value?.toggleFullscreen(),
    increaseVolume: () => mediaBarRef.value?.increaseVolume(),
    decreaseVolume: () => mediaBarRef.value?.decreaseVolume(),
    increasePlaybackRate: () => mediaBarRef.value?.increasePlaybackRate(),
    decreasePlaybackRate: () => mediaBarRef.value?.decreasePlaybackRate(),
    jumpToPlayback: jumpToCurrentSegment,
});

async function saveTranscript() {
    isSaving.value = true;
    try {
        await updateTranscript(props.id, {
            format: "mmt-transcript",
            version: 1,
            language: language.value,
            model: model.value,
            speakers: speakers.value,
            entities: entities.value,
            mentions: mentions.value,
            redactions: redactions.value,
            segments: cleanTranscript(segments.value),
        });
        // Only clear the dirty state once the server has accepted the save.
        store.markSaved();
        messages.add("success", t("transcript_saved"));
    } catch (err) {
        console.error(err);
        messages.add("error", t("save_failed", { error: String(err) }));
    } finally {
        isSaving.value = false;
    }
}
</script>

<template>
    <MessageStack />
    <header class="transcript-header" ref="headerRef">
        <DocumentBar
            :label="label"
            :uploadedFileName="uploadedFile"
            :uploadedFileId="uploadedFileId"
            :language="language"
            :duration="duration"
            :isSaving="isSaving"
            @save="saveTranscript"
            @discard="discardTranscript"
        />
        <MediaBar
            ref="mediaBarRef"
            :transcriptId="id"
            :uploadedFileId="uploadedFileId"
            :activeSegmentIdx="activeSegmentIdx"
            :src="mediaFileURL"
            :mediaType="mediaType"
            :showWaveform="transcriptLoaded && showWaveform"
            @timeupdate="handleTimeUpdate"
            @close-panel="handleCloseWaveformPanel"
        />
        <button
            type="button"
            class="jump-button transcript-header__jump"
            :disabled="currentIsInView"
            @click="jumpToCurrentSegment"
        >
            {{ $t("jump_to_playback") }}
        </button>
    </header>

    <div class="container u-mt-large u-mb-large transcript">
        <div v-if="transcriptLoaded" spellcheck="false">
            <TranscriptSegment
                v-for="(segment, index) in segments"
                ref="segmentRefs"
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
    </div>

    <TranscriptDrawer>
        <TranscriptSidebar
            v-model:showConfidence="showConfidence"
            v-model:showEntities="showEntities"
            v-model:showEdits="showEdits"
            v-model:autoScroll="autoScroll"
        />
    </TranscriptDrawer>
</template>
