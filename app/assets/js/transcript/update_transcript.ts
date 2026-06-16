import { fetchWrapper } from "../shared/fetch_wrapper.js";
import type { RawTranscriptSegment } from "./types";

interface TranscriptContent {
    segments: RawTranscriptSegment[];
}

export default function updateTranscript(
    id: number,
    content: TranscriptContent,
): Promise<unknown> {
    return fetchWrapper.post(`/transcripts/${id}/update/`, { content });
}
