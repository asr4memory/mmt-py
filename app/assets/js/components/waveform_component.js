import formatTimecode from "../helpers/format_timecode";

export default {
    components: {},
    name: "WaveformComponent",
    props: {
        transcriptId: Number,
        uploadedFileId: Number,
        activeSegmentIdx: Number,
        mediaElement: HTMLMediaElement,
    },
    data() {
        return {
            transcriptData: null,
            waveform: null,
        };
    },
    watch: {
        activeSegmentIdx(newValue, oldValue) {
            this.doWaveFormStuff();
        },
    },
    computed: {},
    methods: {
        async prepareWaveForm() {
            [this.waveform, this.transcriptData] = await Promise.all([
                d3.json(`/uploaded-files/${this.uploadedFileId}/waveform/`),
                d3.json(`/transcripts/${this.transcriptId}/json/`),
            ]);
        },
        async doWaveFormStuff() {
            const mediaElement = this.mediaElement;

            const activeSegment =
                this.transcriptData.segments[this.activeSegmentIdx];

            const start = activeSegment.start;
            const end = activeSegment.end;
            const words = activeSegment.words;

            const samplingRate = this.waveform.waveform_sampling_rate;
            const wf = this.waveform.waveform;

            const mappedWf = wf.map((value, index) => ({
                i: index,
                v: value,
            }));

            const window = mappedWf.slice(
                Math.floor(start * samplingRate),
                Math.floor(end * samplingRate),
            );

            // Declare the chart dimensions and margins.
            const width = 1008;
            const height = 200;
            const marginTop = 20;
            const marginRight = 0;
            const marginBottom = 30;
            const marginLeft = 0;

            const xScaleWaveform = d3
                .scaleLinear()
                .domain([0, window.length - 1])
                .range([marginLeft, width - marginRight]);

            // Declare the x (horizontal position) scale.
            const xScale = d3
                .scaleLinear()
                .domain([start, end])
                .range([marginLeft, width - marginRight]);

            const yScale = d3
                .scaleLinear()
                .domain([0, this.waveform.waveform_max])
                .range([0, 100]);

            const xAxis = d3
                .axisBottom(xScale)
                .tickFormat((d) => formatTimecode(d));

            // This is simpler, but not efficient.
            d3.select("#waveform").selectAll("svg").remove();

            const svg = d3
                .select("#waveform")
                .append("svg")
                .attr("width", width)
                .attr("height", height);

            /* Progress line */
            svg.append("line")
                .attr("id", "progress-line")
                .attr("x1", xScale(mediaElement?.currentTime) - xScale(0))
                .attr("x2", xScale(mediaElement?.currentTime) - xScale(0))
                .attr("y1", 0)
                .attr("y2", 200)
                .attr("stroke", "red")
                .attr("opacity", 1);

            svg.append("g")
                .attr("transform", `translate(0,${height - marginBottom})`)
                .call(xAxis);

            /* Waveform */
            if (this.waveform) {
                svg.selectAll(".waveform-line")
                    .data(window, (d) => d.i)
                    .join("line")
                    .classed("waveform-line", true)
                    .attr("x1", (d, i) => xScaleWaveform(i))
                    .attr("x2", (d, i) => xScaleWaveform(i))
                    .attr("y1", (d) => -1 * yScale(d.v) + 100)
                    .attr("y2", (d) => yScale(d.v) + 100)
                    .attr("stroke", "darkblue");
            }

            /* Words */

            const drag = d3.drag().on("drag", handleDrag);
            const drag2 = d3.drag().on("drag", handleDrag2);
            const drag3 = d3.drag().on("drag", handleDrag3);

            function handleDrag(e) {
                const delta = e.dx;
                const newStart = xScale.invert(xScale(e.subject.start) + delta);
                const newEnd = xScale.invert(xScale(e.subject.end) + delta);
                e.subject.start = newStart;
                e.subject.end = newEnd;
                update();
            }

            function handleDrag2(e) {
                const delta = e.dx;
                const newStart = xScale.invert(xScale(e.subject.start) + delta);
                e.subject.start = newStart;
                update();
            }

            function handleDrag3(e) {
                const delta = e.dx;
                const newEnd = xScale.invert(xScale(e.subject.end) + delta);
                e.subject.end = newEnd;
                update();
            }

            const WORD_Y_OFFSET = 80;
            const WORD_HEIGHT = 40;

            function update() {
                if (words) {
                    svg.selectAll(".waveform__word")
                        .data(words)
                        .join("rect")
                        .classed("waveform__word", true)
                        .classed(
                            "waveform__word--active",
                            (d) =>
                                mediaElement.currentTime > d.start &&
                                mediaElement.currentTime < d.end,
                        )
                        .attr("x", (d) => xScale(d.start))
                        .attr("y", WORD_Y_OFFSET)
                        .attr("width", (d) => xScale(d.end) - xScale(d.start))
                        .attr("height", WORD_HEIGHT)
                        .attr("tabindex", 0)
                        .style("cursor", "move")
                        .on("dblclick", function (e) {
                            const startTime = e.target.__data__.start;
                            mediaElement.currentTime = startTime;
                            mediaElement.play();
                        })
                        .append("title")
                        .text(
                            (d) =>
                                `${formatTimecode(d.start)}–${formatTimecode(d.end)}`,
                        );

                    svg.selectAll(".waveform__word-text")
                        .data(words)
                        .join("text")
                        .classed("waveform__word-text", true)
                        .attr("x", (d) =>
                            xScale(d.start + (d.end - d.start) / 2),
                        )
                        .attr("y", WORD_Y_OFFSET + WORD_HEIGHT / 2 + 3)
                        .attr("font-size", "12px")
                        .text((d) => d.word)
                        .style("cursor", "move")
                        .style("text-anchor", "middle");

                    svg.selectAll(".waveform__word-start")
                        .data(words)
                        .join("rect")
                        .classed("waveform__word-start", true)
                        .attr("x", (d) => xScale(d.start))
                        .attr("y", WORD_Y_OFFSET)
                        .attr("width", 5)
                        .attr("height", WORD_HEIGHT)
                        .attr("fill", "black")
                        .attr("opacity", 0.9)
                        .style("cursor", "col-resize")
                        .append("title")
                        .text((d) => formatTimecode(d.start));

                    svg.selectAll(".waveform__word-end")
                        .data(words)
                        .join("rect")
                        .classed("waveform__word-end", true)
                        .attr("x", (d) => xScale(d.end) - 5)
                        .attr("y", WORD_Y_OFFSET)
                        .attr("width", 5)
                        .attr("height", WORD_HEIGHT)
                        .attr("fill", "black")
                        .attr("opacity", 0.9)
                        .style("cursor", "col-resize")
                        .append("title")
                        .text((d) => formatTimecode(d.end));
                }
            }

            function initDrag() {
                svg.selectAll(".waveform__word").call(drag);
                svg.selectAll(".waveform__word-start").call(drag2);
                svg.selectAll(".waveform__word-end").call(drag3);
            }

            update();
            initDrag();

            /* Invisible click area */
            svg.append("rect")
                .attr("x", 0)
                .attr("y", 150)
                .attr("width", width)
                .attr("height", height - 150)
                .attr("fill", "transparent")
                .style("cursor", "crosshair")
                .on("click", (event) => {
                    const [mouseX] = d3.pointer(event);
                    const seconds = xScale.invert(mouseX);
                    mediaElement.currentTime = seconds;
                    mediaElement.play();
                });

            mediaElement.addEventListener("timeupdate", handleTimeUpdate);

            function handleTimeUpdate(event) {
                // Update progress line.
                d3.select("#progress-line")
                    .attr("x1", xScale(mediaElement.currentTime))
                    .attr("x2", xScale(mediaElement.currentTime));

                // Update word boxes
                update();
            }
        },
    },
    async mounted() {
        await this.prepareWaveForm();
        this.doWaveFormStuff();
    },
    template: `
    <div id="waveform" ref="waveform"></div>
    `,
};
