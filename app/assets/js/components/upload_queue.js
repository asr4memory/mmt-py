import addFile from "../helpers/add_file.js";
import createChecksum from "../helpers/create_checksum.js";
import FileStorage from "../helpers/file_storage.js";
import registerUpload from "../helpers/register_upload.js";
import submitChecksum from "../helpers/submit_checksum.js";
import CurrentUpload from "./current_upload.js";
import UploadQueueItem from "./upload_queue_item.js";

let xhrRef = null;
const storedFiles = new FileStorage();

function beforeUnloadHandler(event) {
    event.preventDefault();

    // Included for legacy support, e.g. Chrome/Edge < 119
    event.returnValue = true;
}

export default {
    components: {
        CurrentUpload,
        UploadQueueItem,
    },
    props: ["files", "projectId"],
    data() {
        const pendingJobs = [];
        this.files?.forEach((file) => {
            const id = storedFiles.storeFile(file);
            pendingJobs.push({
                jobId: id,
                filename: file.name,
                filesize: file.size,
            });
        });
        return {
            pendingJobs,
            activeJob: null,
        };
    },
    mounted() {
        this.addBeforeUnloadListener();
        this.startNextJob();
    },
    computed: {
        itemCount() {
            return this.activeJob ?
                this.pendingJobs.length + 1 :
                this.pendingJobs.length;
        },
        isEmpty() {
            return this.itemCount === 0;
        },
    },
    methods: {
        addBeforeUnloadListener() {
            window.addEventListener('beforeunload', beforeUnloadHandler);
        },
        removeBeforeUnloadListener() {
            window.removeEventListener('beforeunload', beforeUnloadHandler);
        },
        redirectToProjectDetailPage() {
            window.location.href = `/projects/${this.projectId}/`;
        },
        removeActiveJob() {
            xhrRef.abort();
            if (this.activeJob) {
                storedFiles.removeFile(this.activeJob.jobId);
            }
            this.activeJob = null;
            this.startNextJob();
        },
        removeItem(idToRemove) {
            const index = this.pendingJobs.findIndex(
                (upload) => upload.jobId === idToRemove,
            );
            if (index === -1) {
                return;
            }
            const firstPart = this.pendingJobs.slice(0, index);
            const lastPart = this.pendingJobs.slice(index + 1);
            this.pendingJobs = firstPart.concat(lastPart);
        },
        async startNextJob() {
            if (this.pendingJobs.length === 0) {
                // Waiting for 1 second to allow other requests to finish.
                setTimeout(() => {
                    this.removeBeforeUnloadListener();
                    this.redirectToProjectDetailPage();
                }, 1000);
                return;
            }

            if (this.activeJob || !this.projectId) {
                /* This should never be reached. */
                return;
            }

            const nextJob = this.pendingJobs[0];
            const nextJobId = nextJob.jobId;
            const nextJobFile = storedFiles.getFile(nextJobId);

            const registeredUpload = await registerUpload(
                nextJobFile,
                this.projectId,
            );
            if (!registeredUpload) {
                // Something did not work during upload registration
                return;
            }

            const registeredJob = {
                jobId: nextJobId,
                serverId: registeredUpload.id,
                serverFilename: registeredUpload.filename,
                filesize: nextJobFile.size,
                transferred: 0,
                checksumProgress: 0,
                startedAt: new Date(),
            };

            this.activeJob = registeredJob;
            this.pendingJobs = this.pendingJobs.slice(1);

            const request = addFile({
                fileId: registeredJob.serverId,
                file: nextJobFile,
                filename: registeredJob.serverFilename,
                onProgress: (updatedTransferredValue) => {
                    if (this.activeJob) {
                        this.activeJob = {
                            ...this.activeJob,
                            transferred: updatedTransferredValue,
                        };
                    }
                },
                onEnd: () => {
                    this.activeJob = null;
                    this.startNextJob();
                    xhrRef = null;
                },
                onAbort: () => {
                    // onEnd will also catch aborted uploads.
                    console.log("onAbort executed");
                },
            });
            xhrRef = request;

            const checksum = await createChecksum(nextJobFile, (progress) => {
                if (this.activeJob) {
                    this.activeJob = {
                        ...this.activeJob,
                        checksumProgress: progress,
                    };
                }
            });
            // Set checksum progress to 100% after checksum is calculated.
            if (this.activeJob) {
                this.activeJob = {
                    ...this.activeJob,
                    checksumProgress: 1,
                };
            }

            await submitChecksum(registeredJob.serverId, checksum);
        },
    },
    template: `
    <ul class="queue u-ll u-mt">
      <CurrentUpload v-if="activeJob" :upload="activeJob" @onCancel="removeActiveJob" />
      <UploadQueueItem v-for="job in pendingJobs" :key="job.jobId" :upload="job" @onCancel="removeItem" />
    </ul>
  `,
};
