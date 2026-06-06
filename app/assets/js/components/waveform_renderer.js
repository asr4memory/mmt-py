import { axisBottom, drag, pointer, scaleLinear, select } from "d3";

import formatTimecode from "../helpers/format_timecode";
import seekAndPlay from "../helpers/seek_and_play";
import playSegment from "../helpers/play_segment";

const HEIGHT_WAVEFORM = 120;
const MIDDLE_OF_WAVEFORM = HEIGHT_WAVEFORM / 2;
const HEIGHT_AXIS = 30;
const HEIGHT_TOTAL = HEIGHT_WAVEFORM + HEIGHT_AXIS;
const WORD_HEIGHT = 36;
const WORD_Y_OFFSET = HEIGHT_WAVEFORM / 2 - WORD_HEIGHT / 2;

export const HORIZONTAL_PIXELS_PER_SECOND = 250;

export class WaveformRenderer {
    #svg = null;
    #xScale = null;

    constructor(containerSelector, mediaElement, { getSegment, onUpdateTimecode }) {
        this.containerSelector = containerSelector;
        this.mediaElement = mediaElement;
        this.getSegment = getSegment;
        this.onUpdateTimecode = onUpdateTimecode;
    }

    render(visibleSamples, maximumAmplitude, waveformWidth) {
        const segment = this.getSegment();

        const xScaleWaveform = scaleLinear()
            .domain([0, visibleSamples.length - 1])
            .range([0, waveformWidth]);

        const xScale = scaleLinear()
            .domain([segment.start, segment.end])
            .range([0, waveformWidth]);

        const yScale = scaleLinear()
            .domain([0, maximumAmplitude])
            .range([0, 100]);

        select(this.containerSelector).selectAll("svg").remove();
        const svg = select(this.containerSelector)
            .append("svg")
            .attr("width", waveformWidth)
            .attr("height", HEIGHT_TOTAL);

        this.#svg = svg;
        this.#xScale = xScale;

        this.#addAxis(svg, xScale);
        this.#addCurrentTimeMarker(svg, xScale);
        this.#addWaveform(svg, xScaleWaveform, yScale, visibleSamples);
        this.#addInvisibleClickArea(svg, xScale, waveformWidth);
        this.#addWordRects(svg, xScale);
        this.#addDragHandlers(svg, xScale);
    }

    updateTime() {
        if (!this.#svg || !this.#xScale) return;
        this.#addCurrentTimeMarker(this.#svg, this.#xScale);
        this.#updateActiveWord(this.#svg);
    }

    destroy() {
        select(this.containerSelector).selectAll("svg").remove();
        this.#svg = null;
        this.#xScale = null;
    }

    #addAxis(svg, xScale) {
        const xAxis = axisBottom(xScale).tickFormat((d) => formatTimecode(d));
        svg.append("g")
            .attr("transform", `translate(0,${HEIGHT_WAVEFORM})`)
            .call(xAxis);
    }

    #addCurrentTimeMarker(svg, xScale) {
        svg.selectAll(".waveform__progress")
            .data([this.mediaElement.currentTime])
            .join("line")
            .classed("waveform__progress", true)
            .attr("x1", (d) => xScale(d))
            .attr("x2", (d) => xScale(d))
            .attr("y1", 0)
            .attr("y2", HEIGHT_WAVEFORM)
            .attr("stroke", "red");
    }

    #addWaveform(svg, xScale, yScale, visibleSamples) {
        svg.selectAll(".waveform-line")
            .data(visibleSamples, (d) => d.i)
            .join("line")
            .classed("waveform-line", true)
            .attr("x1", (d, i) => xScale(i))
            .attr("x2", (d, i) => xScale(i))
            .attr("y1", (d) => MIDDLE_OF_WAVEFORM - yScale(d.v))
            .attr("y2", (d) => MIDDLE_OF_WAVEFORM + yScale(d.v))
            .attr("stroke", "darkblue");
    }

    #addInvisibleClickArea(svg, xScale, waveformWidth) {
        svg.append("rect")
            .attr("x", 0)
            .attr("y", HEIGHT_WAVEFORM)
            .attr("width", waveformWidth)
            .attr("height", HEIGHT_AXIS)
            .attr("fill", "transparent")
            .style("cursor", "crosshair")
            .on("click", (event) => {
                const [mouseX] = pointer(event);
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
    }

    #addWordRects(svg, xScale) {
        const segment = this.getSegment();

        const wordRects = svg
            .selectAll(".waveform__word")
            .data(segment.words)
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
                playSegment(this.mediaElement, e.target.__data__.start, e.target.__data__.end);
            });

        wordRects
            .selectAll("title")
            .data((d) => [d])
            .join("title")
            .text((d) => `${formatTimecode(d.start)}–${formatTimecode(d.end)}`);

        svg.selectAll(".waveform__word-text")
            .data(segment.words)
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
            .data(segment.words)
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
            .data(segment.words)
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
    }

    #updateActiveWord(svg) {
        svg.selectAll(".waveform__word").classed(
            "waveform__word--active",
            (d) =>
                this.mediaElement.currentTime > d.start &&
                this.mediaElement.currentTime < d.end,
        );
    }

    #addDragHandlers(svg, xScale) {
        const secondsDelta = (e) => e.dx / HORIZONTAL_PIXELS_PER_SECOND;

        const handleWordDrag = (e) => {
            const d = secondsDelta(e);
            const segment = this.getSegment();
            this.onUpdateTimecode(
                segment.id,
                e.subject.id,
                e.subject.start + d,
                e.subject.end + d,
            );
            this.#addWordRects(svg, xScale);
        };

        const handleStartDrag = (e) => {
            const segment = this.getSegment();
            this.onUpdateTimecode(
                segment.id,
                e.subject.id,
                e.subject.start + secondsDelta(e),
                e.subject.end,
            );
            this.#addWordRects(svg, xScale);
        };

        const handleEndDrag = (e) => {
            const segment = this.getSegment();
            this.onUpdateTimecode(
                segment.id,
                e.subject.id,
                e.subject.start,
                e.subject.end + secondsDelta(e),
            );
            this.#addWordRects(svg, xScale);
        };

        const wordDrag = drag().on("drag", handleWordDrag);
        const startHandleDrag = drag().on("drag", handleStartDrag);
        const endHandleDrag = drag().on("drag", handleEndDrag);

        svg.selectAll(".waveform__word").call(wordDrag);
        svg.selectAll(".waveform__word-start").call(startHandleDrag);
        svg.selectAll(".waveform__word-end").call(endHandleDrag);
    }
}
