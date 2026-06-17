import { fetchWrapper } from "../shared/fetch_wrapper.js";

import type { ServerResult } from "./types";

export default function registerUpload(
    file: File,
    projectId: number,
): Promise<ServerResult | null> {
    const fileInfo = {
        filename: file.name,
        content_type: file.type,
        size: file.size,
    };

    const resultPromise = fetchWrapper
        .post<ServerResult>(`/projects/${projectId}/create-file/`, fileInfo)
        .catch((err) => {
            console.log(err); // TODO: Associate error with upload.
            return null;
        });
    return resultPromise;
}
