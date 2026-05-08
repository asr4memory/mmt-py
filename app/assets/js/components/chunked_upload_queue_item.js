import formatBytes from "../helpers/format_bytes.js";
import CloseIcon from "./close_icon.js";

const CANCELLABLE = ["pending", "uploading"];

/*
 * Status can be:
 * pending
 * uploading
 * uploaded
 * cancelled
 * incomplete
 */

export default {
    components: { CloseIcon },
    props: ["upload"],
    computed: {
        sizeStr() {
            return formatBytes(this.upload.file.size, this.$i18n.locale);
        },
        isCancellable() {
            return CANCELLABLE.includes(this.upload.status);
        },
    },
    template: `
    <li :class="['chunked-queue-item', 'chunked-queue-item--' + upload.status]">
      <div class="chunked-queue-item__body">
        <h3 class="chunked-queue-item__name">{{ upload.file.name }}</h3>
        <p class="chunked-queue-item__details">{{ sizeStr }} – {{ $t('queue.' + upload.status) }}</p>
      </div>
      <div class="chunked-queue-item__actions">
        <button
          v-if="isCancellable"
          type="button"
          class="chunked-queue-item__button icon-button"
          :aria-label="$t('cancel')"
          :title="$t('cancel')"
          @click="$emit('onCancel', upload)"
        >
          <CloseIcon class="chunked-queue-item__icon icon-button__icon" />
        </button>
      </div>
    </li>
  `,
};
