import { fetchWrapper } from "../shared/fetch_wrapper";
import { routes } from "../shared/routes";

export default async function submitChecksum(
    uploadedFileId: number,
    checksum: string,
): Promise<unknown> {
    const resultPromise = fetchWrapper
        .post(routes.uploadedFileUpdate(uploadedFileId), {
            checksum_client: checksum,
        })
        .catch((err) => {
            console.log(err); // TODO: Associate error with upload.
            return null;
        });
    return resultPromise;
}
