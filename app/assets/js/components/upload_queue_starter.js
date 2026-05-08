import UploadQueue from "./upload_queue.js";

export default {
    components: {
        UploadQueue,
    },
    props: ["projectId", "chunkedUpload", "files"],
    template: `
    <p>
      {{ $t('processing') }}
    </p>
    <UploadQueue :project-id="projectId" :files="files" />
  `,
};
