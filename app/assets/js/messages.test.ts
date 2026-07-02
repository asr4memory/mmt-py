import { describe, expect, test } from "vitest";
import { initMessages } from "./messages";

function makeStack(): { stack: HTMLElement; message: HTMLElement } {
    const stack = document.createElement("div");
    stack.className = "message-stack";
    const message = document.createElement("div");
    message.className = "message";
    const text = document.createElement("p");
    text.className = "message__text";
    text.textContent = "Saved.";
    message.append(text);
    stack.append(message);
    document.body.append(stack);
    return { stack, message };
}

function fireAnimationEnd(el: HTMLElement, animationName: string): void {
    const event = new Event("animationend", { bubbles: true });
    Object.assign(event, { animationName });
    el.dispatchEvent(event);
}

describe("initMessages", () => {
    test("removes a message when its dismiss animation ends", () => {
        const { stack, message } = makeStack();
        initMessages(stack);
        fireAnimationEnd(message, "message-dismiss");
        expect(message.isConnected).toBe(false);
        stack.remove();
    });

    test("removes a message when the motion variant ends", () => {
        const { stack, message } = makeStack();
        initMessages(stack);
        fireAnimationEnd(message, "message-dismiss-motion");
        expect(message.isConnected).toBe(false);
        stack.remove();
    });

    test("ignores unrelated animations", () => {
        const { stack, message } = makeStack();
        initMessages(stack);
        fireAnimationEnd(message, "spinner-rotate");
        expect(message.isConnected).toBe(true);
        stack.remove();
    });
});
