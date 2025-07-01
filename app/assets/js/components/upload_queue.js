import addFile from "../helpers/add_file.js";
import createChecksum from "../helpers/create_checksum.js";
import FileStorage from "../helpers/file_storage.js";
import getNextFileId from "../helpers/get_next_file_id.js";
import registerUpload from "../helpers/register_upload.js";
import submitChecksum from "../helpers/submit_checksum.js";
import sendFile from '../helpers/send_file.js';
import CurrentUpload from "./current_upload.js";
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
            pending: files.map((file) => {
                const id = getNextFileId();
                storedFiles.storeFile(id, file);
                return {
                    jobId: id,
                    filename: file.name,
                    filesize: file.size,
                };
            }),
            active: null,
        };
    },
    mounted() {
        this.startNextJob();
    },
    computed: {
        itemCount() {
            let result = this.pending.length;
            if (this.active) {
                result += 1;
            }
            return result;
        },
        isEmpty() {
            return this.itemCount === 0;
        },
    },
    methods: {
        removeActive() {
            const activeJob = this.active;
            xhrRef.abort();
            if (activeJob) {
                storedFiles.removeFile(activeJob.jobId);
            }
            this.active = null;
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
        async startNextJob() {
            if (this.pending.length === 0) {
                /*
                 * Queue is empty, job done.
                 * This is where we leave the Vue.js app.
                 * Redirect to upload job detail page.
                 * Waiting for 1 second to allow other requests to finish.
                 */
                setTimeout(() => {
                    window.location.href = `/${this.$i18n.locale}/upload-jobs/${this.uploadJobId}/`;
                }, 1000);
                return;
            }

            if (this.active || !this.uploadJobId) {
                /* This should never be reached. */
                return;
            }

            const nextJob = this.pending[0];
            const nextJobId = nextJob.jobId;
            const nextJobFile = storedFiles.getFile(nextJobId);

            const registeredUpload = await registerUpload(nextJobFile, this.uploadJobId);
            if (!registeredUpload) {
                // Something did not work during upload registration
                return;
            }

            const registeredJob = {
                jobId: nextJobId,
                serverId: registeredUpload.id,
                serverFilename: registeredUpload.filename,
                chunkCount: registeredUpload.chunk_count,
                chunksTransferred: registeredUpload.chunks_transferred,
                nextChunk: registeredUpload.next_chunk,
                filesize: nextJobFile.size,
                transferred: 0,
                checksumProgress: 0,
                startedAt: new Date(),
            };

            this.active = registeredJob;
            this.pending = this.pending.slice(1);

            sendFile(registeredJob.serverId, nextJobFile);

            const checksum = await createChecksum(nextJobFile, (progress) => {
                if (this.active) {
                    this.active = {
                        ...this.active,
                        checksumProgress: progress,
                    };
                }
            });
            // Set checksum progress to 100% after checksum is calculated.
            if (this.active) {
                this.active = {
                    ...this.active,
                    checksumProgress: 1,
                };
            }

            const result = await submitChecksum(registeredJob.serverId, checksum);
        },
    },
    template: `
    <ul class="queue u-ll u-mt">
      <CurrentUpload v-if="active" :upload="active" @onCancelActive="removeActive" />
      <UploadQueueItem v-for="job in pending" :key="job.jobId" :upload="job" @onCancel="removeItem" />
    </ul>
  `,
};
