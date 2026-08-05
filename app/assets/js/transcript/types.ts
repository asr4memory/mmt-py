export interface Speaker {
    id: string;
    name: string;
    color: string;
}

// A date has no identity, so no entity carries the DATE label a mention may
// have.
export type EntityType = "PER" | "ORG" | "LOC";

export interface Entity {
    name: string;
    type: EntityType;
    aliases: string[];
    wikidataId?: string | null;
}

export interface Mention {
    label: string;
    score: number;
    // Always present: the backend stores the validated model, so a mention
    // that is linked to no entity carries an explicit null.
    entityId: string | null;
}

export interface TranscriptWord {
    id: string;
    start: number;
    end: number;
    word: string;
    score: number;
    dirty?: boolean;
    speakerId?: string | null;
    mentionId?: string | null;
}

export interface TranscriptSegment {
    id: string;
    start: number;
    end: number;
    speakerId: string | null;
    words: TranscriptWord[];
    dirty?: boolean;
}

export interface TranscriptContent {
    format: "mmt-transcript";
    version: number;
    language?: string | null;
    speakers: Speaker[];
    entities: Record<string, Entity>;
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
