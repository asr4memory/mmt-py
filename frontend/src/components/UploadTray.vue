<script setup lang="ts">
import { useQueueStore } from '@/stores/queue'
import UploadQueue from './UploadQueue.vue'

const store = useQueueStore()

function toggleTray() {
  store.trayOpen = !store.trayOpen;
}
</script>

<template>
  <div class="tray" :class="{ 'tray--is-open': store.trayOpen }">
    <button
      @click="toggleTray"
      type="button"
      tabindex="0"
      class="tray__header"
      :aria-label="$t('components.UploadTray.toggle')"
      >
        {{ $t('components.UploadTray.title') }}
        <span v-if="store.itemCount > 0">({{ store.itemCount }})</span>
    </button>
    <div class="tray__body">
      <UploadQueue />
    </div>
  </div>
</template>
