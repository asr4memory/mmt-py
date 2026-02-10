"""ffmpeg commands as Python functions."""

from pathlib import Path
import subprocess
import struct


def extract_waveform_data(media_file: Path, sampling_rate: int = 10) -> list[int]:
    """Extracts audio waveform data with ffmpeg

    Parameters
    ----------
    media_file : Path
        The location of the audio or video file
    sampling_rate : int, optional
        Samples per second of the waveform data (default is 10)

    Returns
    -------
    list[int]
        a list of integers representing the waveform data
    """

    # fmt: off
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(media_file),
        '-ac', '1',
        '-filter:a', f'aresample={sampling_rate}',
        '-map', '0:a',
        '-c:a', 'pcm_s16le',
        '-f', 's16le',
        '-',
    ]
    # fmt: on

    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True
        )
        # Convert binary data to list of integers
        audio_data = [x[0] for x in struct.iter_unpack('<h', result.stdout)]
        return audio_data
    except subprocess.CalledProcessError as e:
        print(f'Error generating waveform: {e.stderr}')
        raise
