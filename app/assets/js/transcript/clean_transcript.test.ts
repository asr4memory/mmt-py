import { expect, test } from "vitest";
import cleanTranscript from "./clean_transcript";
import type { TranscriptSegment } from "./types";

test("cleanTranscript strips frontend-only properties and rebuilds segment text from words", () => {
    const transcript: TranscriptSegment[] = [
        {
            id: "0",
            start: 0.031,
            end: 6.001,
            text: "Ja, vielen Dank für die netten Worte",
            speaker: null,
            dirty: true,
            words: [
                {
                    id: "0",
                    word: "Ja,",
                    start: 0.031,
                    end: 0.552,
                    score: 1,
                    dirty: true,
                },
                {
                    id: "1",
                    word: "vielen",
                    start: 0.572,
                    end: 2.235,
                    score: 1,
                },
            ],
        },
        {
            id: "1",
            start: 7.031,
            end: 10.001,
            text: "Ja, vielen Dank für die netten Worte",
            speaker: null,
            dirty: true,
            words: [
                {
                    id: "0",
                    word: "vielen",
                    start: 0.572,
                    end: 2.235,
                    score: 1,
                },
            ],
        },
    ];

    const actual = cleanTranscript(transcript);
    const expected = [
        {
            id: "0",
            start: 0.031,
            end: 6.001,
            text: "Ja, vielen",
            speaker: null,
            words: [
                {
                    id: "0",
                    word: "Ja,",
                    start: 0.031,
                    end: 0.552,
                    score: 1,
                },
                {
                    id: "1",
                    word: "vielen",
                    start: 0.572,
                    end: 2.235,
                    score: 1,
                },
            ],
        },
        {
            id: "1",
            start: 7.031,
            end: 10.001,
            text: "vielen",
            speaker: null,
            words: [
                {
                    id: "0",
                    word: "vielen",
                    start: 0.572,
                    end: 2.235,
                    score: 1,
                },
            ],
        },
    ];

    expect(actual).toEqual(expected);
});
