export default class FileStorage {
    _nextFileId = 0;

    constructor() {
        this.files = [];
    }

    getFile(id) {
        if (!(id in this.files)) {
            throw new ReferenceError(`File with id ${id} does not exist.`);
        }

        return this.files[id];
    }

    storeFile(file) {
        const id = this._getNextFileId();
        this.files[id] = file;
        return id;
    }

    removeFile(id) {
        delete this.files[id];
    }

    _getNextFileId() {
        return this._nextFileId++;
    }
}
