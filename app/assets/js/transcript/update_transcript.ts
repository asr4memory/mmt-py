import { fetchWrapper } from "../shared/fetch_wrapper.js";
import type { TranscriptContent } from "./types";

export default function updateTranscript(
    id: number,
    content: TranscriptContent,
): Promise<unknown> {
    return fetchWrapper.patch(`/transcripts/${id}/update/`, { content });
}
