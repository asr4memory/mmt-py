import { fetchWrapper } from "./fetch_wrapper.js";

export default function registerUpload(file, projectId) {
    const fileInfo = {
        filename: file.name,
        content_type: file.type,
        size: file.size,
    };

    const resultPromise = fetchWrapper
        .post(`/projects/${projectId}/create-file/`, fileInfo)
        .catch((err) => {
            console.log(err); // TODO: Associate error with upload.
            return null;
        });
    return resultPromise;
}
