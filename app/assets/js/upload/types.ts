export type UploadStatus =
    | "pending"
    | "uploading"
    | "uploaded"
    | "cancelled"
    | "incomplete";

export interface Upload {
    id?: number;
    file: File;
    status: UploadStatus;
    progress: number;
}
