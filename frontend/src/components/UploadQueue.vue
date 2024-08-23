<script setup lang="ts">
import { useQueueStore } from '@/stores/queue'
import CurrentUpload from './CurrentUpload.vue'
import UploadQueueItem from './UploadQueueItem.vue'

const store = useQueueStore()
</script>

<template>
  <p v-if="store.isEmpty" class="u-mt u-mr u-mb u-ml">
    {{ $t('components.UploadQueue.noJobs') }}
  </p>
  <ul v-else>
    <CurrentUpload v-if="store.active" />
    <UploadQueueItem v-for="job in store.pending" :key="job.jobId" :upload="job" />
  </ul>
</template>
