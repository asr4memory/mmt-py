import { fetchWrapper } from "./fetch_wrapper.js";

export default function registerUpload(file, uploadJobId) {
    const fileInfo = {
        filename: file.name,
        content_type: file.type,
        size: file.size,
    };

    return fetchWrapper
        .post(`/upload-jobs/${uploadJobId}/create-file/`, fileInfo)
        .catch((err) => {
            console.log(err); // TODO: Associate error with upload.
            return null;
        });
}
