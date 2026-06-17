import getCookie from "./get_cookie.js";

const csrftoken = getCookie(document.cookie, "csrftoken");

export const fetchWrapper = {
    get: request("GET"),
    post: request("POST"),
    put: request("PUT"),
    delete: request("DELETE"),
};

function request(method: string) {
    return <T = unknown>(url: string, body?: unknown): Promise<T> => {
        const headers: Record<string, string> = {};
        const requestOptions: RequestInit = {
            method,
            credentials: "include",
            headers,
        };
        if (body) {
            headers["Content-Type"] = "application/json";
            requestOptions.body = JSON.stringify(body);
        }
        if (csrftoken) {
            headers["X-CSRFToken"] = csrftoken;
        }
        return fetch(url, requestOptions).then(handleResponse) as Promise<T>;
    };
}

function handleResponse(response: Response): Promise<unknown> {
    return response.text().then((text) => {
        const data = text ? JSON.parse(text) : null;

        if (!response.ok) {
            const error = data?.code || data?.message || response.statusText;
            return Promise.reject(error);
        }

        return data;
    });
}
