import array
import hashlib
import logging
from pathlib import Path
import subprocess

import magic

logger = logging.getLogger(__name__)

SAMPLING_RATE = 100
FFMPEG_SAMPLING_RATE = 1000

# Upper bound for a single transcode, so a hung ffmpeg cannot occupy a worker
# forever. Generous enough for a multi-hour recording on a slow machine.
TRANSCODE_TIMEOUT = 4 * 60 * 60

# Number of characters of ffmpeg's stderr kept in a failure log record. The
# error ffmpeg reports is at the end of its output.
STDERR_TAIL_LENGTH = 2000


def _log_failure(action: str, media_file: Path, exc: Exception) -> None:
    """Log a warning for a failed ffmpeg run with the tail of its stderr."""
    stderr = getattr(exc, 'stderr', None) or b''
    if isinstance(stderr, bytes):
        stderr = stderr.decode('utf-8', errors='replace')
    logger.warning(
        '%s failed for %s: %s',
        action,
        media_file,
        stderr.strip()[-STDERR_TAIL_LENGTH:],
    )


def generate_file_md5(path: Path, block_size=2**20) -> str:
    m = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            buf = f.read(block_size)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()


def extract_waveform_data(media_file: Path) -> list[int] | None:
    # fmt: off
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(media_file),
        '-ac', '1',
        '-filter:a', f'aresample={FFMPEG_SAMPLING_RATE}',
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
    except subprocess.CalledProcessError:
        return None

    data = result.stdout
    if len(data) % 2:
        # Not a whole number of 16-bit samples.
        return None

    # array.array keeps the samples as compact 16-bit ints. struct.unpack would
    # build a tuple of Python int objects instead, costing ~18x the memory and
    # spiking badly on long recordings. Native byte order matches the
    # little-endian pcm_s16le output on the (amd64) deployment.
    samples = array.array('h')
    samples.frombytes(data)
    del data  # drop the raw-bytes copy; the compact array is enough

    batch_size = FFMPEG_SAMPLING_RATE // SAMPLING_RATE
    batch_count = len(samples) // batch_size

    return [
        sum(abs(s) for s in samples[start : start + batch_size]) // batch_size
        for start in range(0, batch_count * batch_size, batch_size)
    ]


def detect_media_type(path: Path) -> str | None:
    """Detect the MIME type from the file's contents using libmagic.

    Browsers report unreliable types from the filename alone (e.g.
    ``application/ogg`` for any .ogg file). libmagic inspects the actual
    bytes, so it can tell audio from video. Returns None on failure rather
    than clobbering the existing type.
    """
    try:
        return magic.from_file(str(path), mime=True)
    except Exception:
        return None


def extract_duration(media_file: Path) -> float | None:
    cmd = [
        'ffprobe',
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        str(media_file),
    ]

    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True
        )
        return float(result.stdout.strip())
    except subprocess.CalledProcessError, ValueError:
        return None


def transcode_to_web_video(src: Path, dst: Path) -> bool:
    """Transcode a video to a 480p H.264/AAC MP4 for inline playback.

    The output is written to a temporary sibling of ``dst`` and moved into
    place only after ffmpeg succeeded, so a failed or interrupted encode
    leaves no half-written file at ``dst``. Returns True on success and False
    when ffmpeg fails or exceeds TRANSCODE_TIMEOUT.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.parent / (dst.stem + '.tmp' + dst.suffix)

    # fmt: off
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(src),
        # Take only the first video stream and, if the source has one, the
        # first audio stream. The '?' keeps the audio mapping optional. Without
        # explicit mapping, ffmpeg's stream selection also carries over
        # subtitle and data streams.
        '-map', '0:v:0',
        '-map', '0:a:0?',
        # Cap the height at 480 without upscaling a smaller source, and derive
        # the width from the aspect ratio. yuv420p requires even dimensions:
        # '-2' rounds the width to an even number, and floor(ih/2)*2 rounds an
        # odd source height down to even before the min.
        '-vf', "scale=-2:'min(480,floor(ih/2)*2)'",
        '-c:v', 'libx264',
        '-profile:v', 'high',
        '-preset', 'medium',
        '-crf', '23',
        # The bitrate cap keeps a high-motion source from producing an
        # oversized file at the CRF quality target.
        '-maxrate', '1500k',
        '-bufsize', '3000k',
        '-force_key_frames', 'expr:gte(t,n_forced*1)',
        # Some decoders reject 4:2:2 and 4:4:4, so the output is 4:2:0.
        '-pix_fmt', 'yuv420p',
        # Move the MP4 index to the front so playback can start before the
        # whole file has been downloaded.
        '-movflags', '+faststart',
        '-c:a', 'aac',
        '-b:a', '160k',
        '-ac', '2',
        str(tmp),
    ]
    # fmt: on

    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
            timeout=TRANSCODE_TIMEOUT,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        _log_failure('Web video transcode', src, exc)
        tmp.unlink(missing_ok=True)
        return False

    tmp.replace(dst)
    return True
