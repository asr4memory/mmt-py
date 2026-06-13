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
    transferred: number;
    speed: number; // bytes per second
    eta: number | null; // seconds remaining, null until estimable
}
