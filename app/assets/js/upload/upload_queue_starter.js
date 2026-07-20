import ChunkedUploadQueue from "./chunked_upload_queue.vue";
import UploadQueue from "./upload_queue.js";

export default {
    components: {
        ChunkedUploadQueue,
        UploadQueue,
    },
    props: ["projectId", "chunkedUpload", "chunkSize", "files"],
    template: `
    <ChunkedUploadQueue v-if="chunkedUpload" :project-id="projectId" :chunk-size="chunkSize" :files="files" />
    <UploadQueue v-else :project-id="projectId" :files="files" />
  `,
};
