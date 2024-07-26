export default class FileStorage {
  files: { [key: number]: File }

  constructor() {
    this.files = []
  }

  getFile(id: number) {
    if (!(id in this.files)) {
      throw new ReferenceError(`File with id ${id} does not exist.`)
    }

    return this.files[id]
  }

  storeFile(id: number, file: File) {
    if (id in this.files) {
      throw new ReferenceError(`File with id ${id} already exists.`)
    }

    this.files[id] = file
  }

  removeFile(id: number) {
    delete this.files[id]
  }
}
