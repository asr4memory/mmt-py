export interface Speaker {
    id: string;
    name: string;
    color: string;
}

export interface Mention {
    label: string;
}

export interface TranscriptWord {
    id: string;
    start: number;
    end: number;
    word: string;
    score: number;
    dirty?: boolean;
    speakerId?: string | null;
    ner_mention_id?: string | null;
}

export interface TranscriptSegment {
    id: string;
    start: number;
    end: number;
    text: string;
    speakerId: string | null;
    words: TranscriptWord[];
    dirty?: boolean;
}

export interface TranscriptContent {
    format: "mmt-transcript";
    version: number;
    speakers: Speaker[];
    mentions: Record<string, Mention>;
    segments: TranscriptSegment[];
}

export interface WaveformSample {
    i: number;
    v: number;
}

export interface WaveformRendererOptions {
    getSegment: () => TranscriptSegment | undefined;
    onUpdateTimecode: (
        segmentId: string,
        wordId: string,
        start: number,
        end: number,
    ) => void;
}
