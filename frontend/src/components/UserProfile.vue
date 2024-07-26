<script setup lang="ts">
import type { UserInfo } from '@/types'

defineProps<{
  user: UserInfo
}>()
</script>

<template>
  <dl>
    <dt>{{ $t('components.UserProfile.username') }}</dt>
    <dd>{{ user.username }}</dd>
    <dt>{{ $t('components.UserProfile.email') }}</dt>
    <dd>{{ user.email }}</dd>
    <dt>{{ $t('components.UserProfile.locale') }}</dt>
    <dd>{{ user.locale }}</dd>
  </dl>
</template>
