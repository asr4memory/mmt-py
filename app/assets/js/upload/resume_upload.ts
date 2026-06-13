import { computed, defineComponent, onMounted, ref, type PropType } from "vue";

import uploadChunks from "./upload_chunks";
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
    },
    setup(props) {
        const status = ref<UploadStatus>("uploading");
        const transferred = ref(0);
        const speed = ref(0);
        const eta = ref<number | null>(null);
        const abortController = ref<AbortController | null>(null);

        const upload = computed<Upload>(() => ({
            file: props.file,
            status: status.value,
            transferred: transferred.value,
            speed: speed.value,
            eta: eta.value,
        }));

        async function startUpload() {
            abortController.value = new AbortController();
            const samples: Sample[] = [];
            try {
                await uploadChunks({
                    fileId: props.fileId,
                    file: props.file,
                    chunkSize: props.chunkSize,
                    chunksToUpload: props.chunksMissing,
                    signal: abortController.value.signal,
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
                });
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
                window.location.href = `/uploaded-files/${props.fileId}/`;
            }, 1000);
        }

        function onCancel() {
            abortController.value?.abort();
        }

        onMounted(() => {
            void startUpload();
        });

        return { status, transferred, upload, onCancel };
    },
    template: `
    <ul class="chunked-queue u-mt u-ll">
      <ChunkedUploadQueueItem
        :upload="upload"
        @onCancel="onCancel"
      />
    </ul>
  `,
});
