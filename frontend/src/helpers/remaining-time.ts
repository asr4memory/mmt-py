export default function remainingTime(startDate: Date, fileSize: number, fileTransferred: number) {
  const processedTime = Date.now() - startDate.getTime()
  const totalTime = (processedTime * fileSize) / fileTransferred
  const remainingTime = totalTime - processedTime

  return remainingTime
}
