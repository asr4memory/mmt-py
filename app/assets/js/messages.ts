const DISMISS_ANIMATIONS = ["message-dismiss", "message-dismiss-motion"];

export function initMessages(root: ParentNode = document): void {
    for (const message of root.querySelectorAll<HTMLElement>(".message")) {
        message.addEventListener("animationend", (event) => {
            if (DISMISS_ANIMATIONS.includes(event.animationName)) {
                message.remove();
            }
        });
    }
}
