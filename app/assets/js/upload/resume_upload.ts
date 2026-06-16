import { computed, defineComponent, onMounted, onUnmounted, ref, type PropType } from "vue";

import beforeUnloadHandler from "../shared/before_unload_handler.js";
import uploadChunks from "./upload_chunks";
import computeChecksum from "./compute_checksum";
import submitChecksum from "./submit_checksum.js";
import ChunkedUploadQueueItem from "./chunked_upload_queue_item";
import {
    estimateEta,
    estimateSpeed,
    trimToWindow,
    type Sample,
} from "./transfer_stats";
import type { Upload, UploadStatus } from "./types";

export default defineComponent({
    name: "ResumeUpload",
    components: { ChunkedUploadQueueItem },
    props: {
        fileId: { type: Number, required: true },
        chunkSize: { type: Number, required: true },
        chunksMissing: { type: Array as PropType<number[]>, required: true },
        file: { type: Object as PropType<File>, required: true },
        checksumSubmitted: { type: Boolean, required: true },
    },
    setup(props) {
        const status = ref<UploadStatus>("uploading");
        const transferred = ref(0);
        const speed = ref(0);
        const eta = ref<number | null>(null);
        const abortController = ref<AbortController | null>(null);
        const checksumStatus = ref(
            props.checksumSubmitted ? "complete" : "pending",
        );

        const upload = computed<Upload>(() => ({
            file: props.file,
            status: status.value,
            transferred: transferred.value,
            speed: speed.value,
            eta: eta.value,
            checksumStatus: checksumStatus.value as Upload["checksumStatus"],
        }));

        async function generateAndSubmitChecksum(signal: AbortSignal) {
            checksumStatus.value = "generating";
            const checksum = await computeChecksum(props.file, signal);
            checksumStatus.value = "transferring";
            await submitChecksum(props.fileId, checksum);
            checksumStatus.value = "complete";
        }

        async function startUpload() {
            abortController.value = new AbortController();
            const signal = abortController.value.signal;
            const samples: Sample[] = [];
            try {
                const tasks: Promise<unknown>[] = [
                    uploadChunks({
                        fileId: props.fileId,
                        file: props.file,
                        chunkSize: props.chunkSize,
                        chunksToUpload: props.chunksMissing,
                        signal,
                        onProgress: (t) => {
                            transferred.value = t;
                            samples.push({ time: Date.now(), bytes: t });
                            const recent = trimToWindow(samples);
                            speed.value = estimateSpeed(recent);
                            eta.value = estimateEta(
                                props.file.size - t,
                                speed.value,
                            );
                        },
                    }),
                ];
                if (!props.checksumSubmitted) {
                    tasks.push(generateAndSubmitChecksum(signal));
                }
                await Promise.all(tasks);
                status.value = "uploaded";
            } catch (err) {
                status.value =
                    (err as { name: string }).name === "AbortError"
                        ? "cancelled"
                        : "incomplete";
            } finally {
                abortController.value = null;
            }
            setTimeout(() => {
                window.removeEventListener("beforeunload", beforeUnloadHandler);
                window.location.href = `/uploaded-files/${props.fileId}/`;
            }, 1000);
        }

        function onCancel() {
            abortController.value?.abort();
        }

        onMounted(() => {
            window.addEventListener("beforeunload", beforeUnloadHandler);
            void startUpload();
        });

        onUnmounted(() => {
            window.removeEventListener("beforeunload", beforeUnloadHandler);
        });

        return { status, transferred, upload, onCancel };
    },
    template: `
    <p class="u-ll">{{ $t('queue.cancel_hint') }}</p>
    <p class="u-mt">{{ $t('queue.uploading_progress', { current: 1, total: 1 }) }}</p>
    <ul class="chunked-queue u-mt u-ll">
      <ChunkedUploadQueueItem
        :upload="upload"
        @onCancel="onCancel"
      />
    </ul>
  `,
});
