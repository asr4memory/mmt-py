<script setup lang="ts">
import { storeToRefs } from "pinia";

import Message from "./message.vue";
import { useMessagesStore } from "./messages_store";

// Same markup as the Django `_messages.html` template, styled by messages.css.
const store = useMessagesStore();
const { messages } = storeToRefs(store);
</script>

<template>
    <div
        v-if="messages.length > 0"
        class="message-stack"
        data-placement="top"
        role="region"
        aria-label="Messages"
    >
        <Message
            v-for="message in messages"
            :key="message.id"
            :level="message.level"
            :text="message.text"
            @dismiss="store.remove(message.id)"
        />
    </div>
</template>
