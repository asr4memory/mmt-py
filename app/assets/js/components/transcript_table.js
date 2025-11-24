export default {
    components: {},
    props: ['id', 'projectId'],
    data() {
        return {};
    },
    async mounted() {
        const path = `/projects/${this.projectId}/transcripts/${this.id}/json/`
        const result = await fetch(path);
        const json = await result.json();
        console.log(json);
    },
    template: `
    <p>
        Transcript no. {{id}}<br>
        {{ $t('processing') }}
    </p>
    `,
};
