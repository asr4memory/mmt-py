<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDistance, addMilliseconds } from 'date-fns'
import { de } from 'date-fns/locale'
import { useQueueStore } from '@/stores/queue'
import formatBytes from '@/helpers/format-bytes'
import remainingTime from '@/helpers/remaining-time'
import CloseIcon from '@/icons/CloseIcon.vue'
import ProgressBar from './ProgressBar.vue'

const { locale } = useI18n()
const store = useQueueStore()

const timeToGo = computed(() => {
  const localeOptions: any = {}
  if (locale.value === 'de') {
    localeOptions.locale = de
  }

  let remainingMilliseconds: number
  let now = new Date()
  let futureDate = new Date()
  if (store.active && store.active.transferred) {
    remainingMilliseconds = remainingTime(
      store.active.startedAt,
      store.active.filesize,
      store.active.transferred
    )
    futureDate = addMilliseconds(now, remainingMilliseconds)
  }

  return formatDistance(futureDate, now, {
    ...localeOptions
  })
})

const sizeStr = computed(() => {
  return formatBytes(store.active?.filesize || 0, locale.value)
})

function handleCancelClick() {
  store.removeActive()
}
</script>

<template>
  <li class="queue-item queue-item--is-active">
    <div class="queue-item__body">
      <h3 class="queue-item__name">
        {{ store.active?.serverFilename }}
      </h3>
      <p class="queue-item__details">
        {{ sizeStr }} <span>– {{ timeToGo }}</span>
      </p>
      <ProgressBar
        id="upload-progress"
        :percentage="store.percentageFile"
        color=" #bed7ff"
        :label="$t('components.CurrentUpload.upload')"
      />
      <ProgressBar
        id="checksum-progress"
        :percentage="store.percentageChecksum"
        color=" #c7ffbe"
        :label="$t('components.CurrentUpload.checksum')"
      />
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
