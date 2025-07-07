import { fetchWrapper } from "./fetch_wrapper";

const locale = document.documentElement.lang;

export default async function submitChecksum(uploadedFileId, checksum) {
    const resultPromise = fetchWrapper
        .post(`/${locale}/uploaded-files/${uploadedFileId}/update/`, {
            checksum_client: checksum,
        })
        .catch((err) => {
            console.log(err); // TODO: Associate error with upload.
            return null;
        });
    return resultPromise;
}
