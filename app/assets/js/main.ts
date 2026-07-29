import Alpine from "alpinejs";
import htmx from "htmx.org";

import "@/css/main.css";
import { initMessages } from "./messages";
import { initTabs } from "./tabs";

declare global {
    interface Window {
        Alpine: typeof Alpine;
    }
}

// Initialize Alpine.js
window.Alpine = Alpine;
Alpine.start();

// The server answers a request carrying HX-Request with a bare panel. htmx
// restores a history response as the whole body, so a restore request must not
// carry that header, or a cache miss on Back would leave the page without its
// layout.
htmx.config.historyRestoreAsHxRequest = false;

// htmx does not swap a 4xx or 5xx response, which is correct: an error body
// must not land inside the tab panel. Without this listener the click would
// have no visible effect, so the request is repeated as a full page navigation,
// which renders the error page, the login page or the 403 page.
document.body.addEventListener("htmx:responseError", (event) => {
    const detail = (event as CustomEvent).detail;
    window.location.assign(detail.pathInfo.requestPath);
});

initTabs();
initMessages();
