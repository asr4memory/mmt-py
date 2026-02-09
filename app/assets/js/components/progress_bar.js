export default {
    props: ["id", "type", "percentage"],
    computed: {
        label() {
            if (this.type === "upload") {
                return this.$t("upload");
            } else if (this.type === "checksum") {
                return this.$t("checksum");
            }
        },
        percentageStr() {
            return this.percentage.toLocaleString(this.$i18n.locale, {
                maximumFractionDigits: 1,
            });
        },
    },
    template: `
    <div class="progress-bar">
        <label :for="id" class="progress-bar__label">
            {{label}}: {{percentageStr}}&thinsp;%
        </label>
        <progress
            :id="id"
            class="progress-bar__bar"
            :class="{ 'progress-bar__bar--upload': type === 'upload', 'progress-bar__bar--checksum': type === 'checksum' }"
            :value="percentage"
        max="100"
        >
        </progress>
    </div>
    `,
};
