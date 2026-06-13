import { computed, defineComponent, onMounted, ref, type PropType } from "vue";

import registerUpload from "./register_upload.js";
import uploadChunks from "./upload_chunks";
import ChunkedUploadQueueItem from "./chunked_upload_queue_item";
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

            try {
                await uploadChunks({
                    fileId: serverResult.id,
                    file: next.file,
                    chunkSize: serverResult.chunk_size,
                    signal: abortController.value.signal,
                    onProgress: (transferred) => {
                        next.transferred = transferred;
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
            void startNextUpload();
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
