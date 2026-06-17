import createChecksum from "./create_checksum";
import registerUpload from "./register_upload.js";
import submitChecksum from "./submit_checksum";
import beforeUnloadHandler from "../shared/before_unload_handler.js";
import uploadFile from "./upload_file.js";
import CurrentUpload from "./current_upload.js";
import UploadQueueItem from "./upload_queue_item.js";

let xhrRef = null;
let _nextUploadId = 0;

function getNextUploadId() {
    return _nextUploadId++;
}

export default {
    components: {
        CurrentUpload,
        UploadQueueItem,
    },
    name: "UploadQueue",
    props: ["files", "projectId"],
    data() {
        const files = this.files || [];
        const pendingUploads = files.map((file) => {
            return {
                id: getNextUploadId(),
                file,
            };
        });
        return {
            activeUpload: null,
            pendingUploads,
        };
    },
    mounted() {
        window.addEventListener("beforeunload", beforeUnloadHandler);
        this.startNextJob();
    },
    beforeUnmount() {
        window.removeEventListener("beforeunload", beforeUnloadHandler);
    },
    computed: {
        queueLength() {
            return this.activeUpload
                ? this.pendingUploads.length + 1
                : this.pendingUploads.length;
        },
        isQueueEmpty() {
            return this.queueLength === 0;
        },
    },
    methods: {
        exitVueWithRedirect() {
            window.removeEventListener("beforeunload", beforeUnloadHandler);
            window.location.href = `/projects/${this.projectId}/`;
        },
        removeActiveUpload() {
            xhrRef.abort();
        },
        removeUpload(id) {
            const index = this.pendingUploads.findIndex(
                (upload) => upload.id === id,
            );
            if (index === -1) {
                return;
            }
            const firstPart = this.pendingUploads.slice(0, index);
            const lastPart = this.pendingUploads.slice(index + 1);
            this.pendingUploads = firstPart.concat(lastPart);
        },
        async startNextJob() {
            console.assert(Number.isInteger(this.projectId));
            console.assert(this.activeUpload === null);

            if (this.isQueueEmpty) {
                // Waiting for 1 second to allow other requests to finish.
                setTimeout(() => this.exitVueWithRedirect(), 1000);
                return;
            }

            const upload = this.pendingUploads[0];

            const serverResult = await registerUpload(
                upload.file,
                this.projectId,
            );
            if (!serverResult) {
                // Something did not work during upload registration
                this.removeUpload(upload.id);
                this.startNextJob();
                return;
            }

            this.activeUpload = {
                ...upload,
                serverId: serverResult.id,
                serverFilename: serverResult.filename,
                transferred: 0,
                checksumProgress: 0,
                startedAt: new Date(),
            };
            this.pendingUploads = this.pendingUploads.slice(1);

            xhrRef = uploadFile({
                fileId: this.activeUpload.serverId,
                file: this.activeUpload.file,
                filename: this.activeUpload.serverFilename,
                onProgress: this.handleOnProgress,
                onEnd: this.handleOnEnd,
            });

            const checksum = await createChecksum(
                this.activeUpload.file,
                (progress) => {
                    if (this.activeUpload) {
                        this.activeUpload = {
                            ...this.activeUpload,
                            checksumProgress: progress,
                        };
                    }
                },
            );
            // Set checksum progress to 100% after checksum is calculated.
            if (this.activeUpload) {
                this.activeUpload = {
                    ...this.activeUpload,
                    checksumProgress: 1,
                };
            }

            await submitChecksum(this.activeUpload.serverId, checksum);
        },
        handleOnProgress(updatedTransferredValue) {
            if (!this.activeUpload) {
                return;
            }
            this.activeUpload = {
                ...this.activeUpload,
                transferred: updatedTransferredValue,
            };
        },
        handleOnEnd() {
            this.activeUpload = null;
            this.startNextJob();
            xhrRef = null;
        },
    },
    template: `
    <p class="u-ll">{{ $t('queue.large_files_hint') }}</p>
    <ul class="queue u-ll u-mt">
      <CurrentUpload v-if="activeUpload" :upload="activeUpload" @onCancel="removeActiveUpload" />
      <UploadQueueItem v-for="upload in pendingUploads" :key="upload.id" :upload="upload" @onCancel="removeUpload" />
    </ul>
  `,
};
