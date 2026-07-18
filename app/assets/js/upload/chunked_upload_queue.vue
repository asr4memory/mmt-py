<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

import beforeUnloadHandler from "../shared/before_unload_handler.js";
import { useUploadTabTitle } from "./use_upload_tab_title";
import registerUpload from "./register_upload.js";
import fetchResumableUploads from "./fetch_resumable_uploads";
import applyResumableMatches from "./apply_resumable_matches";
import uploadOne from "./upload_one";
import ChunkedUploadQueueItem from "./chunked_upload_queue_item.vue";
import type { Upload } from "./types";

defineOptions({ name: "ChunkedUploadQueue" });

const props = defineProps<{
    files: File[];
    projectId: number;
}>();

const uploads = ref<Upload[]>(
    props.files.map((file, i) => ({
        id: i,
        file,
        status: "pending",
        transferred: 0,
        speed: 0,
        eta: null,
        checksumStatus: "pending",
    })),
);
const abortController = ref<AbortController | null>(null);
// Chunk size reported by the resumable-uploads lookup, used for files that are
// resumed (registered files get their chunk size from registerUpload instead).
let resumeChunkSize = 0;

const currentUploadNumber = computed(() => {
    const index = uploads.value.findIndex((u) => u.status === "uploading");
    return index === -1 ? null : index + 1;
});

// Bytes already handled, weighted by file size so progress is proportional.
// Cancelled and incomplete files count as fully transferred so the overall
// percentage can still reach 100% once the queue is done.
const overallProgress = computed(() => {
    const totalBytes = uploads.value.reduce((sum, u) => sum + u.file.size, 0);
    if (totalBytes === 0) return 0;
    const transferredBytes = uploads.value.reduce(
        (sum, u) =>
            sum +
            (u.status === "uploaded" ||
            u.status === "cancelled" ||
            u.status === "incomplete"
                ? u.file.size
                : u.transferred),
        0,
    );
    return Math.round((transferredBytes / totalBytes) * 100);
});

useUploadTabTitle(
    overallProgress,
    currentUploadNumber,
    () => uploads.value.length,
);

async function startNextUpload() {
    const next = uploads.value.find((u) => u.status === "pending");
    if (!next) {
        // A single uploaded file goes straight to its detail page; with several
        // there is no single page to show, so fall back to the project page.
        const uploaded = uploads.value.filter((u) => u.status === "uploaded");
        const target =
            uploaded.length === 1
                ? `/uploaded-files/${uploaded[0].fileId}/`
                : `/projects/${props.projectId}/`;
        setTimeout(() => {
            window.removeEventListener("beforeunload", beforeUnloadHandler);
            window.location.href = target;
        }, 1000);
        return;
    }

    next.status = "uploading";

    let fileId: number;
    let chunkSize: number;
    let chunksToUpload: number[] | undefined;

    if (next.resuming && next.fileId !== undefined) {
        fileId = next.fileId;
        chunkSize = resumeChunkSize;
        chunksToUpload = next.chunksMissing;
    } else {
        const serverResult = await registerUpload(next.file, props.projectId);
        if (!serverResult) {
            next.status = "incomplete";
            void startNextUpload();
            return;
        }
        next.fileId = serverResult.id;
        fileId = serverResult.id;
        chunkSize = serverResult.chunk_size;
    }

    abortController.value = new AbortController();

    try {
        await uploadOne({
            fileId,
            file: next.file,
            chunkSize,
            chunksToUpload,
            checksumSubmitted: next.checksumSubmitted,
            signal: abortController.value.signal,
            onProgress: ({ transferred, speed, eta }) => {
                next.transferred = transferred;
                next.speed = speed;
                next.eta = eta;
            },
            onChecksumStatus: (status) => {
                next.checksumStatus = status;
            },
        });
        next.status = "uploaded";
    } catch (err) {
        next.status =
            (err as { name: string }).name === "AbortError"
                ? "cancelled"
                : "incomplete";
    } finally {
        abortController.value = null;
    }

    void startNextUpload();
}

function cancelActive() {
    abortController.value?.abort();
}

function onCancel(upload: Upload) {
    if (upload.status === "uploading") {
        cancelActive();
    } else if (upload.id !== undefined) {
        cancelPending(upload.id);
    }
}

function cancelPending(id: number) {
    const index = uploads.value.findIndex((u) => u.id === id);
    if (index !== -1) {
        uploads.value.splice(index, 1);
    }
}

// Look up which selected files can be resumed and pre-fill their state before
// the queue starts, so their progress bars already show the bytes transferred
// so far.
onMounted(async () => {
    window.addEventListener("beforeunload", beforeUnloadHandler);
    const result = await fetchResumableUploads(
        props.files.map((file) => ({ filename: file.name, size: file.size })),
        props.projectId,
    );
    resumeChunkSize = result.chunk_size;
    applyResumableMatches(uploads.value, result);
    void startNextUpload();
});

onUnmounted(() => {
    window.removeEventListener("beforeunload", beforeUnloadHandler);
});

defineExpose({
    uploads,
    currentUploadNumber,
    overallProgress,
    cancelActive,
    cancelPending,
});
</script>

<template>
    <p class="u-ll">{{ $t('queue.tab_switch_hint') }}</p>
    <p class="u-ll">{{ $t('queue.cancel_hint') }}</p>
    <p v-if="currentUploadNumber" class="u-mt">{{ $t('queue.uploading_progress', { current: currentUploadNumber, total: uploads.length }) }}</p>
    <ul class="chunked-queue u-mt u-ll">
      <ChunkedUploadQueueItem
        v-for="upload in uploads"
        :key="upload.id"
        :upload="upload"
        @onCancel="onCancel"
      />
    </ul>
</template>
