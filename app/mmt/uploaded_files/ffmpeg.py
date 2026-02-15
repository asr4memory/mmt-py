"""ffmpeg commands as Python functions."""

from pathlib import Path
import subprocess
import struct


def extract_waveform_data(media_file: Path, sampling_rate: int = 100) -> list[int]:
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

    HIGH_SAMPLING_RATE = 1000

    # fmt: off
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(media_file),
        '-ac', '1',
        '-filter:a', f'aresample={HIGH_SAMPLING_RATE}',
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

        data = result.stdout
        num_samples = len(data) // 2
        waveform = struct.unpack(f'<{num_samples}h', data)
        audio_data = waveform

        audio_data_abs = tuple(abs(val) for val in audio_data)

        batch_size = HIGH_SAMPLING_RATE // sampling_rate
        batch_count = num_samples // batch_size

        new_data = [
            sum(audio_data_abs[x * batch_size : (x + 1) * batch_size]) // batch_size
            for x in range(batch_count)
        ]

        audio_data = new_data

        return audio_data
    except subprocess.CalledProcessError as e:
        print(f'Error generating waveform: {e.stderr}')
        raise
