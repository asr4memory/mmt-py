import Alpine from "alpinejs";

import "@/css/main.css";
import { initMessages } from "./messages";

declare global {
    interface Window {
        Alpine: typeof Alpine;
    }
}

// Initialize Alpine.js
window.Alpine = Alpine;
Alpine.start();

initMessages();
