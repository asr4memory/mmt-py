import { defineComponent, type PropType } from "vue";

import type { UploadStatus } from "./types";

export default defineComponent({
    name: "UploadStatusIcon",
    props: {
        status: { type: String as PropType<UploadStatus>, required: true },
    },
    template: `
    <svg viewBox="0 0 24 24">
      <template v-if="status === 'pending' || status === 'uploading'">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </template>
      <template v-else-if="status === 'uploaded'">
        <path d="M5 13l4 4L19 7" />
      </template>
      <template v-else-if="status === 'incomplete'">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8v5M12 16.5v.01" />
      </template>
      <template v-else>
        <path d="M6 6l12 12M18 6L6 18" />
      </template>
    </svg>
  `,
});
