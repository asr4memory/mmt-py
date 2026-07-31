import Alpine from "alpinejs";

import "@/css/main.css";
import { initMessages } from "./messages";
import { createUploadStatusPoller } from "./upload_status_poller";

declare global {
    interface Window {
        Alpine: typeof Alpine;
    }
}

// Initialize Alpine.js
window.Alpine = Alpine;
Alpine.data("uploadStatusPoller", (statusUrl: string) =>
    createUploadStatusPoller(statusUrl),
);
Alpine.start();

initMessages();
