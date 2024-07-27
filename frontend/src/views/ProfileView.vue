<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import UserProfile from '@/components/UserProfile.vue'
import type { UserInfo } from '@/types'

const store = useAuthStore()
</script>

<template>
  <main class="container u-mt u-mb-2">
    <h2>{{ $t('views.ProfileView.title') }}</h2>

    <UserProfile v-if="store.user" />
  </main>
</template>
