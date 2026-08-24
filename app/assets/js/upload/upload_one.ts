import uploadChunks from "./upload_chunks";
import computeChecksum from "./compute_checksum";
import submitChecksum from "./submit_checksum";
import {
    estimateEta,
    estimateSpeed,
    trimToWindow,
    type Sample,
} from "./transfer_stats";
import type { ChecksumStatus } from "./types";

export interface UploadProgress {
    transferred: number;
    speed: number; // bytes per second
    eta: number | null; // seconds remaining, null until estimable
}

export interface UploadOneArgs {
    fileId: number;
    file: File;
    chunkSize: number;
    // Chunk indices still to send; omit to upload the whole file.
    chunksToUpload?: number[];
    // Skip generating and submitting the checksum when it already exists.
    checksumSubmitted?: boolean;
    signal: AbortSignal;
    onProgress: (progress: UploadProgress) => void;
    onChecksumStatus: (status: ChecksumStatus) => void;
}

/**
 * Upload a single file to an already-registered UploadedFile: send its chunks
 * and, unless the checksum is already submitted, compute and submit the client
 * checksum in parallel. Transfer speed and ETA are derived from the progress
 * samples and reported through onProgress. Resolves when both tasks finish;
 * rejects (with an AbortError when the signal is aborted) if either fails.
 */
export default async function uploadOne({
    fileId,
    file,
    chunkSize,
    chunksToUpload,
    checksumSubmitted = false,
    signal,
    onProgress,
    onChecksumStatus,
}: UploadOneArgs): Promise<void> {
    const samples: Sample[] = [];

    async function generateAndSubmitChecksum() {
        onChecksumStatus("generating");
        const checksum = await computeChecksum(file, signal);
        onChecksumStatus("transferring");
        await submitChecksum(fileId, checksum);
        onChecksumStatus("complete");
    }

    const tasks: Promise<unknown>[] = [
        uploadChunks({
            fileId,
            file,
            chunkSize,
            chunksToUpload,
            signal,
            onProgress: (transferred) => {
                samples.push({ time: Date.now(), bytes: transferred });
                trimToWindow(samples);
                const speed = estimateSpeed(samples);
                onProgress({
                    transferred,
                    speed,
                    eta: estimateEta(file.size - transferred, speed),
                });
            },
        }),
    ];
    if (!checksumSubmitted) {
        tasks.push(generateAndSubmitChecksum());
    }
    await Promise.all(tasks);
}
