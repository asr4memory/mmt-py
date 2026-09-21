import { computed, ref } from "vue";

// The transcript label. It is edited in the document bar and written by the
// same save as the content, so it carries its own unsaved state.
export function useLabel() {
    const label = ref("");
    // The label as the server has it. A label that differs from it is unsaved.
    const savedLabel = ref("");

    const labelIsDirty = computed(() => label.value !== savedLabel.value);

    function loadLabel(value: string) {
        label.value = value;
        savedLabel.value = value;
    }

    function markLabelSaved() {
        savedLabel.value = label.value;
    }

    function discardLabel() {
        label.value = savedLabel.value;
    }

    return { label, labelIsDirty, loadLabel, markLabelSaved, discardLabel };
}
