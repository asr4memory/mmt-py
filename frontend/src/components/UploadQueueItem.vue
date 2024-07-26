<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useQueueStore } from '@/stores/queue'
import formatBytes from '@/helpers/format-bytes'
import CloseIcon from '@/icons/CloseIcon.vue'
import type { PendingUpload } from '@/types'

const { locale } = useI18n()
const store = useQueueStore()

const props = defineProps<{
  upload: PendingUpload
}>()

const sizeStr = formatBytes(props.upload.filesize, locale.value)
function handleCancelClick() {
  store.removeJob(props.upload.jobId)
}
</script>

<template>
  <li class="queue-item">
    <div class="queue-item__body">
      <h3 class="queue-item__name">{{ upload.filename }}</h3>
      <p class="queue-item__details">{{ sizeStr }}</p>
    </div>
    <div class="queue-item__actions">
      <button
        type="button"
        class="queue-item__button icon-button"
        :aria-label="$t('components.UploadQueue.cancel')"
        :title="$t('components.UploadQueue.cancel')"
        @click="handleCancelClick"
      >
        <CloseIcon class="queue-item__icon icon-button__icon" />
      </button>
    </div>
  </li>
</template>
