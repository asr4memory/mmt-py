declare module "*.css";

declare module "alpinejs" {
    const Alpine: {
        start(): void;
        data<Args extends unknown[], Component extends object>(
            name: string,
            callback: (...args: Args) => Component,
        ): void;
        [key: string]: unknown;
    };
    export default Alpine;
}
