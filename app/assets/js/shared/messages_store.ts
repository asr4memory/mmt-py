import { defineStore } from "pinia";
import { ref } from "vue";

export type MessageLevel = "success" | "info" | "warning" | "error";

export interface Message {
    id: number;
    level: MessageLevel;
    text: string;
}

// Messages shown in the message stack, the JS counterpart of the Django
// messages framework.
export const useMessagesStore = defineStore("messages", () => {
    const messages = ref<Message[]>([]);
    let nextId = 1;

    function add(level: MessageLevel, text: string): number {
        const id = nextId++;
        messages.value.push({ id, level, text });
        return id;
    }

    function remove(id: number) {
        messages.value = messages.value.filter((message) => message.id !== id);
    }

    return { messages, add, remove };
});
