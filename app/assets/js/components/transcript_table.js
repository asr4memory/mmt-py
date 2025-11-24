export default {
    components: {},
    props: ['id'],
    data() {
        return {};
    },
    template: `
    <p>
        Transcript no. {{id}}<br>
        {{ $t('processing') }}
    </p>
    `,
};
