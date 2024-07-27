<script setup lang="ts">
import type { Header, Item } from 'vue3-easy-data-table'
import { useI18n } from 'vue-i18n'

import DownloadIcon from '@/icons/DownloadIcon.vue'
import formatBytes from '@/helpers/format-bytes'
import formatDate from '@/helpers/format-date'
import type { DownloadableFile } from '@/types'

const baseUrl = `${import.meta.env.VITE_API_URL}`

const { t } = useI18n()

const props = defineProps<{
  downloads: Array<DownloadableFile>
  loading: boolean
}>()

const headers: Header[] = [
  { text: t('components.DownloadsTable.filename'), value: 'filename', sortable: true },
  { text: t('components.DownloadsTable.type'), value: 'type', sortable: true },
  { text: t('components.DownloadsTable.size'), value: 'size', sortable: true },
  { text: t('components.DownloadsTable.modified'), value: 'modified', sortable: true },
  { text: t('components.DownloadsTable.actions'), value: 'actions' }
]

const items: Item[] = props.downloads.map((download) => ({
  key: download.filename,
  filename: download.filename,
  type: download.type,
  size: download.size,
  modified: download.modified,
  actions: `<button>X</button`
}))
</script>

<template>
  <EasyDataTable :headers="headers" :items="items" :loading="loading" alternating>
    <template #item-size="item">
      <span :title="`${item.size.toLocaleString($i18n.locale)} Bytes`">
        {{ formatBytes(item.size, $i18n.locale) }}
      </span>
    </template>
    <template #item-modified="item">
      <span :title="formatDate(item.modified, $i18n.locale, true)">
        {{ formatDate(item.modified, $i18n.locale) }}
      </span>
    </template>
    <template #item-actions="item">
      <a
        class="icon-link"
        :href="`${baseUrl}/downloads/${item.filename}`"
        download
        :aria-label="$t('components.DownloadsTable.download')"
        :title="$t('components.DownloadsTable.download')"
      >
        <DownloadIcon class="icon-link__icon" aria-hidden="true" />
      </a>
    </template>
  </EasyDataTable>
</template>
