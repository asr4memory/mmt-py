import re
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.http import content_disposition_header

RANGE_RE = re.compile(r'^bytes=(\d*)-(\d*)$')


def _file_range_iterator(file_path, start, length, chunk_size=65536):
    "Yield `length` bytes from `file_path` starting at byte offset `start`."
    with open(file_path, 'rb') as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            chunk = f.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def serve_file(request, file_path, *, content_type, as_attachment=False, filename=''):
    """Serve a file with HTTP Range support so media can be seeked.

    Honors a single-range `Range: bytes=...` request header, replying with a
    `206 Partial Content` slice, `416` when the range is unsatisfiable, or the
    full `200` body otherwise. Always advertises `Accept-Ranges: bytes`.

    When `MMT_X_ACCEL_LOCATION` is set, the transfer is delegated to nginx
    instead and this function reads no bytes at all.
    """
    if settings.MMT_X_ACCEL_LOCATION:
        return x_accel_response(
            file_path,
            content_type=content_type,
            as_attachment=as_attachment,
            filename=filename,
        )

    file_size = file_path.stat().st_size
    start, end = 0, file_size - 1
    status = 200

    range_header = request.headers.get('Range')
    if range_header and (match := RANGE_RE.match(range_header.strip())):
        first, last = match.group(1), match.group(2)
        if first == '' and last == '':
            pass  # `bytes=-` is invalid; serve the whole file.
        elif first == '':
            # Suffix range: the last `last` bytes of the file.
            suffix_length = int(last)
            if suffix_length == 0:
                return _unsatisfiable_response(file_size)
            start = max(file_size - suffix_length, 0)
            status = 206
        else:
            start = int(first)
            end = int(last) if last != '' else file_size - 1
            end = min(end, file_size - 1)
            if start > end or start >= file_size:
                return _unsatisfiable_response(file_size)
            status = 206

    length = end - start + 1
    response = StreamingHttpResponse(
        _file_range_iterator(file_path, start, length),
        status=status,
        content_type=content_type,
    )
    response['Accept-Ranges'] = 'bytes'
    response['Content-Length'] = str(length)
    if status == 206:
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'

    # content_disposition_header encodes a non-ASCII name per RFC 8187.
    # Interpolating it by hand makes Django encode it as an RFC 2047 word
    # instead, which browsers do not read in this header. It returns None for
    # an inline response without a filename, which still needs the bare
    # disposition type.
    disposition = 'attachment' if as_attachment else 'inline'
    response['Content-Disposition'] = (
        content_disposition_header(as_attachment, filename) or disposition
    )
    return response


def _unsatisfiable_response(file_size):
    response = HttpResponse(status=416)
    response['Content-Range'] = f'bytes */{file_size}'
    return response


def x_accel_response(file_path, *, content_type, as_attachment, filename):
    """Empty response that tells nginx to serve `file_path` itself.

    The file is named relative to `MMT_USER_FILES_DIR`, below the internal
    location in `MMT_X_ACCEL_LOCATION`. nginx discards this body, applies the
    client's `Range` header to the internal request and sets `Accept-Ranges`,
    `Content-Length` and `Content-Range` itself.
    """
    root = settings.MMT_USER_FILES_DIR.resolve()
    try:
        # Both sides are resolved because a symlinked user files directory is
        # normal in development and would otherwise defeat the comparison.
        relative = file_path.resolve().relative_to(root)
    except ValueError:
        raise SuspiciousFileOperation(
            f'{file_path} is not inside the user files directory {root}'
        )

    response = HttpResponse(content_type=content_type)
    # quote's default safe='/' keeps the path separators and encodes
    # everything else; nginx reads the header value as a URI. Filenames
    # written since the ASCII filenames feature need this only for spaces and
    # punctuation, rows predating it can hold any Unicode name.
    response['X-Accel-Redirect'] = settings.MMT_X_ACCEL_LOCATION + quote(str(relative))
    disposition = 'attachment' if as_attachment else 'inline'
    response['Content-Disposition'] = (
        content_disposition_header(as_attachment, filename) or disposition
    )
    # Django sets 0 for the empty body. The length that belongs on the
    # response is the length of the file or of the range, which nginx
    # determines.
    del response['Content-Length']
    return response
