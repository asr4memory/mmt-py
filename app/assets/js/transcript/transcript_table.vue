<script setup lang="ts">
import { storeToRefs } from "pinia";
import {
    computed,
    onBeforeUnmount,
    onMounted,
    ref,
    useTemplateRef,
    watch,
} from "vue";
import { useI18n } from "vue-i18n";
import beforeUnloadHandler from "../shared/before_unload_handler";
import MessageStack from "../shared/message_stack.vue";
import { useMessagesStore } from "../shared/messages_store";
import cleanTranscript from "./clean_transcript";
import DocumentBar from "./document_bar.vue";
import { ENTITY_LABELS } from "./entities";
import findPlaybackPosition from "./find_playback_position";
import MediaBar from "./media_bar.vue";
import { useMediaStore } from "./media_store";
import TranscriptDrawer from "./transcript_drawer.vue";
import TranscriptSegment from "./transcript_segment.vue";
import TranscriptSidebar from "./transcript_sidebar.vue";
import { useTranscriptStore } from "./transcript_store";
import updateTranscript from "./update_transcript";
import { useMediaShortcuts } from "./useMediaShortcuts";

const props = defineProps<{
    id: number;
    initialLabel: string;
    mediaType: string;
    duration: string;
    uploadedFile: string;
    uploadedFileId: number;
    mediaUrl: string;
    projectId: number;
}>();

const { t } = useI18n();
const messages = useMessagesStore();
const store = useTranscriptStore();
const media = useMediaStore();
const {
    segments,
    speakers,
    mentions,
    entities,
    redactions,
    label,
    labelIsDirty,
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
// The NER labels whose highlighting is switched on in the sidebar. The master
// toggle sits in front of the per-type selection, so the transcript is given
// no types at all while it is off.
const visibleEntityTypes = ref<string[]>([...ENTITY_LABELS]);
const shownEntityTypes = computed(() =>
    showEntities.value ? visibleEntityTypes.value : [],
);
const showEdits = ref(true);
const autoScroll = ref(false);
const showWaveform = ref(true);
const isSaving = ref(false);

const segmentRefs =
    useTemplateRef<InstanceType<typeof TranscriptSegment>[]>("segmentRefs");
// In the pause between two segments there is no current segment. The jump
// target is then the segment that was played last.
const jumpSegmentIdx = ref(-1);

watch(transcriptIsDirty, (newValue, oldValue) => {
    if (newValue === true && oldValue === false) {
        window.addEventListener("beforeunload", beforeUnloadHandler);
    }
    if (newValue === false && oldValue === true) {
        window.removeEventListener("beforeunload", beforeUnloadHandler);
    }
});

// The label is put into the store before the first render, so the document
// bar never shows an empty heading.
store.loadLabel(props.initialLabel);

onMounted(async () => {
    await loadTranscript();
});

onBeforeUnmount(() => {
    window.removeEventListener("beforeunload", beforeUnloadHandler);
});

function currentSegmentElement(): HTMLElement | null {
    if (jumpSegmentIdx.value < 0) return null;
    const segment = segmentRefs.value?.[jumpSegmentIdx.value];
    return (segment?.$el as HTMLElement) ?? null;
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
    store.loadSpeakers(json.speakers);
    mentions.value = json.mentions;
    entities.value = json.entities;
    redactions.value = json.redactions;
    language.value = json.language ?? null;
    model.value = json.model ?? null;
    transcriptLoaded.value = true;
}

async function discardTranscript() {
    store.discardLabel();
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
}

// The store supplies every command that acts on the media element. The
// commands are plain functions bound to the store, so spreading them once here
// keeps them working. Jumping to the played segment is the table's own,
// because only the table knows where the segments are on screen.
useMediaShortcuts({
    ...media,
    jumpToPlayback: jumpToCurrentSegment,
});

async function saveTranscript() {
    isSaving.value = true;
    try {
        await updateTranscript(
            props.id,
            {
                format: "mmt-transcript",
                version: 1,
                language: language.value,
                model: model.value,
                speakers: speakers.value,
                entities: entities.value,
                mentions: mentions.value,
                redactions: redactions.value,
                segments: cleanTranscript(segments.value),
            },
            labelIsDirty.value ? label.value : undefined,
        );
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
    <header class="transcript-header">
        <DocumentBar
            :transcriptId="id"
            :uploadedFileName="uploadedFile"
            :uploadedFileId="uploadedFileId"
            :language="language"
            :duration="duration"
            :isSaving="isSaving"
            @save="saveTranscript"
            @discard="discardTranscript"
        />
        <MediaBar
            :transcriptId="id"
            :uploadedFileId="uploadedFileId"
            :activeSegmentIdx="activeSegmentIdx"
            :src="mediaUrl"
            :mediaType="mediaType"
            :showWaveform="transcriptLoaded && showWaveform"
            @timeupdate="handleTimeUpdate"
            @close-panel="handleCloseWaveformPanel"
        />
        <button
            type="button"
            class="jump-button transcript-header__jump"
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
                :visibleEntityTypes="shownEntityTypes"
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
            v-model:visibleEntityTypes="visibleEntityTypes"
            v-model:showEdits="showEdits"
            v-model:autoScroll="autoScroll"
        />
    </TranscriptDrawer>
</template>
