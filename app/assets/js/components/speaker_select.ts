import { defineComponent } from "vue";

export default defineComponent({
    name: "SpeakerSelect",
    props: {
        modelValue: String,
        speakers: {
            type: Array as () => { name: string; color: string }[],
            required: true,
        },
    },
    emits: ["update:modelValue"],
    setup(props, { emit }) {
        function handleChange(event: Event) {
            emit(
                "update:modelValue",
                (event.target as HTMLSelectElement).value,
            );
        }

        return { handleChange };
    },
    template: `
    <select :value="modelValue" @change="handleChange">
        <option v-for="speaker in speakers" :key="speaker.name" :value="speaker.name">
            {{speaker.name}}
        </option>
    </select>
    `,
});
