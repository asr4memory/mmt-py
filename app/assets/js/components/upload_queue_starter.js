import UploadQueue from "./upload_queue.js";

const FILESIZE_LIMIT = 1 * 1024 * 1024 * 1024 * 1024; // 1 TB

export default {
    components: {
        UploadQueue,
    },
    props: ["projectId", "files"],
    data() {
        return {
            error: null,
            loading: false,
            uploadJob: null,
        };
    },
    template: `
    <p>
      {{ $t('processing') }}
    </p>
    <UploadQueue :project-id="projectId" :files="files" />
  `,
};
