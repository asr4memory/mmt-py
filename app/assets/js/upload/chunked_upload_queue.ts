import { computed, defineComponent, onMounted, onUnmounted, ref, type PropType } from "vue";

import beforeUnloadHandler from "../shared/before_unload_handler.js";
import registerUpload from "./register_upload.js";
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
import type { Upload } from "./types";

export default defineComponent({
    name: "ChunkedUploadQueue",
    components: { ChunkedUploadQueueItem },
    props: {
        files: { type: Array as PropType<File[]>, required: true },
        projectId: { type: Number, required: true },
    },
    setup(props) {
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

        const currentUploadNumber = computed(() => {
            const index = uploads.value.findIndex(
                (u) => u.status === "uploading",
            );
            return index === -1 ? null : index + 1;
        });

        async function startNextUpload() {
            const next = uploads.value.find((u) => u.status === "pending");
            if (!next) {
                setTimeout(() => {
                    window.removeEventListener("beforeunload", beforeUnloadHandler);
                    window.location.href = `/projects/${props.projectId}/`;
                }, 1000);
                return;
            }

            next.status = "uploading";

            const serverResult = await registerUpload(next.file, props.projectId);
            if (!serverResult) {
                next.status = "incomplete";
                void startNextUpload();
                return;
            }

            abortController.value = new AbortController();
            const signal = abortController.value.signal;

            const samples: Sample[] = [];
            const upload = next;

            async function generateAndSubmitChecksum() {
                upload.checksumStatus = "generating";
                const checksum = await computeChecksum(upload.file, signal);
                upload.checksumStatus = "transferring";
                await submitChecksum(serverResult!.id, checksum);
                upload.checksumStatus = "complete";
            }

            try {
                await Promise.all([
                    uploadChunks({
                        fileId: serverResult.id,
                        file: next.file,
                        chunkSize: serverResult.chunk_size,
                        signal,
                        onProgress: (transferred) => {
                            next.transferred = transferred;
                            samples.push({ time: Date.now(), bytes: transferred });
                            const recent = trimToWindow(samples);
                            next.speed = estimateSpeed(recent);
                            next.eta = estimateEta(
                                next.file.size - transferred,
                                next.speed,
                            );
                        },
                    }),
                    generateAndSubmitChecksum(),
                ]);
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
            } else {
                cancelPending(upload.id);
            }
        }

        function cancelPending(id: number) {
            const index = uploads.value.findIndex((u) => u.id === id);
            if (index !== -1) {
                uploads.value.splice(index, 1);
            }
        }

        onMounted(() => {
            window.addEventListener("beforeunload", beforeUnloadHandler);
            void startNextUpload();
        });

        onUnmounted(() => {
            window.removeEventListener("beforeunload", beforeUnloadHandler);
        });

        return { uploads, currentUploadNumber, cancelActive, cancelPending, onCancel };
    },
    template: `
    <p v-if="currentUploadNumber" class="u-mt">{{ $t('queue.uploading_progress', { current: currentUploadNumber, total: uploads.length }) }}</p>
    <ul class="chunked-queue u-mt u-ll">
      <ChunkedUploadQueueItem
        v-for="upload in uploads"
        :key="upload.id"
        :upload="upload"
        @onCancel="onCancel"
      />
    </ul>
  `,
});
