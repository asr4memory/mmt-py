export type UploadStatus =
    | "pending"
    | "uploading"
    | "uploaded"
    | "cancelled"
    | "incomplete";

export type ChecksumStatus =
    | "pending"
    | "generating"
    | "transferring"
    | "complete";

export interface ServerResult {
    id: number;
    filename: string;
    chunk_size: number;
}

export interface ResumableMatch {
    filename: string;
    size: number;
    id: number; // server-side UploadedFile id to resume
    chunks_missing: number[];
    checksum_submitted: boolean;
}

export interface ResumableUploadsResult {
    chunk_size: number;
    matches: ResumableMatch[];
}

export interface Upload {
    id?: number;
    fileId?: number; // server-side UploadedFile id, set once registered
    file: File;
    status: UploadStatus;
    transferred: number;
    speed: number; // bytes per second
    eta: number | null; // seconds remaining, null until estimable
    checksumStatus: ChecksumStatus;
    // Set when the file matches an incomplete upload that can be resumed.
    resuming?: boolean;
    chunksMissing?: number[];
    checksumSubmitted?: boolean;
}
