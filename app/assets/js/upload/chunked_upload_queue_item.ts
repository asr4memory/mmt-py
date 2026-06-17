import { computed, defineComponent, type PropType } from "vue";
import { useI18n } from "vue-i18n";

import formatBytes from "./format_bytes";
import formatEta from "./format_eta";
import CloseIcon from "../shared/close_icon.vue";
import UploadStatusIcon from "./upload_status_icon.js";
import type { Upload, UploadStatus } from "./types";

const CANCELLABLE: UploadStatus[] = ["pending", "uploading"];

export default defineComponent({
    name: "ChunkedUploadQueueItem",
    components: { CloseIcon, UploadStatusIcon },
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

        const etaStr = computed(() => formatEta(props.upload.eta) ?? "");

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
    <li v-if="upload.status == 'uploading'" class="chunked-queue-item" data-state="uploading">
      <div class="chunked-queue-item__header">
        <div class="chunked-queue-item__main">
          <div class="chunked-queue-item__file">{{ upload.file.name }}</div>
          <div class="chunked-queue-item__status">
            <UploadStatusIcon class="chunked-queue-item__glyph" :status="upload.status" />
            <span class="chunked-queue-item__status-label">{{ $t('queue.' + upload.status) }}</span>
          </div>
        </div>
        <div class="chunked-queue-item__controls">
          <button
            v-if="isCancellable"
            type="button"
            class="chunked-queue-item__close"
            :aria-label="$t('cancel')"
            :title="$t('cancel')"
            @click="$emit('onCancel', upload)"
          >
            <CloseIcon class="chunked-queue-item__icon icon-button__icon" />
          </button>
        </div>
      </div>
      <div class="chunked-queue-item__stats">
        <div class="chunked-queue-item__stat">
          <span class="chunked-queue-item__stat-label">{{ $t('queue.transferred') }}</span>
          <span class="chunked-queue-item__stat-value">{{ transferredStr }}</span>
        </div>
        <div class="chunked-queue-item__stat">
          <span class="chunked-queue-item__stat-label">{{ $t('queue.total') }}</span>
          <span class="chunked-queue-item__stat-value">{{ sizeStr }}</span>
        </div>
        <div v-if="speedStr" class="chunked-queue-item__stat">
          <span class="chunked-queue-item__stat-label">{{ $t('queue.speed') }}</span>
          <span class="chunked-queue-item__stat-value chunked-queue-item__speed">{{ speedStr }}</span>
        </div>
        <div v-if="etaStr" class="chunked-queue-item__stat">
          <span class="chunked-queue-item__stat-label">{{ $t('queue.eta') }}</span>
          <span class="chunked-queue-item__stat-value chunked-queue-item__eta">{{ etaStr }}</span>
        </div>
      </div>
      <div class="chunked-queue-item__progress">
        <progress class="chunked-queue-item__bar" :value="upload.transferred" :max="upload.file.size"></progress>
        <span class="chunked-queue-item__percent">{{ percentStr }}</span>
      </div>

      <div class="chunked-queue-item__footer">
        <div class="chunked-queue-item__checksum" :data-checksum="upload.checksumStatus">
          <span class="chunked-queue-item__checksum-label">{{ $t('checksum') }}</span>
          <span class="chunked-queue-item__checksum-dot"></span>
          <span class="chunked-queue-item__checksum-status">{{ upload.checksumStatus ? $t('queue.checksum_status_' + upload.checksumStatus) : '' }}</span>
        </div>
      </div>
    </li>
    <li v-else class="chunked-queue-item" :data-state="upload.status">
      <div class="chunked-queue-item__header">
        <div class="chunked-queue-item__main">
          <div class="chunked-queue-item__file">{{ upload.file.name }}</div>
          <div class="chunked-queue-item__status">
            <UploadStatusIcon class="chunked-queue-item__glyph" :status="upload.status" />
            <span class="chunked-queue-item__status-label">{{ $t('queue.' + upload.status) }}</span>
          </div>
        </div>
        <div class="chunked-queue-item__controls">
          <button
            v-if="isCancellable"
            type="button"
            class="chunked-queue-item__close"
            :aria-label="$t('cancel')"
            :title="$t('cancel')"
            @click="$emit('onCancel', upload)"
          >
            <CloseIcon class="chunked-queue-item__icon icon-button__icon" />
          </button>
        </div>
      </div>
      <div class="chunked-queue-item__meta">{{ transferredStr }} / {{ sizeStr }}</div>
    </li>
  `,
});
