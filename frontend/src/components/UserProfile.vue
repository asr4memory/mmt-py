<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const store = useAuthStore()
const LOCALES = ['de', 'en']

function handleChange(event: Event) {
  store.setLocale(event.target.value)
}
</script>

<template>
  <dl>
    <dt>{{ $t('components.UserProfile.username') }}</dt>
    <dd>{{ store.user.username }}</dd>
    <dt>{{ $t('components.UserProfile.email') }}</dt>
    <dd>{{ store.user.email }}</dd>
    <dt>{{ $t('components.UserProfile.admin') }}</dt>
    <dd>{{ $t(`general.booleans.${store.user.admin}`) }}</dd>
    <dt>{{ $t('components.UserProfile.can_upload') }}</dt>
    <dd>{{ $t(`general.booleans.${store.user.can_upload}`) }}</dd>
    <dt>{{ $t('components.UserProfile.locale') }}</dt>
    <dd>
      <form class="u-flex u-gap-1/2">
        <span v-for="loc in LOCALES" :key="loc">
          <input
            type="radio"
            :id="loc"
            :value="loc"
            v-model="store.user.locale"
            @click="handleChange"
          />
          <label :for="loc" class="u-ml-1/4">
            {{ $t(`general.locales.${loc}`) }}
          </label>
        </span>
      </form>
    </dd>
  </dl>
</template>
