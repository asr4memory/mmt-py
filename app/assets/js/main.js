import "vite/modulepreload-polyfill";

import Alpine from "alpinejs";

import "@/css/main.css";

// Initialize Alpine.js
window.Alpine = Alpine;
Alpine.start();
