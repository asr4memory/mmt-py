<script setup lang="ts">
import type { Header, Item } from 'vue3-easy-data-table'
import { useI18n } from 'vue-i18n'

import type { User } from '@/types'

const { t } = useI18n()

const props = defineProps<{
  users: Array<User>
  loading: boolean
}>()

const headers: Header[] = [
  { text: t('components.UsersTable.id'), value: 'id', sortable: true },
  { text: t('components.UsersTable.username'), value: 'username', sortable: true },
  { text: t('components.UsersTable.email'), value: 'email', sortable: true },
  { text: t('components.UsersTable.locale'), value: 'locale', sortable: true },
  { text: t('components.UsersTable.activated'), value: 'activated', sortable: true },
  { text: t('components.UsersTable.admin'), value: 'admin', sortable: true },
  { text: t('components.UsersTable.canUpload'), value: 'canUpload', sortable: true },
  { text: t('components.UsersTable.actions'), value: 'actions' }
]

const items: Item[] = props.users.map((user) => ({
  key: user.id,
  id: user.id,
  username: user.username,
  email: user.email,
  locale: user.locale,
  activated: user.activated,
  admin: user.admin,
  canUpload: user.can_upload,
  actions: `<button>X</button`
}))
</script>

<template>
  <EasyDataTable :headers="headers" :items="items" :loading="loading" alternating>

  </EasyDataTable>
</template>
