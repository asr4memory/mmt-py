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

    test("removes a message when its close button is clicked", () => {
        const { stack, message } = makeStack();
        const close = document.createElement("button");
        close.className = "message__close";
        message.append(close);
        initMessages(stack);
        close.click();
        expect(message.isConnected).toBe(false);
        stack.remove();
    });

    test("only removes the message whose animation ended in a multi-message stack", () => {
        const { stack, message: first } = makeStack();
        const second = first.cloneNode(true) as HTMLElement;
        stack.append(second);
        initMessages(stack);
        fireAnimationEnd(first, "message-dismiss");
        expect(first.isConnected).toBe(false);
        expect(second.isConnected).toBe(true);
        stack.remove();
    });

    test("only removes the message whose close button was clicked in a multi-message stack", () => {
        const { stack, message: first } = makeStack();
        const makeClose = () => {
            const close = document.createElement("button");
            close.className = "message__close";
            return close;
        };
        first.append(makeClose());
        const second = first.cloneNode(true) as HTMLElement;
        stack.append(second);
        initMessages(stack);
        second.querySelector<HTMLElement>(".message__close")?.click();
        expect(first.isConnected).toBe(true);
        expect(second.isConnected).toBe(false);
        stack.remove();
    });

    test("does not remove a message on clicks outside the close button", () => {
        const { stack, message } = makeStack();
        initMessages(stack);
        message.click();
        expect(message.isConnected).toBe(true);
        stack.remove();
    });
});
