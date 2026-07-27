import { expect, test } from "vitest";
import findPlaybackPosition from "./find_playback_position";
import type { TranscriptSegment } from "./types";

const segments: TranscriptSegment[] = [
    {
        id: "0",
        start: 0.0,
        end: 2.0,
        speakerId: null,
        words: [
            { id: "0", word: "Hello", start: 0.0, end: 0.8, score: 1 },
            { id: "1", word: "World!", start: 1.0, end: 2.0, score: 1 },
        ],
    },
    {
        id: "1",
        start: 2.5,
        end: 4.0,
        speakerId: null,
        words: [
            { id: "2", word: "What's", start: 2.5, end: 3.0, score: 1 },
            { id: "3", word: "up?", start: 3.0, end: 4.0, score: 1 },
        ],
    },
];

test("findPlaybackPosition finds segment and word containing the time", () => {
    expect(findPlaybackPosition(segments, 0.5)).toEqual({
        segmentIdx: 0,
        wordIdx: 0,
    });
    expect(findPlaybackPosition(segments, 3.5)).toEqual({
        segmentIdx: 1,
        wordIdx: 1,
    });
});

test("findPlaybackPosition includes segment and word boundaries", () => {
    expect(findPlaybackPosition(segments, 0.0)).toEqual({
        segmentIdx: 0,
        wordIdx: 0,
    });
    expect(findPlaybackPosition(segments, 4.0)).toEqual({
        segmentIdx: 1,
        wordIdx: 1,
    });
});

test("findPlaybackPosition returns wordIdx -1 in gaps between words", () => {
    expect(findPlaybackPosition(segments, 0.9)).toEqual({
        segmentIdx: 0,
        wordIdx: -1,
    });
});

test("findPlaybackPosition returns -1 indices outside any segment", () => {
    expect(findPlaybackPosition(segments, 2.2)).toEqual({
        segmentIdx: -1,
        wordIdx: -1,
    });
    expect(findPlaybackPosition(segments, 5.0)).toEqual({
        segmentIdx: -1,
        wordIdx: -1,
    });
});

test("findPlaybackPosition handles empty segments", () => {
    expect(findPlaybackPosition([], 1.0)).toEqual({
        segmentIdx: -1,
        wordIdx: -1,
    });
});
