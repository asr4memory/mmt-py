import type { DragBehavior, D3DragEvent, ScaleLinear, Selection } from "d3";
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
    #svg: Selection<SVGSVGElement, unknown, HTMLElement, unknown> | null = null;
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

        this.#svg!.attr("width", waveformWidth);
        this.#svg!.select(".waveform__click-area").attr("width", waveformWidth);

        this.#updateAxis();
        this.#updatePlayhead();
        this.#updateWaveform(xScaleWaveform, yScale, visibleSamples);
        this.#updateWordRects();
    }

    updateTime() {
        if (!this.#svg || !this.#xScale) return;
        this.#updatePlayhead();
        this.#updateActiveWord();
    }

    updatePlayhead() {
        if (!this.#svg || !this.#xScale) return;
        this.#updatePlayhead();
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

        svg.append("g")
            .classed("waveform__waveform-group", true)
            .append("path")
            .classed("waveform__samples", true)
            .attr("fill", "none")
            .attr("stroke", "var(--color-waveform-line)");

        svg.append("g")
            .classed("waveform__axis-group", true)
            .attr("transform", `translate(0,${HEIGHT_WAVEFORM})`);

        svg.append("rect")
            .classed("waveform__playhead", true)
            .attr("y", 0)
            .attr("width", 2)
            .attr("height", HEIGHT_WAVEFORM)
            .attr("fill", "red");

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
            const ctx = this.#dragContext(e);
            if (!ctx) return;
            this.onUpdateTimecode(
                ctx.segment.id,
                ctx.word.id,
                ctx.word.start + ctx.delta,
                ctx.word.end + ctx.delta,
            );
            this.#updateWordRects();
        });

        this.#startHandleDrag = drag<
            SVGRectElement,
            TranscriptWord,
            TranscriptWord
        >().on("drag", (e: WordDragEvent) => {
            const ctx = this.#dragContext(e);
            if (!ctx) return;
            this.onUpdateTimecode(
                ctx.segment.id,
                ctx.word.id,
                ctx.word.start + ctx.delta,
                ctx.word.end,
            );
            this.#updateWordRects();
        });

        this.#endHandleDrag = drag<
            SVGRectElement,
            TranscriptWord,
            TranscriptWord
        >().on("drag", (e: WordDragEvent) => {
            const ctx = this.#dragContext(e);
            if (!ctx) return;
            this.onUpdateTimecode(
                ctx.segment.id,
                ctx.word.id,
                ctx.word.start,
                ctx.word.end + ctx.delta,
            );
            this.#updateWordRects();
        });
    }

    // Resolves the dragged word from the store (e.subject may be a stale
    // snapshot) and converts the pixel delta to seconds via the x scale.
    #dragContext(e: WordDragEvent) {
        const segment = this.getSegment();
        const word = segment?.words.find((w) => w.id === e.subject.id);
        if (!segment || !word || !this.#xScale) return null;
        const delta = this.#xScale.invert(e.dx) - this.#xScale.invert(0);
        return { segment, word, delta };
    }

    #updateAxis() {
        const xAxis = axisBottom(this.#xScale!).tickFormat((d) =>
            formatTimecode(d as number),
        );
        this.#svg!.select<SVGGElement>(".waveform__axis-group").call(xAxis);
    }

    #updatePlayhead() {
        const x = this.#xScale!(this.mediaElement.currentTime);
        this.#svg!.select(".waveform__playhead").attr("x", x - 1);
    }

    // One vertical stroke per sample, mirrored around the middle, drawn as
    // a single path instead of one <line> element per sample.
    #updateWaveform(
        xScaleWaveform: ScaleLinear<number, number, never>,
        yScale: ScaleLinear<number, number, never>,
        visibleSamples: WaveformSample[],
    ) {
        const d = visibleSamples
            .map((sample, i) => {
                const x = xScaleWaveform(i);
                const amplitude = yScale(sample.v);
                const y1 = MIDDLE_OF_WAVEFORM - amplitude;
                const y2 = MIDDLE_OF_WAVEFORM + amplitude;
                return `M${x},${y1}V${y2}`;
            })
            .join("");
        this.#svg!.select(".waveform__samples").attr("d", d);
    }

    #updateWordRects() {
        const xScale = this.#xScale!;
        const segment = this.getSegment()!;
        const wordsGroup = this.#svg!.select<SVGGElement>(
            ".waveform__words-group",
        );

        const wordRects = wordsGroup
            .selectAll<SVGRectElement, TranscriptWord>(".waveform__word")
            .data(segment.words, (d) => d.id)
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
            .on("dblclick", (_e: MouseEvent, d) => {
                playSegment(this.mediaElement, d.start, d.end);
            });

        wordRects
            .selectAll<SVGTitleElement, TranscriptWord>("title")
            .data((d) => [d])
            .join("title")
            .text((d) => `${formatTimecode(d.start)}–${formatTimecode(d.end)}`);

        wordsGroup
            .selectAll<SVGTextElement, TranscriptWord>(".waveform__word-text")
            .data(segment.words, (d) => d.id)
            .join("text")
            .classed("waveform__word-text", true)
            .attr("x", (d) => xScale(d.start + (d.end - d.start) / 2))
            .attr("y", WORD_Y_OFFSET + WORD_HEIGHT / 2 + 3)
            .attr("font-size", "14px")
            .text((d) => d.word)
            .style("cursor", "move")
            .style("text-anchor", "middle");

        const startHandleRects = wordsGroup
            .selectAll<SVGRectElement, TranscriptWord>(".waveform__word-start")
            .data(segment.words, (d) => d.id)
            .join("rect")
            .classed("waveform__word-start", true)
            .attr("x", (d) => xScale(d.start))
            .attr("y", WORD_Y_OFFSET)
            .attr("width", 5)
            .attr("height", WORD_HEIGHT)
            .attr("fill", "var(--color-waveform-wordbox)")
            .attr("opacity", 0.9)
            .style("cursor", "col-resize");

        startHandleRects
            .selectAll<SVGTitleElement, TranscriptWord>("title")
            .data((d) => [d])
            .join("title")
            .text((d) => formatTimecode(d.start));

        const endHandleRects = wordsGroup
            .selectAll<SVGRectElement, TranscriptWord>(".waveform__word-end")
            .data(segment.words, (d) => d.id)
            .join("rect")
            .classed("waveform__word-end", true)
            .attr("x", (d) => xScale(d.end) - 5)
            .attr("y", WORD_Y_OFFSET)
            .attr("width", 5)
            .attr("height", WORD_HEIGHT)
            .attr("fill", "var(--color-waveform-wordbox)")
            .attr("opacity", 0.9)
            .style("cursor", "col-resize");

        endHandleRects
            .selectAll<SVGTitleElement, TranscriptWord>("title")
            .data((d) => [d])
            .join("title")
            .text((d) => formatTimecode(d.end));

        wordsGroup
            .selectAll<SVGRectElement, TranscriptWord>(".waveform__word")
            .call(this.#wordDrag!);
        wordsGroup
            .selectAll<SVGRectElement, TranscriptWord>(".waveform__word-start")
            .call(this.#startHandleDrag!);
        wordsGroup
            .selectAll<SVGRectElement, TranscriptWord>(".waveform__word-end")
            .call(this.#endHandleDrag!);
    }

    #updateActiveWord() {
        this.#svg!.select(".waveform__words-group")
            .selectAll<SVGRectElement, TranscriptWord>(".waveform__word")
            .classed(
                "waveform__word--active",
                (d) =>
                    this.mediaElement.currentTime > d.start &&
                    this.mediaElement.currentTime < d.end,
            );
    }
}
