import { mapState, mapWritableState } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import updateTranscript from "../helpers/update_transcript";
import cleanTranscript from "../helpers/clean_transcript";
import TranscriptSegment from "./transcript_segment";

export default {
    components: {
        TranscriptSegment,
    },
    name: "TranscriptTable",
    props: ["id", "label", "mediaType", "uploadedFileId", "projectId"],
    data() {
        return {
            activeSegmentIdx: 0,
            transcriptLoaded: false,
            transcriptData: null,
            waveform: null,
        };
    },
    computed: {
        ...mapState(useTranscriptStore, ["segments", "transcriptIsDirty"]),
        ...mapWritableState(useTranscriptStore, ["segments"]),
        isVideo() {
            return this.mediaType.startsWith("video");
        },
        mediaFileURL() {
            return `/uploaded-files/${this.uploadedFileId}/download/`;
        },
        activeSegment() {
            return this.segments[this.activeSegmentIdx];
        },
        activeWaveformSection() {
            if (!this.waveform) {
                return [];
            }

            const samplingRate = this.waveform.waveform_sampling_rate;

            const startIndex = Math.floor(
                this.activeSegment.start * samplingRate,
            );
            const endIndex = Math.floor(
                this.activeSegment.end * samplingRate,
            );
            const result = this.waveform.waveform.slice(startIndex, endIndex);
            return result;
        },
    },
    methods: {
        updateActiveSegment(newIndex) {
            this.activeSegmentIdx = newIndex;
            this.doWaveFormStuff();
        },
        async saveTranscript() {
            const cleanedTranscript = cleanTranscript(this.segments);
            const result = await updateTranscript(this.id, {
                segments: cleanedTranscript,
            });
            this.segments = cleanedTranscript;
        },
        async prepareWaveForm() {
            this.waveform = await d3.json(
                `/uploaded-files/${this.uploadedFileId}/waveform/`,
            );
            this.transcriptData = await d3.json(
                `/transcripts/${this.id}/json/`,
            );
        },
        async doWaveFormStuff() {
            const mediaElement = this.$refs.media;

            const start = this.activeSegment.start;
            const end = this.activeSegment.end;
            const words = this.activeSegment.words;

            // Declare the chart dimensions and margins.
            const width = 1008;
            const height = 200;
            const marginTop = 20;
            const marginRight = 0;
            const marginBottom = 30;
            const marginLeft = 0;

            // Declare the x (horizontal position) scale.
            const xScale = d3
                .scaleLinear()
                .domain([start, end])
                .range([marginLeft, width - marginRight]);

            const yScale = d3
                .scaleLinear()
                .domain([0, this.waveform.waveform_max])
                .range([0, 100]);

            const xAxis = d3.axisBottom(xScale).tickFormat((d) => {
                const hours = Math.floor(d / 3600);
                const minutes = Math.floor((d % 3600) / 60);
                const seconds = Math.floor(d % 60);

                if (hours > 0) {
                    return `${hours}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
                } else {
                    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
                }
            });

            const svg = d3
                .select("#waveform")
                .append("svg")
                .attr("width", width)
                .attr("height", height);

            /* Progress bar */
            svg.append("rect")
                .attr("id", "progress")
                .attr("x", xScale(0))
                .attr("y", 150)
                .attr("width", xScale(mediaElement?.currentTime) - xScale(0))
                .attr("height", 50)
                .attr("fill", "var(--accent-color)")
                .attr("opacity", 0.5);

            svg.append("g")
                .attr("transform", `translate(0,${height - marginBottom})`)
                .call(xAxis);

            /* Waveform */
            if (this.waveform) {
                const samplingRate = this.waveform.waveform_sampling_rate;
                svg.selectAll(".waveform-line")
                    .data(this.waveform.waveform)
                    .join("line")
                    .classed("waveform-line", true)
                    .attr("x1", (d, idx) =>
                        xScale(idx / samplingRate),
                    )
                    .attr("x2", (d, idx) =>
                        xScale(idx / samplingRate),
                    )
                    .attr("y1", (d) => -1 * yScale(d) + 100)
                    .attr("y2", (d) => yScale(d) + 100)
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
                        });

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
                        .style("cursor", "col-resize");

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
                        .style("cursor", "col-resize");
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
                // Update progress bar.
                d3.select("#progress").attr(
                    "width",
                    xScale(mediaElement.currentTime) - xScale(0),
                );

                // Update word boxes
                update();
            }
        },
    },
    async mounted() {
        const path = `/transcripts/${this.id}/json/`;
        const result = await fetch(path);
        const json = await result.json();
        this.transcriptLoaded = true;
        this.segments = json.segments;

        await this.prepareWaveForm();
        this.doWaveFormStuff();
    },
    template: `
    <h1>{{ label }}</h1>

    <div class="layout layout--transcript transcript">
        <div class="transcript__media-column">
            <video v-if="isVideo" id="media-player" ref="media" controls width="240" class="transcript__media">
                <source :src="mediaFileURL"
                        :type="mediaType" />
            </video>
            <audio v-else id="media-player" ref="media" controls width="240" class="transcript__media">
                <source :src="mediaFileURL"
                        :type="mediaType" />
            </audio>
            <div class="u-mt">
                <button type="button" class="button button--primary" :disabled="!transcriptIsDirty"
                    @click="saveTranscript">{{$t('save_transcript')}}</button>
            </div>
        </div>
        <div v-if="transcriptLoaded" spellcheck="false">
            <TranscriptSegment v-for="(segment, index) in segments"
                @activate-segment="updateActiveSegment"
                :key="segment.start"
                :segment="segment"
                :index="index"
                :active="activeSegmentIdx === index" />
        </div>
        <p v-else>{{$t('loading_transcript')}}</p>
        <div id="waveform" ref="waveform" v-if="transcriptLoaded"></div>
    </div>
    `,
};
