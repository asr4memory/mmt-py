import formatBytes from "../helpers/format_bytes.js";
import CloseIcon from "./close_icon.js";

const CANCELLABLE = ["pending", "uploading"];

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
    <li :class="['queue-item', 'queue-item--' + upload.status]">
      <div class="queue-item__body">
        <h3 class="queue-item__name">{{ upload.file.name }}</h3>
        <p class="queue-item__details">{{ sizeStr }}</p>
      </div>
      <div class="queue-item__actions">
        <button
          v-if="isCancellable"
          type="button"
          class="queue-item__button icon-button"
          :aria-label="$t('cancel')"
          :title="$t('cancel')"
          @click="$emit('onCancel', upload)"
        >
          <CloseIcon class="queue-item__icon icon-button__icon" />
        </button>
      </div>
    </li>
  `,
};
