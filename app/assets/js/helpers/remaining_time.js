export default function remainingTime(startDate, fileSize, fileTransferred) {
    const processedTime = Date.now() - startDate.getTime();
    const totalTime = (processedTime * fileSize) / fileTransferred;
    return totalTime - processedTime;
}
