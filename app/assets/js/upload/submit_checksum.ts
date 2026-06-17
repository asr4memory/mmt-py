import { fetchWrapper } from "../shared/fetch_wrapper";

export default async function submitChecksum(
    uploadedFileId: number,
    checksum: string,
): Promise<unknown> {
    const resultPromise = fetchWrapper
        .post(`/uploaded-files/${uploadedFileId}/update/`, {
            checksum_client: checksum,
        })
        .catch((err) => {
            console.log(err); // TODO: Associate error with upload.
            return null;
        });
    return resultPromise;
}
