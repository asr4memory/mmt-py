<script setup lang="ts">
import { useQueueStore } from '@/stores/queue'
import UploadQueue from './UploadQueue.vue'

const store = useQueueStore()
</script>

<template>
  <div class="tray" :class="{ 'tray--is-open': store.showUploadTray }">
    <header class="tray__header">
      <h3 class="tray__title">
        {{ $t('components.UploadTray.title') }}
        <span v-if="store.itemCount > 0">({{ store.itemCount }})</span>
      </h3>
      <button
        type="button"
        class="tray__handle"
        tabindex="0"
        :aria-label="$t('components.UploadTray.expand')"
      ></button>
    </header>
    <div class="tray__body">
      <UploadQueue />
    </div>
  </div>
</template>
