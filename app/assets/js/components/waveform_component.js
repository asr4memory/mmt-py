import { mapState, mapActions } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import formatTimecode from "../helpers/format_timecode";
import seekAndPlay from "../helpers/seek_and_play";
import playSegment from "../helpers/play_segment";

const SEEK_TIME_WAVEFORM = 0.5;
const HEIGHT_WAVEFORM = 120;
const MIDDLE_OF_WAVEFORM = HEIGHT_WAVEFORM / 2;
const HEIGHT_AXIS = 30;
const HEIGHT_TOTAL = HEIGHT_WAVEFORM + HEIGHT_AXIS;
const HORIZONTAL_PIXELS_PER_SECOND = 250;
const WORD_HEIGHT = 36;
const WORD_Y_OFFSET = HEIGHT_WAVEFORM / 2 - WORD_HEIGHT / 2;

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
            waveform: [],
            samplingRate: 0,
            maximumAmplitude: 0,
        };
    },
    async mounted() {
        await this.prepareWaveForm();
        this.doWaveFormStuff();
    },
    watch: {
        activeSegmentIdx(newValue, oldValue) {
            this.doWaveFormStuff();
        },
    },
    computed: {
        ...mapState(useTranscriptStore, ["segments"]),
        formattedID() {
            return String(this.activeSegment.id).padStart(3, "0");
        },
        activeSegment() {
            if (this.segments) {
                return this.segments[this.activeSegmentIdx];
            }
        },
        duration() {
            return this.activeSegment.end - this.activeSegment.start;
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
        formattedDuration() {
            if (this.activeSegment) {
                return (
                    this.activeSegment.end - this.activeSegment.start
                ).toFixed(2);
            }
        },
        waveformWithIDs() {
            return this.waveform.map((value, index) => ({
                i: index,
                v: value,
            }));
        },
        window() {
            return this.waveformWithIDs.slice(
                Math.floor(this.activeSegment.start * this.samplingRate),
                Math.floor(this.activeSegment.end * this.samplingRate),
            );
        },
        waveformWidth() {
            return this.duration * HORIZONTAL_PIXELS_PER_SECOND;
        },
    },
    methods: {
        ...mapActions(useTranscriptStore, ["updateTimecode"]),
        async prepareWaveForm() {
            try {
                const waveformData = await d3.json(
                    `/uploaded-files/${this.uploadedFileId}/waveform/`,
                );
                this.waveform = waveformData.waveform;
                this.samplingRate = waveformData.waveform_sampling_rate;
                this.maximumAmplitude = waveformData.waveform_max;
            } catch {
                this.waveform = null;
                this.samplingRate = null;
                this.maximumAmplitude = null;
            }
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
            // Scales
            const xScaleWaveform = d3
                .scaleLinear()
                .domain([0, this.window.length - 1])
                .range([0, this.waveformWidth]);

            const xScale = d3
                .scaleLinear()
                .domain([this.activeSegment.start, this.activeSegment.end])
                .range([0, this.waveformWidth]);

            const yScale = d3
                .scaleLinear()
                .domain([0, this.maximumAmplitude])
                .range([0, 100]);

            // Remove and recreate SVG
            d3.select("#waveform").selectAll("svg").remove();
            const svg = d3
                .select("#waveform")
                .append("svg")
                .attr("width", this.waveformWidth)
                .attr("height", HEIGHT_TOTAL);

            // Add everything.
            this.addAxis(svg, xScale);
            this.addCurrentTimeMarker(svg, xScale);
            this.addWaveform(svg, xScaleWaveform, yScale);
            this.addInvisibleClickArea(svg, xScale);
            this.addWordRects(svg, xScale);
            this.addDragHandlers(svg, xScale);

            const handleTimeUpdate = (event) => {
                // Progress marker and word rects need to be updated when
                // currentTime changes.
                this.addCurrentTimeMarker(svg, xScale);
                this.addWordRects(svg, xScale);
            };

            // Does not have a removeEventListener yet.
            this.mediaElement.addEventListener("timeupdate", handleTimeUpdate);
        },
        addAxis(svg, xScale) {
            const xAxis = d3
                .axisBottom(xScale)
                .tickFormat((d) => formatTimecode(d));

            svg.append("g")
                .attr("transform", `translate(0,${HEIGHT_WAVEFORM})`)
                .call(xAxis);
        },
        addCurrentTimeMarker(svg, xScale) {
            svg.selectAll(".waveform__progress")
                .data([this.mediaElement.currentTime])
                .join("line")
                .classed("waveform__progress", true)
                .attr("x1", (d) => xScale(d))
                .attr("x2", (d) => xScale(d))
                .attr("y1", 0)
                .attr("y2", HEIGHT_WAVEFORM)
                .attr("stroke", "red");
        },
        addWaveform(svg, xScale, yScale) {
            svg.selectAll(".waveform-line")
                .data(this.window, (d) => d.i)
                .join("line")
                .classed("waveform-line", true)
                .attr("x1", (d, i) => xScale(i))
                .attr("x2", (d, i) => xScale(i))
                .attr("y1", (d) => MIDDLE_OF_WAVEFORM - yScale(d.v))
                .attr("y2", (d) => MIDDLE_OF_WAVEFORM + yScale(d.v))
                .attr("stroke", "darkblue");
        },
        addInvisibleClickArea(svg, xScale) {
            svg.append("rect")
                .attr("x", 0)
                .attr("y", HEIGHT_WAVEFORM)
                .attr("width", this.waveformWidth)
                .attr("height", HEIGHT_AXIS)
                .attr("fill", "transparent")
                .style("cursor", "crosshair")
                .on("click", (event) => {
                    const [mouseX] = d3.pointer(event);
                    const seconds = xScale.invert(mouseX);
                    seekAndPlay(this.mediaElement, seconds);

                    if (specialTimeUpdateHandler) {
                        this.mediaElement.removeEventListener(
                            "timeupdate",
                            specialTimeUpdateHandler,
                        );
                        specialTimeUpdateHandler = null;
                    }
                });
        },
        addWordRects(svg, xScale) {
            const wordRects = svg
                .selectAll(".waveform__word")
                .data(this.activeSegment.words)
                .join("rect")
                .classed("waveform__word", true)
                .classed(
                    "waveform__word--active",
                    (d) =>
                        this.mediaElement.currentTime > d.start &&
                        this.mediaElement.currentTime < d.end,
                )
                .attr("x", (d) => xScale(d.start))
                .attr("y", WORD_Y_OFFSET)
                .attr("width", (d) => xScale(d.end) - xScale(d.start))
                .attr("height", WORD_HEIGHT)
                .attr("tabindex", 0)
                .style("cursor", "move")
                .on("dblclick", (e) => {
                    const startTime = e.target.__data__.start;
                    const endTime = e.target.__data__.end;
                    playSegment(this.mediaElement, startTime, endTime);
                });

            wordRects
                .selectAll("title")
                .data((d) => [d])
                .join("title")
                .text(
                    (d) =>
                        `${formatTimecode(d.start)}–${formatTimecode(d.end)}`,
                );

            svg.selectAll(".waveform__word-text")
                .data(this.activeSegment.words)
                .join("text")
                .classed("waveform__word-text", true)
                .attr("x", (d) => xScale(d.start + (d.end - d.start) / 2))
                .attr("y", WORD_Y_OFFSET + WORD_HEIGHT / 2 + 3)
                .attr("font-size", "14px")
                .text((d) => d.word)
                .style("cursor", "move")
                .style("text-anchor", "middle");

            const startHandleRects = svg
                .selectAll(".waveform__word-start")
                .data(this.activeSegment.words)
                .join("rect")
                .classed("waveform__word-start", true)
                .attr("x", (d) => xScale(d.start))
                .attr("y", WORD_Y_OFFSET)
                .attr("width", 5)
                .attr("height", WORD_HEIGHT)
                .attr("fill", "black")
                .attr("opacity", 0.9)
                .style("cursor", "col-resize");

            startHandleRects
                .selectAll("title")
                .data((d) => [d])
                .join("title")
                .text((d) => formatTimecode(d.start));

            const endHandleRects = svg
                .selectAll(".waveform__word-end")
                .data(this.activeSegment.words)
                .join("rect")
                .classed("waveform__word-end", true)
                .attr("x", (d) => xScale(d.end) - 5)
                .attr("y", WORD_Y_OFFSET)
                .attr("width", 5)
                .attr("height", WORD_HEIGHT)
                .attr("fill", "black")
                .attr("opacity", 0.9)
                .style("cursor", "col-resize");

            endHandleRects
                .selectAll("title")
                .data((d) => [d])
                .join("title")
                .text((d) => formatTimecode(d.end));
        },
        addDragHandlers(svg, xScale) {
            const handleWordDrag = (e) => {
                const delta = e.dx;
                const newStart = xScale.invert(xScale(e.subject.start) + delta);
                const newEnd = xScale.invert(xScale(e.subject.end) + delta);
                this.updateTimecode(
                    this.activeSegment.id,
                    e.subject.id,
                    newStart,
                    newEnd,
                );
                this.addWordRects(svg, xScale);
            };

            const handleStartDrag = (e) => {
                const delta = e.dx;
                const newStart = xScale.invert(xScale(e.subject.start) + delta);
                this.updateTimecode(
                    this.activeSegment.id,
                    e.subject.id,
                    newStart,
                    e.subject.end,
                );
                this.addWordRects(svg, xScale);
            };

            const handleEndDrag = (e) => {
                const delta = e.dx;
                const newEnd = xScale.invert(xScale(e.subject.end) + delta);
                this.updateTimecode(
                    this.activeSegment.id,
                    e.subject.id,
                    e.subject.start,
                    newEnd,
                );
                this.addWordRects(svg, xScale);
            };

            const drag = d3.drag().on("drag", handleWordDrag);
            const drag2 = d3.drag().on("drag", handleStartDrag);
            const drag3 = d3.drag().on("drag", handleEndDrag);

            svg.selectAll(".waveform__word").call(drag);
            svg.selectAll(".waveform__word-start").call(drag2);
            svg.selectAll(".waveform__word-end").call(drag3);
        },
    },
    template: `
    <div class="waveform">
        <header class="waveform__header">
            <span>#{{formattedID}} {{startTimecode}}–{{endTimecode}} ({{formattedDuration}}s)</span>
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
