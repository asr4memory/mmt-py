<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useQueueStore } from '@/stores/queue'
import { fetchWrapper } from '@/helpers/fetch-wrapper'
import UploadButton from '@/components/UploadButton.vue'
import UploadsTable from '@/components/UploadsTable.vue'
import InlineMessage from '@/components/InlineMessage.vue'
import truncateText from '@/helpers/truncate-text'
import type { Upload } from '@/types'

const { t } = useI18n()
const store = useQueueStore()

const baseUrl = import.meta.env.VITE_API_URL

const route = useRoute()

const loading = ref(false)
const uploads = ref<Array<Upload> | null>(null)
const error = ref<string>('')

// watch the params of the route to fetch the data again
watch(() => route.params.id, fetchUploads, { immediate: true })

async function fetchUploads() {
  uploads.value = null
  error.value = ''
  loading.value = true

  uploads.value = await fetchWrapper.get(`${baseUrl}/uploads/`).catch((err) => {
    error.value = err
    return null
  })

  loading.value = false
}

async function handleDeleteClick(uploadId: number, filename: string) {
  const confirmed = confirm(
    t('views.UploadsView.confirmDelete', { filename: truncateText(filename, 20) })
  )

  if (!confirmed) {
    return
  }

  const result = await fetchWrapper.post(`${baseUrl}/uploads/${uploadId}/delete`).catch((err) => {
    error.value = err
    return null
  })
}

async function handleButtonClick(e: Event) {
  const fileInput = e.target as HTMLInputElement
  const files = fileInput.files as FileList
  const fileList = [...files]
  store.addJobsFromFiles(fileList)
}
</script>

<template>
  <main class="container u-mt u-mb-2">
    <h2>
      {{ $t('views.UploadsView.title') }}
    </h2>

    <InlineMessage v-if="error" type="error" class="u-mt">
      {{ $t(`${error}`) }}
    </InlineMessage>

    <UploadButton :on-change="handleButtonClick" class="u-mt" />
    <UploadsTable
      v-if="uploads"
      class="u-mt"
      :uploads="uploads"
      :loading="loading"
      :on-delete="handleDeleteClick"
    />
  </main>
</template>
