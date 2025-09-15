import getCookie from './get_cookie.js';

const csrftoken = getCookie(document.cookie, 'csrftoken');

export default function uploadFile(options) {
    const { fileId, file, filename, onProgress, onEnd, onAbort } = options;
    const uploadEndPoint = `/uploaded-files/${fileId}/upload/`;
    const request = buildRequest(uploadEndPoint, onProgress, onEnd, onAbort);
    const formData = new FormData();
    formData.append('file', file, filename);
    request.send(formData);
    return request;
}

function buildRequest(url, onProgress, onEnd, onAbort) {
    const request = new XMLHttpRequest();
    request.withCredentials = true;
    request.open('POST', url);
    request.setRequestHeader('X-CSRFToken', csrftoken);
    request.addEventListener('loadend', () => onEnd?.());
    request.addEventListener('abort', () => onAbort?.());
    request.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
            onProgress?.(event.loaded);
        }
    });
    return request;
}
