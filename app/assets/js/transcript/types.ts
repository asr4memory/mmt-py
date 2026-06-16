export type RawTranscriptWord = Omit<TranscriptWord, "id">;
export type RawTranscriptSegment = Omit<TranscriptSegment, "id" | "words"> & {
    words: RawTranscriptWord[];
};

export interface TranscriptWord {
    id: string | number;
    start: number;
    end: number;
    word: string;
    score: number;
    dirty?: boolean;
    speaker?: string | null;
    ner_entity?: string | null;
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
