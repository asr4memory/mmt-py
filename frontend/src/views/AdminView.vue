<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { fetchWrapper } from '@/helpers/fetch-wrapper'
import InlineMessage from '@/components/InlineMessage.vue'
import UsersTable from '@/components/UsersTable.vue'
import type { User } from '@/types'

const baseUrl = `${import.meta.env.VITE_API_URL}`

const route = useRoute()
const { t } = useI18n()

const loading = ref(false)
const users = ref<Array<User> | null>(null)
const error = ref<string>('')

// watch the params of the route to fetch the data again
// not useful in our case... we just need to fetch it once.
watch(() => route.params.id, fetchUsers, { immediate: true })

async function fetchUsers() {
  users.value = null
  error.value = ''
  loading.value = true

  users.value = await fetchWrapper.get(`${baseUrl}/admin/users`).catch((err) => {
    error.value = err
    return []
  })

  loading.value = false
}

async function handleActivateClick(userId: number, username: string) {
  const confirmed = confirm(
    t('views.AdminView.confirmActivation', { username })
  )

  if (!confirmed) {
    return
  }

  const result = await fetchWrapper.post(`${baseUrl}/admin/users/${userId}/activate`).catch((err) => {
    error.value = err
    return null
  })
}
</script>

<template>
  <main class="container u-mt u-mb-2">
    <h2>
      {{ $t('views.AdminView.title') }}
    </h2>

    <InlineMessage v-if="error" type="error" class="u-mt">
      {{ $t(`${error}`) }}
    </InlineMessage>

    <UsersTable v-if="users" class="u-mt" :users="users" :on-activate="handleActivateClick" :loading="loading" />
  </main>
</template>
