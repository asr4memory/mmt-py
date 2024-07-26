<script setup lang="ts">
import { ref } from 'vue'
import type { Ref } from 'vue'

import { fetchWrapper } from '@/helpers/fetch-wrapper'
import RegistrationForm from '@/components/RegistrationForm.vue'
import RegistrationComplete from '@/components/RegistrationComplete.vue'
import type { UserInfo } from '@/types'

const baseUrl = `${import.meta.env.VITE_API_URL}/auth`

const loading = ref(false)
const registeredUser: Ref<UserInfo | null> = ref(null)
const error: Ref<string | null> = ref(null)

async function handleSubmit(event: Event): Promise<void> {
  event.preventDefault()
  const form = event?.target as HTMLFormElement
  const elements = form.elements

  const usernameInput = elements[0] as HTMLInputElement
  const emailInput = elements[1] as HTMLInputElement
  const passwordInput1 = elements[2] as HTMLInputElement
  const passwordInput2 = elements[3] as HTMLInputElement
  const username = usernameInput.value
  const email = emailInput.value
  const password1 = passwordInput1.value
  const password2 = passwordInput2.value

  error.value = null
  if (password1 !== password2) {
    error.value = 'password_mismatch'
  } else {
    loading.value = true
    const result = await fetchWrapper
      .post(`${baseUrl}/register`, { username, email, password: password1 })
      .catch((err) => {
        error.value = err
        console.log(err)
        return null
      })
    loading.value = false
    if (result) {
      registeredUser.value = result
    }
  }
}
</script>

<template>
  <main class="container u-mt u-mb-2">
    <RegistrationComplete v-if="registeredUser" :username="registeredUser.username" />
    <RegistrationForm v-else :error="error" :loading="loading" :on-submit="handleSubmit" />
  </main>
</template>
