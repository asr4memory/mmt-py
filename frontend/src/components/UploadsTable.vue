<script setup lang="ts">
import type { Header, Item } from 'vue3-easy-data-table'
import { useI18n } from 'vue-i18n'

import formatBytes from '@/helpers/format-bytes'
import formatDate from '@/helpers/format-date'
import TrashIcon from '@/icons/TrashIcon.vue'
import CheckmarkIcon from '@/icons/CheckmarkIcon.vue'
import BugIcon from '@/icons/BugIcon.vue'
import type { Upload } from '@/types'

const { t } = useI18n()

const props = defineProps<{
  uploads: Array<Upload>
  loading: boolean
  onDelete: (uploadId: number, fileName: string) => Promise<void>
}>()

const headers: Header[] = [
  { text: t('components.UploadsTable.id'), value: 'id', sortable: true },
  { text: t('components.UploadsTable.filename'), value: 'filename', sortable: true },
  { text: t('components.UploadsTable.mediaType'), value: 'mediaType', sortable: true },
  { text: t('components.UploadsTable.size'), value: 'size', sortable: true },
  { text: t('components.UploadsTable.state'), value: 'state', sortable: true },
  { text: t('components.UploadsTable.uploaded'), value: 'uploaded', sortable: true },
  { text: t('components.UploadsTable.ok'), value: 'ok', sortable: true },
  { text: t('components.UploadsTable.actions'), value: 'actions' }
]

const items: Item[] = props.uploads.map((upload) => ({
  key: upload.id,
  id: upload.id,
  filename: upload.filename,
  mediaType: upload.content_type,
  size: upload.size,
  state: t(`components.UploadsTable.${upload.state}`),
  uploaded: new Date(upload.created),
  ok: { checksumServer: upload.checksum_server, checksumClient: upload.checksum_client },
  actions: `<button>X</button`
}))

const deleteItem = (val: Item) => {
  props.onDelete(val.id, val.filename)
}
</script>

<template>
  <EasyDataTable :headers="headers" :items="items" :loading="loading" alternating>
    <template #item-size="item">
      <span :title="`${item.size.toLocaleString($i18n.locale)} Bytes`">
        {{ formatBytes(item.size, $i18n.locale) }}
      </span>
    </template>
    <template #item-uploaded="item">
      <time
        :datetime="item.uploaded.toISOString()"
        :title="formatDate(item.uploaded, $i18n.locale, true)"
      >
        {{ formatDate(item.uploaded, $i18n.locale) }}
      </time>
    </template>
    <template #item-ok="item">
      <span
        v-if="item.ok.checksumClient == item.ok.checksumServer"
        :title="$t('components.UploadsTable.checksumMatch', { checksum: item.ok.checksumClient })"
      >
        <CheckmarkIcon class="icon icon--ok" />
      </span>
      <span
          v-else
          :title="$t('components.UploadsTable.checksumMismatch', { checksumServer: item.ok.checksumServer, checksumClient: item.ok.checksumClient })"
      >
          <BugIcon class="icon icon--warning" />
      </span>
    </template>
    <template #item-actions="item">
      <div>
        <button
          type="button"
          class="icon-button icon-button--danger"
          @click="deleteItem(item)"
          :title="$t('components.UploadsTable.delete')"
          :aria-label="$t('components.UploadsTable.delete')"
        >
          <TrashIcon class="icon-button__icon" aria-hidden="true" />
        </button>
      </div>
    </template>
  </EasyDataTable>
</template>
