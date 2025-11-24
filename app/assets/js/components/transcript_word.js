export default {
    components: {},
    name: 'TranscriptWord',
    props: ['index', 'start', 'end', 'word', 'speaker', 'score'],
    data() {
        return {};
    },
    computed: {
        backgroundColor() {
            return `hsl(208 71% 77% / ${this.score})`;
        },
    },
    template: `
    <span class="word"
        :style="{'background-color': backgroundColor }"
        :title="score">
        {{word}}
    </span>
    `,
};
