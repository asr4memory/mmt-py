import { fetchWrapper } from "./fetch_wrapper.js";

export default function updateTranscript(id, content) {
    const resultPromise = fetchWrapper
        .post(`/transcripts/${id}/update/`, { content })
        .catch((err) => {
            console.log(err);
            return null;
        });
    return resultPromise;
}
