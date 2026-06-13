import uploadChunks from "./upload_chunks.js";
import ChunkedUploadQueueItem from "./chunked_upload_queue_item.js";

export default {
    name: "ResumeUpload",
    components: { ChunkedUploadQueueItem },
    props: ["fileId", "chunkSize", "chunksMissing", "file"],
    data() {
        return {
            status: "uploading",
            progress: 0,
            abortController: null,
        };
    },
    computed: {
        upload() {
            return {
                file: this.file,
                status: this.status,
                progress: this.progress,
            };
        },
    },
    mounted() {
        this.startUpload();
    },
    methods: {
        async startUpload() {
            this.abortController = new AbortController();
            try {
                await uploadChunks({
                    fileId: this.fileId,
                    file: this.file,
                    chunkSize: this.chunkSize,
                    chunksToUpload: this.chunksMissing,
                    signal: this.abortController.signal,
                    onProgress: (p) => {
                        this.progress = p;
                    },
                });
                this.status = "uploaded";
            } catch (err) {
                this.status =
                    err.name === "AbortError" ? "cancelled" : "incomplete";
            } finally {
                this.abortController = null;
            }
            setTimeout(() => {
                window.location.href = `/uploaded-files/${this.fileId}/`;
            }, 1000);
        },
        onCancel() {
            this.abortController?.abort();
        },
    },
    template: `
    <ul class="chunked-queue u-mt u-ll">
      <ChunkedUploadQueueItem
        :upload="upload"
        @onCancel="onCancel"
      />
    </ul>
  `,
};
