import formatBytes from "./format_bytes.js";
import CloseIcon from "../shared/close_icon.vue";

export default {
    components: {
        CloseIcon,
    },
    props: ["upload"],
    computed: {
        sizeStr() {
            return formatBytes(this.upload.file.size, this.$i18n.locale);
        },
    },
    template: `
    <li class="queue-item">
      <div class="queue-item__body">
        <h3 class="queue-item__name">{{ upload.file.name }}</h3>
        <p class="queue-item__details">{{ sizeStr }}</p>
      </div>
      <div class="queue-item__actions">
        <button
          type="button"
          class="queue-item__button icon-button"
          :aria-label="$t('cancel')"
          :title="$t('cancel')"
          @click="$emit('onCancel', upload.id)"
        >
          <CloseIcon class="queue-item__icon icon-button__icon" />
        </button>
      </div>
    </li>
  `,
};
