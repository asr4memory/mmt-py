<script setup lang="ts">
import type { Header, Item } from 'vue3-easy-data-table'
import { useI18n } from 'vue-i18n'

import type { User } from '@/types'
import CheckmarkIcon from '@/icons/CheckmarkIcon.vue'
import CloseIcon from "@/icons/CloseIcon.vue";
import LockOpenIcon from "@/icons/LockOpenIcon.vue";
import BugIcon from "@/icons/BugIcon.vue";

const { t } = useI18n()

const props = defineProps<{
  users: Array<User>
  loading: boolean,
  onActivate: (userId: number, username: string) => Promise<void>
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
  locale: t(`general.locales.${user.locale}`),
  activated: user.activated,
  admin: user.admin,
  canUpload: user.can_upload,
  actions: `<button>X</button`
}))

const activateUser = (val: Item) => {
  props.onActivate(val.id, val.username)
}
</script>

<template>
  <EasyDataTable :headers="headers" :items="items" :loading="loading" alternating>
    <template #item-activated="item">
      <span
        :title="$t('components.UsersTable.true')"
        :aria-label="$t('components.UsersTable.true')"
      >
        <CheckmarkIcon v-if="item.activated" class="icon icon--ok" />
        <CloseIcon v-else class="icon icon--warning" />
      </span>
    </template>
    <template #item-admin="item">
      <CheckmarkIcon v-if="item.admin" class="icon icon--ok" />
      <CloseIcon v-else class="icon icon--warning" />
    </template>
    <template #item-canUpload="item">
      <CheckmarkIcon v-if="item.canUpload" class="icon icon--ok" />
      <CloseIcon v-else class="icon icon--warning" />
    </template>
    <template #item-actions="item">
      <button
        v-if="!item.activated"
        type="button"
        class="icon-button icon-button--ok"
        @click="activateUser(item)"
        :title="$t('components.UsersTable.activate')"
        :aria-label="$t('components.UsersTable.activate')"
      >
        <LockOpenIcon class="icon-button__icon" aria-hidden="true" />
      </button>
    </template>
  </EasyDataTable>
</template>
