let nextFileId = 0

export default function getNextFileId() {
  const idToReturn = nextFileId
  nextFileId += 1
  return idToReturn
}
