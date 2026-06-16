import type { TranscriptSegment } from "./types";

export default function getAllSpeakers(segments: TranscriptSegment[]): string[] {
    const speakers: string[] = [];

    segments.forEach((segment) => {
        if (isValidSpeaker(segment.speaker) && !speakers.includes(segment.speaker!)) {
            speakers.push(segment.speaker!);
        }

        segment.words.forEach((word) => {
            if (isValidSpeaker(word.speaker) && !speakers.includes(word.speaker!)) {
                speakers.push(word.speaker!);
            }
        });
    });

    return speakers.toSorted();
}

function isValidSpeaker(speaker: string | null | undefined): boolean {
    return typeof speaker === "string" && speaker.trim() !== "";
}
