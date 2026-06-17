import Alpine from "alpinejs";

import "@/css/main.css";

declare global {
    interface Window {
        Alpine: typeof Alpine;
    }
}

// Initialize Alpine.js
window.Alpine = Alpine;
Alpine.start();
