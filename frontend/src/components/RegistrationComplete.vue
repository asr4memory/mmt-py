<script setup lang="ts">
defineProps({
  username: String
})
</script>

<template>
  <h2>{{ $t('components.RegistrationComplete.title') }}</h2>
  <p class="u-ll u-mt">
    {{ $t('components.RegistrationComplete.message', { username: username }) }}
  </p>
  <p class="u-ll u-mt">
    {{ $t('components.RegistrationComplete.activation') }}
  </p>
</template>
