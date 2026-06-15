import formatTimecode from "../shared/format_timecode";
import deformatTimecode from "../shared/deformat_timecode";

export default {
    name: "TimecodeInput",
    props: {
        seconds: Number,
    },
    emits: ["submit"],
    data() {
        return {
            editMode: false,
        };
    },
    computed: {
        formattedTimecode() {
            return formatTimecode(this.seconds);
        },
    },
    methods: {
        handleFocus(event) {
            this.editMode = true;
            const span = event.target;
            this.$nextTick(() => {
                const input = span.firstElementChild;
                input?.focus();
            });
        },
        handleChange(event) {
            if (event.target.checkValidity()) {
                const newSeconds = deformatTimecode(event.target.value);
                if (newSeconds !== this.seconds) {
                    this.$emit("submit", newSeconds);
                }
            }
            this.$nextTick(() => {
                this.editMode = false;
            });
        },
    },
    template: `
    <span class="timecode-input"
        :tabindex="editMode ? -1 : 0"
        @focus="handleFocus">
        {{formattedTimecode}}
        <input v-if="editMode" class="timecode-input__input"
            tabindex="0"
            required
            pattern="[0-9]{1,2}:[0-5][0-9]:[0-5][0-9]\.[0-9]{3}"
            placeholder="#:##:##.###"
            :value="formattedTimecode"
            @blur="handleChange"
            @keyup.enter="handleChange" />
    </span>
    `,
};
