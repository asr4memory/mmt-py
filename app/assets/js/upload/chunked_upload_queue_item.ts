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

        const percentStrCss = computed(() => {
            const { transferred, file } = props.upload;
            if (!file.size) return "0%";
            return `${Math.floor((transferred / file.size) * 100)}%`;
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
            percentStrCss,
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
            <!--svg class="chunked-queue-item__glyph" viewBox="0 0 24 24">…</svg-->
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
        <div class="chunked-queue-item__stat">
          <span class="chunked-queue-item__stat-label">{{ $t('queue.speed') }}</span>
          <span class="chunked-queue-item__stat-value">{{ speedStr }}</span>
        </div>
        <div class="chunked-queue-item__stat">
          <span class="chunked-queue-item__stat-label">{{ $t('queue.eta') }}</span>
          <span class="chunked-queue-item__stat-value">{{ etaStr }}</span>
        </div>
      </div>
      <div class="chunked-queue-item__progress">
        <div class="chunked-queue-item__bar">
          <div class="chunked-queue-item__bar-fill" :style="'--qi-progress: ' + percentStrCss"></div>
        </div>
        <span class="chunked-queue-item__percent">{{ percentStr }}</span>
      </div>

      <div class="chunked-queue-item__footer">
        <div class="chunked-queue-item__checksum" :data-checksum="upload.checksumStatus">
          <span class="chunked-queue-item__checksum-label">{{ $t('checksum') }}</span>
          <span class="chunked-queue-item__checksum-dot"></span>
          <span class="chunked-queue-item__checksum-status">{{ $t('queue.checksum_status_' + upload.checksumStatus) }}</span>
        </div>
      </div>
    </li>
    <li v-else class="chunked-queue-item" :data-state="upload.status">
      <div class="chunked-queue-item__header">
        <div class="chunked-queue-item__main">
          <div class="chunked-queue-item__file">{{ upload.file.name }}</div>
          <div class="chunked-queue-item__status">
            <!--svg class="chunked-queue-item__glyph" viewBox="0 0 24 24">…</svg-->
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
      <div class="chunked-queue-item__meta">{{ sizeStr }}</div>
    </li>
  `,
});
