import { expect, test } from "vitest";
import cleanTranscript from "./clean_transcript";

test("cleanTranscript cleans frontend-related aligns segment text with single words", () => {
    const transcript = [
        {
            id: "0",
            start: 0.031,
            end: 6.001,
            text: "Ja, vielen Dank für die netten Worte",
            dirty: true,
            words: [
                {
                    id: "0",
                    word: "Ja,",
                    start: 0.031,
                    end: 0.552,
                    dirty: true,
                },
                {
                    id: "1",
                    word: "vielen",
                    start: 0.572,
                    end: 2.235,
                },
            ],
        },
        {
            id: "1",
            start: 7.031,
            end: 10.001,
            text: "Ja, vielen Dank für die netten Worte",
            dirty: true,
            words: [
                {
                    id: "0",
                    word: "vielen",
                    start: 0.572,
                    end: 2.235,
                },
            ],
        },
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
        },
    ];

    expect(actual).toEqual(expected);
});
