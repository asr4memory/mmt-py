export default class FileStorage {
    constructor() {
        this.files = [];
    }

    getFile(id) {
        if (!(id in this.files)) {
            throw new ReferenceError(`File with id ${id} does not exist.`);
        }

        return this.files[id];
    }

    storeFile(id, file) {
        if (id in this.files) {
            throw new ReferenceError(`File with id ${id} already exists.`);
        }

        this.files[id] = file;
    }

    removeFile(id) {
        delete this.files[id];
    }
}
