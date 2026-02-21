import { expect, test } from "vitest";
import cleanTranscript from "./clean_transcript";

test("cleanTranscript aligns segment text with single words", () => {
    const transcript = [
        {
            start: 0.031,
            end: 6.001,
            text: "Ja, vielen Dank für die netten Worte",
            dirty: true,
            words: [
                {
                    word: "Ja,",
                    start: 0.031,
                    end: 0.552,
                    dirty: true,
                },
                {
                    word: "vielen",
                    start: 0.572,
                    end: 2.235,
                },
            ],
        },
        {
            start: 7.031,
            end: 10.001,
            text: "Ja, vielen Dank für die netten Worte",
            dirty: true,
            words: [
                {
                    word: "vielen",
                    start: 0.572,
                    end: 2.235,
                },
            ],
        }
    ];

    const actual = cleanTranscript(transcript);
    const expected = [
        {
            start: 0.031,
            end: 6.001,
            text: "Ja, vielen",
            words: [
                {
                    word: "Ja,",
                    start: 0.031,
                    end: 0.552,
                },
                {
                    word: "vielen",
                    start: 0.572,
                    end: 2.235,
                },
            ],
        },
        {
            start: 7.031,
            end: 10.001,
            text: "vielen",
            words: [
                {
                    word: "vielen",
                    start: 0.572,
                    end: 2.235,
                },
            ],
        }
    ];

    expect(actual).toEqual(expected);
});
