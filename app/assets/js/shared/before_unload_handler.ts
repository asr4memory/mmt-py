export default function beforeUnloadHandler(event: BeforeUnloadEvent): void {
    event.preventDefault();

    // Included for legacy support, e.g. Chrome/Edge < 119
    event.returnValue = true;
}
