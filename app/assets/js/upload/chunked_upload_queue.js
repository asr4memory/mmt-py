import registerUpload from "./register_upload.js";
import uploadChunks from "./upload_chunks.js";
import ChunkedUploadQueueItem from "./chunked_upload_queue_item.js";

export default {
    name: "ChunkedUploadQueue",
    components: { ChunkedUploadQueueItem },
    props: ["files", "projectId"],
    data() {
        return {
            uploads: (this.files || []).map((file, i) => ({
                id: i,
                file,
                status: "pending",
                progress: 0,
            })),
            abortController: null,
        };
    },
    mounted() {
        this.startNextUpload();
    },
    computed: {
        currentUploadNumber() {
            const index = this.uploads.findIndex(
                (u) => u.status === "uploading",
            );
            return index === -1 ? null : index + 1;
        },
    },
    methods: {
        async startNextUpload() {
            const next = this.uploads.find((u) => u.status === "pending");
            if (!next) {
                setTimeout(() => {
                    window.location.href = `/projects/${this.projectId}/`;
                }, 1000);
                return;
            }

            next.status = "uploading";

            const serverResult = await registerUpload(
                next.file,
                this.projectId,
            );
            if (!serverResult) {
                next.status = "incomplete";
                this.startNextUpload();
                return;
            }

            this.abortController = new AbortController();

            try {
                await uploadChunks({
                    fileId: serverResult.id,
                    file: next.file,
                    chunkSize: serverResult.chunk_size,
                    signal: this.abortController.signal,
                    onProgress: (p) => {
                        next.progress = p;
                    },
                });
                next.status = "uploaded";
            } catch (err) {
                next.status =
                    err.name === "AbortError" ? "cancelled" : "incomplete";
            } finally {
                this.abortController = null;
            }

            this.startNextUpload();
        },

        cancelActive() {
            this.abortController?.abort();
        },

        onCancel(upload) {
            if (upload.status === "uploading") {
                this.cancelActive();
            } else {
                this.cancelPending(upload.id);
            }
        },

        cancelPending(id) {
            const index = this.uploads.findIndex((u) => u.id === id);
            if (index !== -1) {
                this.uploads.splice(index, 1);
            }
        },
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
};
