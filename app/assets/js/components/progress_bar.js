export default {
    props: ["id", "percentage", "color", "label"],
    computed: {
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
        :style="'--bar-color: ' + color + ';'"
        :value="percentage"
        max="100"
      >
      </progress>
    </div>
  `,
};
