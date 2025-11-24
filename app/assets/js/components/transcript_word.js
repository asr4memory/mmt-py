export default {
    components: {},
    name: 'TranscriptWord',
    props: ['index', 'start', 'end', 'word', 'speaker', 'score'],
    data() {
        return {};
    },
    template: `
    <span class="word">
        {{word}}
    </span>
    `,
};
