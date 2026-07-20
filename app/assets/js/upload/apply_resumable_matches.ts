import type { ResumableUploadsResult, Upload } from "./types";

/**
 * Apply the resumable-uploads lookup result to the queue's uploads: mark each
 * matched upload as resuming, record the server file id, the missing chunk
 * indices and whether the checksum was already submitted, mark the checksum
 * status complete when it was, and pre-fill the transferred bytes so the
 * progress bar starts at the bytes already on the server. Each match is applied
 * to a single upload, so two identically named and sized selections do not both
 * resume onto the same server file.
 */
export default function applyResumableMatches(
    uploads: Upload[],
    result: ResumableUploadsResult,
    chunkSize: number,
): void {
    const matchesByKey = new Map(
        result.matches.map((match) => [
            matchKey(match.filename, match.size),
            match,
        ]),
    );
    for (const upload of uploads) {
        const key = matchKey(upload.file.name, upload.file.size);
        const match = matchesByKey.get(key);
        if (!match) continue;
        matchesByKey.delete(key);

        upload.resuming = true;
        upload.fileId = match.id;
        upload.chunksMissing = match.chunks_missing;
        upload.checksumSubmitted = match.checksum_submitted;
        // The checksum was submitted during the previous upload and will not be
        // generated again, so show it as complete rather than leaving it pending.
        if (match.checksum_submitted) {
            upload.checksumStatus = "complete";
        }
        upload.transferred = transferredBytes(
            upload.file.size,
            match.chunks_missing,
            chunkSize,
        );
    }
}

function matchKey(filename: string, size: number): string {
    return `${filename}\u0000${size}`;
}

// Bytes already on the server: the file size minus the size of the chunks still
// missing. Every chunk is chunkSize bytes except the last, which is shorter.
function transferredBytes(
    fileSize: number,
    chunksMissing: number[],
    chunkSize: number,
): number {
    if (chunkSize === 0) return 0;
    const lastIndex = Math.ceil(fileSize / chunkSize) - 1;
    const missingBytes = chunksMissing.reduce(
        (sum, index) =>
            sum +
            (index === lastIndex
                ? fileSize - lastIndex * chunkSize
                : chunkSize),
        0,
    );
    return fileSize - missingBytes;
}
