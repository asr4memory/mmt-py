import getCookie from "./get_cookie.js";

const csrftoken = getCookie("csrftoken");

export const fetchWrapper = {
    get: request("GET"),
    post: request("POST"),
    put: request("PUT"),
    delete: request("DELETE"),
};

function request(method) {
    return (url, body) => {
        const requestOptions = {
            method,
            credentials: "include",
            headers: {},
        };
        if (body) {
            requestOptions.headers["Content-Type"] = "application/json";
            requestOptions.body = JSON.stringify(body);
        }
        if (csrftoken) {
            requestOptions.headers["X-CSRFToken"] = csrftoken;
        }
        return fetch(url, requestOptions).then(handleResponse);
    };
}

// helper functions

/*
function authHeader(url: string) {
  // return auth header with jwt if user is logged in and request is to the api url
  const { user } = useAuthStore()
  const isLoggedIn = !!user?.token
  const isApiUrl = url.startsWith(import.meta.env.VITE_API_URL)
  if (isLoggedIn && isApiUrl) {
    return { Authorization: `Bearer ${user.token}` }
  } else {
    return {}
  }
}
*/

function handleResponse(response) {
    return response.text().then((text) => {
        const data = text && JSON.parse(text);

        if (!response.ok) {
            const error = data?.code || data?.message || response.statusText;
            return Promise.reject(error);
        }

        return data;
    });
}
