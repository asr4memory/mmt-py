import type { DragBehavior, D3DragEvent, ScaleLinear } from "d3";
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

export interface TranscriptWord {
    id: string | number;
    start: number;
    end: number;
    word: string;
    score: number;
    dirty?: boolean;
    speaker?: string | null;
}

export interface TranscriptSegment {
    id: string | number;
    start: number;
    end: number;
    text: string;
    speaker: string | null;
    words: TranscriptWord[];
    dirty?: boolean;
}

export interface WaveformSample {
    i: number;
    v: number;
}

export interface WaveformRendererOptions {
    getSegment: () => TranscriptSegment | undefined;
    onUpdateTimecode: (
        segmentId: string | number,
        wordId: string | number,
        start: number,
        end: number,
    ) => void;
}

type WordDrag = DragBehavior<SVGRectElement, TranscriptWord, TranscriptWord>;
type WordDragEvent = D3DragEvent<
    SVGRectElement,
    TranscriptWord,
    TranscriptWord
>;

export class WaveformRenderer {
    // D3 selections have deeply nested generics that change at every chain step;
    // any is pragmatic here and does not affect the public API.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    #svg: any = null;
    #xScale: ScaleLinear<number, number, never> | null = null;
    #wordDrag: WordDrag | null = null;
    #startHandleDrag: WordDrag | null = null;
    #endHandleDrag: WordDrag | null = null;

    readonly containerSelector: string;
    readonly mediaElement: HTMLMediaElement;
    readonly getSegment: () => TranscriptSegment | undefined;
    readonly onUpdateTimecode: WaveformRendererOptions["onUpdateTimecode"];

    constructor(
        containerSelector: string,
        mediaElement: HTMLMediaElement,
        { getSegment, onUpdateTimecode }: WaveformRendererOptions,
    ) {
        this.containerSelector = containerSelector;
        this.mediaElement = mediaElement;
        this.getSegment = getSegment;
        this.onUpdateTimecode = onUpdateTimecode;
    }

    render(
        visibleSamples: WaveformSample[],
        maximumAmplitude: number,
        waveformWidth: number,
    ) {
        const segment = this.getSegment();
        if (!segment) return;

        const xScaleWaveform = scaleLinear()
            .domain([0, visibleSamples.length - 1])
            .range([0, waveformWidth]);

        this.#xScale = scaleLinear()
            .domain([segment.start, segment.end])
            .range([0, waveformWidth]);

        const yScale = scaleLinear()
            .domain([0, maximumAmplitude])
            .range([0, 100]);

        if (!this.#svg) {
            this.#initSVG();
        }

        this.#svg.attr("width", waveformWidth);
        this.#svg.select(".waveform__click-area").attr("width", waveformWidth);

        this.#updateAxis();
        this.#addCurrentTimeMarker();
        this.#updateWaveform(xScaleWaveform, yScale, visibleSamples);
        this.#addWordRects();
    }

    updateTime() {
        if (!this.#svg || !this.#xScale) return;
        this.#addCurrentTimeMarker();
        this.#updateActiveWord();
    }

    destroy() {
        select(this.containerSelector).selectAll("svg").remove();
        this.#svg = null;
        this.#xScale = null;
    }

    #initSVG() {
        const svg = select(this.containerSelector)
            .append("svg")
            .attr("height", HEIGHT_TOTAL);

        svg.append("g").classed("waveform__waveform-group", true);

        svg.append("g")
            .classed("waveform__axis-group", true)
            .attr("transform", `translate(0,${HEIGHT_WAVEFORM})`);

        svg.append("line")
            .classed("waveform__progress", true)
            .attr("y1", 0)
            .attr("y2", HEIGHT_WAVEFORM)
            .attr("stroke", "red");

        svg.append("rect")
            .classed("waveform__click-area", true)
            .attr("x", 0)
            .attr("y", HEIGHT_WAVEFORM)
            .attr("height", HEIGHT_AXIS)
            .attr("fill", "transparent")
            .style("cursor", "crosshair")
            .on("click", (event: MouseEvent) => {
                const [mouseX] = pointer(event);
                seekAndPlay(this.mediaElement, this.#xScale!.invert(mouseX));
            });

        svg.append("g").classed("waveform__words-group", true);

        this.#svg = svg;
        this.#initDragHandlers();
    }

    #initDragHandlers() {
        this.#wordDrag = drag<
            SVGRectElement,
            TranscriptWord,
            TranscriptWord
        >().on("drag", (e: WordDragEvent) => {
            const delta = e.dx / HORIZONTAL_PIXELS_PER_SECOND;
            const segment = this.getSegment()!;
            this.onUpdateTimecode(
                segment.id,
                e.subject.id,
                e.subject.start + delta,
                e.subject.end + delta,
            );
            this.#addWordRects();
        });

        this.#startHandleDrag = drag<
            SVGRectElement,
            TranscriptWord,
            TranscriptWord
        >().on("drag", (e: WordDragEvent) => {
            const segment = this.getSegment()!;
            this.onUpdateTimecode(
                segment.id,
                e.subject.id,
                e.subject.start + e.dx / HORIZONTAL_PIXELS_PER_SECOND,
                e.subject.end,
            );
            this.#addWordRects();
        });

        this.#endHandleDrag = drag<
            SVGRectElement,
            TranscriptWord,
            TranscriptWord
        >().on("drag", (e: WordDragEvent) => {
            const segment = this.getSegment()!;
            this.onUpdateTimecode(
                segment.id,
                e.subject.id,
                e.subject.start,
                e.subject.end + e.dx / HORIZONTAL_PIXELS_PER_SECOND,
            );
            this.#addWordRects();
        });
    }

    #updateAxis() {
        const xAxis = axisBottom(this.#xScale!).tickFormat((d) =>
            formatTimecode(d as number),
        );
        this.#svg.select(".waveform__axis-group").call(xAxis);
    }

    #addCurrentTimeMarker() {
        const x = this.#xScale!(this.mediaElement.currentTime);
        this.#svg.select(".waveform__progress").attr("x1", x).attr("x2", x);
    }

    #updateWaveform(
        xScaleWaveform: ScaleLinear<number, number, never>,
        yScale: ScaleLinear<number, number, never>,
        visibleSamples: WaveformSample[],
    ) {
        this.#svg
            .select(".waveform__waveform-group")
            .selectAll(".waveform-line")
            .data(visibleSamples, (d: WaveformSample) => d.i)
            .join("line")
            .classed("waveform-line", true)
            .attr("x1", (_: WaveformSample, i: number) => xScaleWaveform(i))
            .attr("x2", (_: WaveformSample, i: number) => xScaleWaveform(i))
            .attr("y1", (d: WaveformSample) => MIDDLE_OF_WAVEFORM - yScale(d.v))
            .attr("y2", (d: WaveformSample) => MIDDLE_OF_WAVEFORM + yScale(d.v))
            .attr("stroke", "var(--color-waveform-line)");
    }

    #addWordRects() {
        const xScale = this.#xScale!;
        const segment = this.getSegment()!;
        const wordsGroup = this.#svg.select(".waveform__words-group");

        const wordRects = wordsGroup
            .selectAll(".waveform__word")
            .data(segment.words)
            .join("rect")
            .classed("waveform__word", true)
            .classed(
                "waveform__word--active",
                (d: TranscriptWord) =>
                    this.mediaElement.currentTime > d.start &&
                    this.mediaElement.currentTime < d.end,
            )
            .attr("x", (d: TranscriptWord) => xScale(d.start))
            .attr("y", WORD_Y_OFFSET)
            .attr(
                "width",
                (d: TranscriptWord) => xScale(d.end) - xScale(d.start),
            )
            .attr("height", WORD_HEIGHT)
            .attr("tabindex", 0)
            .style("cursor", "move")
            .on("dblclick", (_e: MouseEvent, d: TranscriptWord) => {
                playSegment(this.mediaElement, d.start, d.end);
            });

        wordRects
            .selectAll("title")
            .data((d: TranscriptWord) => [d])
            .join("title")
            .text(
                (d: TranscriptWord) =>
                    `${formatTimecode(d.start)}–${formatTimecode(d.end)}`,
            );

        wordsGroup
            .selectAll(".waveform__word-text")
            .data(segment.words)
            .join("text")
            .classed("waveform__word-text", true)
            .attr("x", (d: TranscriptWord) =>
                xScale(d.start + (d.end - d.start) / 2),
            )
            .attr("y", WORD_Y_OFFSET + WORD_HEIGHT / 2 + 3)
            .attr("font-size", "14px")
            .text((d: TranscriptWord) => d.word)
            .style("cursor", "move")
            .style("text-anchor", "middle");

        const startHandleRects = wordsGroup
            .selectAll(".waveform__word-start")
            .data(segment.words)
            .join("rect")
            .classed("waveform__word-start", true)
            .attr("x", (d: TranscriptWord) => xScale(d.start))
            .attr("y", WORD_Y_OFFSET)
            .attr("width", 5)
            .attr("height", WORD_HEIGHT)
            .attr("fill", "var(--color-waveform-wordbox)")
            .attr("opacity", 0.9)
            .style("cursor", "col-resize");

        startHandleRects
            .selectAll("title")
            .data((d: TranscriptWord) => [d])
            .join("title")
            .text((d: TranscriptWord) => formatTimecode(d.start));

        const endHandleRects = wordsGroup
            .selectAll(".waveform__word-end")
            .data(segment.words)
            .join("rect")
            .classed("waveform__word-end", true)
            .attr("x", (d: TranscriptWord) => xScale(d.end) - 5)
            .attr("y", WORD_Y_OFFSET)
            .attr("width", 5)
            .attr("height", WORD_HEIGHT)
            .attr("fill", "var(--color-waveform-wordbox)")
            .attr("opacity", 0.9)
            .style("cursor", "col-resize");

        endHandleRects
            .selectAll("title")
            .data((d: TranscriptWord) => [d])
            .join("title")
            .text((d: TranscriptWord) => formatTimecode(d.end));

        wordsGroup.selectAll(".waveform__word").call(this.#wordDrag!);
        wordsGroup
            .selectAll(".waveform__word-start")
            .call(this.#startHandleDrag!);
        wordsGroup.selectAll(".waveform__word-end").call(this.#endHandleDrag!);
    }

    #updateActiveWord() {
        this.#svg
            .select(".waveform__words-group")
            .selectAll(".waveform__word")
            .classed(
                "waveform__word--active",
                (d: TranscriptWord) =>
                    this.mediaElement.currentTime > d.start &&
                    this.mediaElement.currentTime < d.end,
            );
    }
}
