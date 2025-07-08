import { fetchWrapper } from "../helpers/fetch_wrapper.js";
import UploadQueue from "./upload_queue.js";

const FILESIZE_LIMIT = 1 * 1024 * 1024 * 1024 * 1024; // 1 TB

export default {
    components: {
        UploadQueue,
    },
    props: [
        "files",
        "title",
        "description",
        "language",
        "makeAvailableOnPlatform",
        "transcribe",
        "checkMediaFiles",
        "replaceExistingFiles",
    ],
    data() {
        return {
            error: null,
            loading: false,
            uploadJob: null,
        };
    },
    methods: {
        async createUploadJob() {
            this.error = null;
            this.loading = true;

            const result = await fetchWrapper
                .post('/upload-jobs/create/', {
                    title: this.title,
                    description: this.description,
                    language: this.language,
                    make_available_on_platform: this.makeAvailableOnPlatform,
                    transcribe: this.transcribe,
                    check_media_files: this.checkMediaFiles,
                    replace_existing_files: this.replaceExistingFiles,
                })
                .catch((err) => {
                    this.error = err.message;
                    console.log(err);
                    return null;
                });

            this.loading = false;
            this.uploadJob = result;
        },
    },
    mounted() {
        this.createUploadJob();
    },
    template: `
    <p>
      {{ $t('processing', { title }) }}
    </p>
    <UploadQueue v-if="uploadJob" :files="files"
                 :upload-job-id="uploadJob.id" />
  `,
};
