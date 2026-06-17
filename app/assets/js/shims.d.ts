declare module "*.css";

declare module "alpinejs" {
    const Alpine: {
        start(): void;
        [key: string]: unknown;
    };
    export default Alpine;
}
