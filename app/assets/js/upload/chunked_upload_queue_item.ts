import { computed, defineComponent, type PropType } from "vue";
import { useI18n } from "vue-i18n";

import formatBytes from "./format_bytes.js";
import CloseIcon from "../shared/close_icon.js";
import type { Upload, UploadStatus } from "./types";

const CANCELLABLE: UploadStatus[] = ["pending", "uploading"];

export default defineComponent({
    name: "ChunkedUploadQueueItem",
    components: { CloseIcon },
    props: {
        upload: { type: Object as PropType<Upload>, required: true },
    },
    emits: ["onCancel"],
    setup(props) {
        const { locale } = useI18n();

        const sizeStr = computed(() =>
            formatBytes(props.upload.file.size, locale.value),
        );

        const transferredStr = computed(() =>
            formatBytes(props.upload.transferred, locale.value),
        );

        const isCancellable = computed(() =>
            CANCELLABLE.includes(props.upload.status),
        );

        return { sizeStr, transferredStr, isCancellable };
    },
    template: `
    <li :class="['chunked-queue-item', 'chunked-queue-item--' + upload.status]">
      <progress class="chunked-queue-item__progress" :value="upload.transferred" :max="upload.file.size"></progress>
      <div class="chunked-queue-item__body">
        <h3 class="chunked-queue-item__name">{{ upload.file.name }}</h3>
        <p class="chunked-queue-item__details">{{ transferredStr }} / {{ sizeStr }} – {{ $t('queue.' + upload.status) }}</p>
      </div>
      <button
        v-if="isCancellable"
        type="button"
        class="chunked-queue-item__button"
        :aria-label="$t('cancel')"
        :title="$t('cancel')"
        @click="$emit('onCancel', upload)"
      >
        <CloseIcon class="chunked-queue-item__icon icon-button__icon" />
      </button>
    </li>
  `,
});
