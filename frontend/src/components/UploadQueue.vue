<script setup lang="ts">
import { useQueueStore } from '@/stores/queue'
import CurrentUpload from './CurrentUpload.vue'
import UploadQueueItem from './UploadQueueItem.vue'

const store = useQueueStore()
</script>

<template>
  <ul>
    <CurrentUpload v-if="store.active" />
    <UploadQueueItem v-for="job in store.pending" :key="job.jobId" :upload="job" />
  </ul>
</template>
