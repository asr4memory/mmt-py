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

export interface Upload {
    id?: number;
    file: File;
    status: UploadStatus;
    transferred: number;
    speed: number; // bytes per second
    eta: number | null; // seconds remaining, null until estimable
    checksumStatus: ChecksumStatus;
}
