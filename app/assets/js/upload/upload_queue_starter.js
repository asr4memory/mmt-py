import ChunkedUploadQueue from "./chunked_upload_queue";
import UploadQueue from "./upload_queue.js";

export default {
    components: {
        ChunkedUploadQueue,
        UploadQueue,
    },
    props: ["projectId", "chunkedUpload", "files"],
    template: `
    <p>
      {{ $t('processing') }}
    </p>
    <ChunkedUploadQueue v-if="chunkedUpload" :project-id="projectId" :files="files" />
    <UploadQueue v-else :project-id="projectId" :files="files" />
  `,
};
