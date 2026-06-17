export default function deformatTimecode(str: string): number {
    const timecode = /([0-9]{1,2}):([0-9]{2}):([0-9]{2})(\.[0-9]{3})/;
    const result = timecode.exec(str);

    if (!result) {
        throw new Error(`Invalid timecode: ${str}`);
    }

    const hours = Number.parseInt(result[1]);
    const minutes = Number.parseInt(result[2]);
    const seconds = Number.parseInt(result[3]);
    const milliseconds = Number.parseFloat(result[4]);

    return hours * 3600 + minutes * 60 + seconds + milliseconds;
}
