import createChecksum from "../helpers/create_checksum.js";
import CurrentUpload from "./current_upload.js";
import FileStorage from "../helpers/file_storage.js";
import getNextFileId from "../helpers/get_next_file_id.js";
import registerUpload from "../helpers/register_upload.js";
import sendFile from "../helpers/send_file.js";
import submitChecksum from "../helpers/submit_checksum.js";
import UploadQueueItem from "./upload_queue_item.js";

let xhrRef = null;
const storedFiles = new FileStorage();

export default {
    components: {
        CurrentUpload,
        UploadQueueItem,
    },
    props: ["files", "uploadJobId"],
    data() {
        const files = this.files || [];
        return {
            activeJob: null,
            pending: files.map((file) => {
                const id = getNextFileId();
                storedFiles.storeFile(id, file);
                return {
                    jobId: id,
                    filename: file.name,
                    filesize: file.size,
                };
            }),
        };
    },
    async mounted() {
        while (this.queueHasItems) {
            await this.processQueue();
        }
        this.redirectToUploadJobDetailPage();
    },
    computed: {
        itemCount() {
            const queueLength = this.pending.length;
            return this.activeJob ? queueLength + 1 : queueLength;
        },
        isEmpty() {
            return this.itemCount === 0;
        },
        queueHasItems() {
            return this.pending.length > 0;
        }
    },
    methods: {
        redirectToUploadJobDetailPage() {
            /* Redirect and leave Vue.js app. */
            this.$nextTick(() => {
                window.location.href = `/${this.$i18n.locale}/upload-jobs/${this.uploadJobId}/`;
            });
        },
        async prepareNextJob() {
            const nextJob = this.pending[0];
            const nextJobId = nextJob.jobId;
            const nextJobFile = storedFiles.getFile(nextJobId);

            const registeredUpload = await registerUpload(nextJobFile, this.uploadJobId);
            if (!registeredUpload) {
                // Something did not work during upload registration
                return;
            }

            const result = {
                jobId: nextJobId,
                serverId: registeredUpload.id,
                serverFilename: registeredUpload.filename,
                chunkCount: registeredUpload.chunk_count,
                chunksTransferred: registeredUpload.chunks_transferred,
                nextChunk: registeredUpload.next_chunk,
                file: nextJobFile,
                filesize: nextJobFile.size,
                transferred: 0,
                checksumProgress: 0,
                startedAt: new Date(),
            };
            return result;
        },
        dequeue() {
            this.pending = this.pending.slice(1);
        },
        async calculateChecksum(file) {
            const checksum = await createChecksum(file, (progress) => {
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
            return checksum;
        },
        removeActive() {
            const activeJob = this.activeJob;
            xhrRef.abort();
            if (activeJob) {
                storedFiles.removeFile(activeJob.jobId);
            }
            this.activeJob = null;
            this.startNextJob();
        },
        removeItem(idToRemove) {
            const index = this.pending.findIndex((upload) => upload.jobId === idToRemove);
            if (index === -1) {
                return;
            }
            const firstPart = this.pending.slice(0, index);
            const lastPart = this.pending.slice(index + 1);
            this.pending = firstPart.concat(lastPart);
        },
        async processQueue() {
            this.activeJob = await this.prepareNextJob();
            this.dequeue();

            console.log(this.activeJob);
            const checksum = await this.calculateChecksum(this.activeJob.file);
            await submitChecksum(this.activeJob.serverId, checksum);
            await sendFile(this.activeJob.serverId, this.activeJob.file, (updatedTransferredValue) => {
                console.log(updatedTransferredValue);
                this.activeJob = {
                    ...this.activeJob,
                    transferred: updatedTransferredValue,
                };
            });

            this.activeJob = null;
        },
    },
    template: `
    <ul class="queue u-ll u-mt">
      <CurrentUpload v-if="activeJob" :upload="activeJob" @onCancelActive="removeActive" />
      <UploadQueueItem v-for="job in pending" :key="job.jobId" :upload="job" @onCancel="removeItem" />
    </ul>
  `,
};
