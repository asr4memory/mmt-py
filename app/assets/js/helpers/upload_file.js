import getCookie from './get_cookie.js';

const csrftoken = getCookie(document.cookie, 'csrftoken');

export default function uploadFile(options) {
    const { fileId, file, filename, onProgress, onEnd, onAbort } = options;
    const request = buildRequest(fileId, onProgress, onEnd, onAbort);
    const formData = new FormData();
    formData.append('file', file, filename);
    request.send(formData);
    return request;
}

function buildRequest(fileId, onProgress, onEnd, onAbort) {
    const request = new XMLHttpRequest();
    request.withCredentials = true;
    const url = `/uploaded-files/${fileId}/upload/`;
    request.open('POST', url);

    request.setRequestHeader('X-CSRFToken', csrftoken);
    request.setRequestHeader('Uploaded-File-Id', fileId);
    request.addEventListener('loadend', () => onEnd?.());
    request.addEventListener('abort', () => onAbort?.());
    request.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
            onProgress?.(event.loaded);
        }
    });
    return request;
}
