"""What the ASR service offers, read from its GET /info endpoint."""

from dataclasses import dataclass

import requests
from django.conf import settings
from django.core.cache import cache

CACHE_KEY = 'asr_info'
AVAILABLE_TIMEOUT = 300
UNAVAILABLE_TIMEOUT = 30
# Stored in place of None, which the cache returns for a missing key.
UNAVAILABLE = 'unavailable'


@dataclass(frozen=True)
class AsrModel:
    name: str
    description: str


@dataclass(frozen=True)
class AsrInfo:
    version: str
    diarization: bool
    default_model: str
    models: tuple[AsrModel, ...]


def asr_info() -> AsrInfo | None:
    """The service's version, diarization and models; None if it is unavailable."""
    cached = cache.get(CACHE_KEY)
    if cached == UNAVAILABLE:
        return None
    if cached is not None:
        return cached

    info = _fetch()
    if info is None:
        cache.set(CACHE_KEY, UNAVAILABLE, UNAVAILABLE_TIMEOUT)
    else:
        cache.set(CACHE_KEY, info, AVAILABLE_TIMEOUT)
    return info


def _fetch() -> AsrInfo | None:
    try:
        response = requests.get(f'{settings.MMT_ASR_API_URL}/info', timeout=2)
        response.raise_for_status()
        data = response.json()
        return AsrInfo(
            version=data['version'],
            diarization=data['diarization'],
            default_model=data['default_model'],
            models=tuple(
                AsrModel(name=model['name'], description=model['description'])
                for model in data['models']
            ),
        )
    except requests.RequestException, ValueError, KeyError, TypeError:
        return None
