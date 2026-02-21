import { mapState, mapActions } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import formatTimecode from "../helpers/format_timecode";
import seekAndPlay from "../helpers/seek_and_play";

const SEEK_TIME_WAVEFORM = 0.5;

let specialTimeUpdateHandler = null;

export default {
    components: {},
    name: "WaveformComponent",
    props: {
        transcriptId: Number,
        uploadedFileId: Number,
        activeSegmentIdx: Number,
        mediaElement: HTMLMediaElement,
    },
    emits: ["close-panel"],
    data() {
        return {
            waveform: null,
        };
    },
    watch: {
        activeSegmentIdx(newValue, oldValue) {
            this.doWaveFormStuff();
        },
    },
    computed: {
        ...mapState(useTranscriptStore, ["segments"]),
        formattedID() {
            return String(this.activeSegmentIdx).padStart(3, "0");
        },
        activeSegment() {
            if (this.segments) {
                return this.segments[this.activeSegmentIdx];
            }
        },
        startTimecode() {
            if (this.activeSegment) {
                return formatTimecode(this.activeSegment.start);
            }
        },
        endTimecode() {
            if (this.activeSegment) {
                return formatTimecode(this.activeSegment.end);
            }
        },
        duration() {
            if (this.activeSegment) {
                return (
                    this.activeSegment.end - this.activeSegment.start
                ).toFixed(2);
            }
        },
    },
    methods: {
        ...mapActions(useTranscriptStore, ["updateTimecode"]),
        async prepareWaveForm() {
            this.waveform = await d3.json(`/uploaded-files/${this.uploadedFileId}/waveform/`);
        },
        clearWaitForPauseHandler() {
            if (specialTimeUpdateHandler) {
                this.mediaElement.removeEventListener(
                    "timeupdate",
                    specialTimeUpdateHandler,
                );
                specialTimeUpdateHandler = null;
            }
        },
        preventPrevent(event) {
            event.preventDefault();
        },
        handleSpaceKey(event) {
            if (this.mediaElement.paused) {
                this.mediaElement.play();
            } else {
                this.mediaElement.pause();
                this.clearWaitForPauseHandler();
            }
        },
        handleLeftKey(event) {
            event.preventDefault();
            this.mediaElement.currentTime =
                this.mediaElement.currentTime - SEEK_TIME_WAVEFORM;
        },
        handleRightKey(event) {
            event.preventDefault();
            this.mediaElement.currentTime =
                this.mediaElement.currentTime + SEEK_TIME_WAVEFORM;
        },
        async doWaveFormStuff() {
            const HEIGHT_WAVEFORM = 120;
            const MIDDLE_OF_WAVEFORM = HEIGHT_WAVEFORM / 2;
            const HEIGHT_AXIS = 30;
            const HEIGHT = HEIGHT_WAVEFORM + HEIGHT_AXIS;
            const HORIZONTAL_PIXELS_PER_SECOND = 250;

            const WORD_HEIGHT = 36;
            const WORD_Y_OFFSET = (HEIGHT_WAVEFORM / 2) - (WORD_HEIGHT / 2);


            const mediaElement = this.mediaElement;
            const activeSegment = this.segments[this.activeSegmentIdx];

            const start = activeSegment.start;
            const end = activeSegment.end;
            const segmentDuration = end - start;
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
            const width = segmentDuration * HORIZONTAL_PIXELS_PER_SECOND;
            const height = HEIGHT;
            const marginBottom = HEIGHT_AXIS;

            const xScaleWaveform = d3
                .scaleLinear()
                .domain([0, window.length - 1])
                .range([0, width]);

            // Declare the x (horizontal position) scale.
            const xScale = d3
                .scaleLinear()
                .domain([start, end])
                .range([0, width]);

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
                .attr("y2", HEIGHT_WAVEFORM)
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
                    .attr("y1", (d) => MIDDLE_OF_WAVEFORM - yScale(d.v))
                    .attr("y2", (d) => MIDDLE_OF_WAVEFORM + yScale(d.v))
                    .attr("stroke", "darkblue");
            }

            /* Words */

            const handleWordDrag = (e) => {
                const delta = e.dx;
                const newStart = xScale.invert(xScale(e.subject.start) + delta);
                const newEnd = xScale.invert(xScale(e.subject.end) + delta);
                this.updateTimecode(activeSegment.id, e.subject.id, newStart, newEnd);
                update();
            }

            const handleStartDrag = (e) => {
                const delta = e.dx;
                const newStart = xScale.invert(xScale(e.subject.start) + delta);
                this.updateTimecode(activeSegment.id, e.subject.id, newStart, e.subject.end);
                update();
            }

            const handleEndDrag = (e) => {
                const delta = e.dx;
                const newEnd = xScale.invert(xScale(e.subject.end) + delta);
                this.updateTimecode(activeSegment.id, e.subject.id, e.subject.start, newEnd);
                update();
            }

            const drag = d3.drag().on("drag", handleWordDrag);
            const drag2 = d3.drag().on("drag", handleStartDrag);
            const drag3 = d3.drag().on("drag", handleEndDrag);



            function update() {
                if (words) {
                    const wordRects = svg.selectAll(".waveform__word")
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
                            if (specialTimeUpdateHandler) {
                                mediaElement.removeEventListener(
                                    "timeupdate",
                                    specialTimeUpdateHandler,
                                );
                                specialTimeUpdateHandler = null;
                            }

                            const startTime = e.target.__data__.start;
                            const endTime = e.target.__data__.end;

                            const listener = (e) => {
                                if (mediaElement.currentTime >= endTime) {
                                    mediaElement.pause();
                                    mediaElement.currentTime = endTime;
                                    mediaElement.removeEventListener(
                                        "timeupdate",
                                        listener,
                                    );
                                }
                            };
                            specialTimeUpdateHandler = listener;

                            mediaElement.addEventListener(
                                "timeupdate",
                                listener,
                            );

                            seekAndPlay(mediaElement, startTime);
                        });

                    wordRects.selectAll("title")
                        .data(d => [d])
                        .join("title")
                        .text((d) => `${formatTimecode(d.start)}–${formatTimecode(d.end)}`);


                    svg.selectAll(".waveform__word-text")
                        .data(words)
                        .join("text")
                        .classed("waveform__word-text", true)
                        .attr("x", (d) =>
                            xScale(d.start + (d.end - d.start) / 2),
                        )
                        .attr("y", WORD_Y_OFFSET + WORD_HEIGHT / 2 + 3)
                        .attr("font-size", "14px")
                        .text((d) => d.word)
                        .style("cursor", "move")
                        .style("text-anchor", "middle");


                    const startHandleRects = svg.selectAll(".waveform__word-start")
                        .data(words)
                        .join("rect")
                        .classed("waveform__word-start", true)
                        .attr("x", (d) => xScale(d.start))
                        .attr("y", WORD_Y_OFFSET)
                        .attr("width", 5)
                        .attr("height", WORD_HEIGHT)
                        .attr("fill", "black")
                        .attr("opacity", 0.9)
                        .style("cursor", "col-resize");

                    startHandleRects.selectAll("title")
                        .data(d => [d])
                        .join("title")
                        .text((d) => formatTimecode(d.start));


                    const endHandleRects = svg.selectAll(".waveform__word-end")
                        .data(words)
                        .join("rect")
                        .classed("waveform__word-end", true)
                        .attr("x", (d) => xScale(d.end) - 5)
                        .attr("y", WORD_Y_OFFSET)
                        .attr("width", 5)
                        .attr("height", WORD_HEIGHT)
                        .attr("fill", "black")
                        .attr("opacity", 0.9)
                        .style("cursor", "col-resize");

                    endHandleRects.selectAll("title")
                        .data(d => [d])
                        .join("title")
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
                .attr("y", HEIGHT_WAVEFORM)
                .attr("width", width)
                .attr("height", HEIGHT_AXIS)
                .attr("fill", "transparent")
                .style("cursor", "crosshair")
                .on("click", (event) => {
                    const [mouseX] = d3.pointer(event);
                    const seconds = xScale.invert(mouseX);
                    seekAndPlay(mediaElement, seconds);

                    if (specialTimeUpdateHandler) {
                        mediaElement.removeEventListener(
                            "timeupdate",
                            specialTimeUpdateHandler,
                        );
                        specialTimeUpdateHandler = null;
                    }
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
    <div class="waveform">
        <header class="waveform__header">
            <span>#{{formattedID}} {{startTimecode}}–{{endTimecode}} ({{duration}}s)</span>
            <button type="button" class="waveform__close"
                @click="$emit('closePanel')">&times;</button>
        </header>
        <!-- Set tabindex so that div can be focused and receive key events. -->
        <div id="waveform"
            class="waveform__container"
            tabindex="0"
            @keydown.space="preventPrevent"
            @keyup.space="handleSpaceKey"
            @keyup.left="handleLeftKey"
            @keyup.right="handleRightKey"></div>
    </div>
    `,
};
