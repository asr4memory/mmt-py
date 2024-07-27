<script setup lang="ts">
import type { Header, Item } from 'vue3-easy-data-table'
import { useI18n } from 'vue-i18n'

import TrashIcon from '@/icons/TrashIcon.vue'
import CheckmarkIcon from '@/icons/CheckmarkIcon.vue'
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
  state: t(`components.UploadsTable.${upload.state}`),
  uploaded: new Date(upload.created).toLocaleString(),
  ok: upload.checksum_client === upload.checksum_server ? 'v' : 'x',
  actions: `<button>X</button`
}))

const deleteItem = (val: Item) => {
  props.onDelete(val.id, val.filename)
}
</script>

<template>
  <EasyDataTable :headers="headers" :items="items" :loading="loading" alternating>
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
