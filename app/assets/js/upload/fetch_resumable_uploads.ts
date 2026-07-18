import { fetchWrapper } from "../shared/fetch_wrapper";

import type { ResumableUploadsResult } from "./types";

interface FileInfo {
    filename: string;
    size: number;
}

// Ask the server which of the given files match an incomplete upload that can
// be resumed. On any error an empty result is returned so every file is simply
// uploaded from the start.
export default function fetchResumableUploads(
    files: FileInfo[],
    projectId: number,
): Promise<ResumableUploadsResult> {
    return fetchWrapper
        .post<ResumableUploadsResult>(
            `/projects/${projectId}/resumable-uploads/`,
            { files },
        )
        .catch((err) => {
            console.log(err); // TODO: Associate error with upload.
            return { chunk_size: 0, matches: [] };
        });
}
