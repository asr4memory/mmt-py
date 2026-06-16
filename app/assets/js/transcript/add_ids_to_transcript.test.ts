import { expect, test } from "vitest";
import addIDsToTranscript from "./add_ids_to_transcript";
import type { RawTranscriptSegment } from "./types";

test("addIDsToTranscript adds ids to segment and word arrays", () => {
    const segments: RawTranscriptSegment[] = [
        {
            start: 0.0,
            end: 1.0,
            text: "Hello World!",
            speaker: null,
            words: [
                { word: "Hello", start: 0.0, end: 0.5, score: 1 },
                { word: "World!", start: 0.5, end: 1.0, score: 1 },
            ],
        },
        {
            start: 1.5,
            end: 2.5,
            text: "What's up?",
            speaker: null,
            words: [
                { word: "What's", start: 1.5, end: 2.0, score: 1 },
                { word: "up?", start: 2.0, end: 2.5, score: 1 },
            ],
        },
    ];
    const actual = addIDsToTranscript(segments);
    expect(actual[0].id).toBe("0");
    expect(actual[0].words[0].id).toBe("0");
    expect(actual[0].words[1].id).toBe("1");
    expect(actual[1].id).toBe("1");
    expect(actual[1].words[0].id).toBe("0");
});
