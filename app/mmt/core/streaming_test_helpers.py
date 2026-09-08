"""Helpers for tests that read a streamed response body."""

import asyncio


def streamed_body(response) -> bytes:
    """Return the complete body of a `StreamingHttpResponse`.

    The file responses are asynchronous iterators. Iterating them directly
    from synchronous test code makes Django collect the whole body through
    `async_to_sync` and emit a warning; consuming them in an event loop is
    the intended way.
    """

    async def collect():
        return b''.join([part async for part in response.streaming_content])

    return asyncio.run(collect())
