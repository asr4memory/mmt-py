import { computed, defineComponent, type PropType } from "vue";
import { useI18n } from "vue-i18n";

import formatBytes from "./format_bytes.js";
import formatEta from "./format_eta";
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
        const { t, locale } = useI18n();

        const sizeStr = computed(() =>
            formatBytes(props.upload.file.size, locale.value),
        );

        const transferredStr = computed(() =>
            formatBytes(props.upload.transferred, locale.value),
        );

        const isCancellable = computed(() =>
            CANCELLABLE.includes(props.upload.status),
        );

        const isUploading = computed(() => props.upload.status === "uploading");

        const percentStr = computed(() => {
            const { transferred, file } = props.upload;
            if (!file.size) return "0 %";
            return `${Math.floor((transferred / file.size) * 100)} %`;
        });

        const speedStr = computed(() =>
            props.upload.speed > 0
                ? `${formatBytes(props.upload.speed, locale.value)}/s`
                : "",
        );

        const etaStr = computed(() => {
            const label = formatEta(props.upload.eta);
            return label ? t(label.key, label.params ?? {}) : "";
        });

        const isChecksumComplete = computed(
            () => props.upload.checksumStatus === "complete",
        );

        return {
            sizeStr,
            transferredStr,
            isCancellable,
            isUploading,
            percentStr,
            speedStr,
            etaStr,
            isChecksumComplete,
        };
    },
    template: `
    <li :class="['chunked-queue-item', 'chunked-queue-item--' + upload.status]">
      <progress class="chunked-queue-item__progress" :value="upload.transferred" :max="upload.file.size"></progress>
      <div class="chunked-queue-item__body">
        <h3 class="chunked-queue-item__name">
          {{ upload.file.name }}
          <span
            v-if="isChecksumComplete"
            class="chunked-queue-item__checksum-dot"
            :title="$t('queue.checksum_complete')"
            :aria-label="$t('queue.checksum_complete')"
          ></span>
        </h3>
        <p class="chunked-queue-item__details">{{ transferredStr }} / {{ sizeStr }} – {{ $t('queue.' + upload.status) }}</p>
        <p v-if="isUploading" class="chunked-queue-item__stats">
          <span class="chunked-queue-item__percent">{{ percentStr }}</span>
          <span v-if="speedStr" class="chunked-queue-item__speed">{{ speedStr }}</span>
          <span v-if="etaStr" class="chunked-queue-item__eta">{{ etaStr }}</span>
        </p>
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
