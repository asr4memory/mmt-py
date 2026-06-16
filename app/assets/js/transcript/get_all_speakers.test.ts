import { expect, test } from "vitest";
import getAllSpeakers from "./get_all_speakers";

test("getAllSpeakers extracts all speakers from segments and words", () => {
    const segments = [
        {
            text: "Hello World!",
            words: [
                { word: "Hello", speaker: "SPEAKER_01" },
                { word: "World!" },
            ],
            speaker: "SPEAKER_00",
        },
        {
            text: "What's up?",
            words: [
                { word: "What's", speaker: "SPEAKER_01" },
                { word: "up?", speaker: "SPEAKER_02" },
            ],
        },
    ];
    const actual = getAllSpeakers(segments as any);
    const expected = ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"];
    expect(actual).toEqual(expected);
});
