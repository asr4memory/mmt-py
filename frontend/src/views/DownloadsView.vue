<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { fetchWrapper } from '@/helpers/fetch-wrapper'
import InlineMessage from '@/components/InlineMessage.vue'
import DownloadsTable from '@/components/DownloadsTable.vue'
import type { DownloadableFile } from '@/types'

const baseUrl = `${import.meta.env.VITE_API_URL}`

const route = useRoute()

const loading = ref(false)
const downloads = ref<Array<DownloadableFile> | null>(null)
const error = ref<string>('')

// watch the params of the route to fetch the data again
watch(() => route.params.id, fetchDownloads, { immediate: true })

async function fetchDownloads() {
  downloads.value = null
  error.value = ''
  loading.value = true

  downloads.value = await fetchWrapper.get(`${baseUrl}/downloads/`).catch((err) => {
    error.value = err
    return []
  })

  loading.value = false
}
</script>

<template>
  <main class="container u-mt u-mb-2">
    <h2>
      {{ $t('views.DownloadsView.title') }}
    </h2>

    <InlineMessage v-if="error" type="error" class="u-mt">
      {{ $t(`${error}`) }}
    </InlineMessage>

    <DownloadsTable v-if="downloads" class="u-mt" :downloads="downloads" :loading="loading" />
  </main>
</template>
