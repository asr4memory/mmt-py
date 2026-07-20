// Single source of truth for the server URL paths the frontend builds. Keeping
// the path shapes in one place avoids duplicating the `/projects/` and
// `/uploaded-files/` prefixes across call sites and gives every route a
// type-checked builder.
export const routes = {
    project: (id: number) => `/projects/${id}/`,
    createFile: (projectId: number) => `/projects/${projectId}/create-file/`,
    resumableUploads: (projectId: number) =>
        `/projects/${projectId}/resumable-uploads/`,
    uploadedFile: (id: number) => `/uploaded-files/${id}/`,
    uploadedFileStream: (id: number) => `/uploaded-files/${id}/stream/`,
    uploadedFileWaveform: (id: number) => `/uploaded-files/${id}/waveform/`,
    uploadedFileUpdate: (id: number) => `/uploaded-files/${id}/update/`,
    uploadedFileUploadChunk: (id: number, index: number) =>
        `/uploaded-files/${id}/upload/${index}/`,
};
