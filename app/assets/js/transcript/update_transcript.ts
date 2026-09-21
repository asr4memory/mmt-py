import { fetchWrapper } from "../shared/fetch_wrapper.js";
import type { TranscriptContent } from "./types";

// The label is sent only when it was changed, so a save does not write a
// rename made elsewhere back to the label the editor was opened with.
export default function updateTranscript(
    id: number,
    content: TranscriptContent,
    label?: string,
): Promise<unknown> {
    const payload = label === undefined ? { content } : { content, label };
    return fetchWrapper.patch(`/transcripts/${id}/update/`, payload);
}
