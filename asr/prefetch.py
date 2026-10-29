"""Populates the Hugging Face cache volume mounted at `HF_HOME`.

The image contains no model weights, so the first job that uses a given model
downloads it. This module is run as a one-off container against the same
`mmt-asr-models` volume the service uses, which moves that download out of the
first job:

    podman run --rm \
           --volume mmt-asr-models:/model_cache \
           --volume /path/to/models.toml:/etc/mmt-asr/models.toml:ro \
           --volume /path/to/models:/models:ro \
           --env ALIGN_LANGUAGES="de en" \
           --env HF_TOKEN=... \
           ghcr.io/asr4memory/mmt-asr:TAG python prefetch.py

Files already present in the volume are not downloaded again, so the command
can be repeated after a model or language change. Models with a local
`source` are not downloaded and are skipped.
"""

import whisperx

import config
from models import Registry, load_registry

# Loading on the CPU is enough to populate the cache; the GPU is only used at
# run time. The prefetch container therefore needs no GPU device.
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# Named explicitly rather than left to whisperx's default, because the default
# changes between whisperx versions and the repository is gated: access is
# granted per repository, so the prefetch run and the transcriber have to name
# the same one.
DIARIZATION_MODEL = "pyannote/speaker-diarization-community-1"


def prefetch(registry: Registry, languages: list[str], hf_token: str | None) -> None:
    for spec in registry.models:
        if not spec.is_local:
            whisperx.load_model(spec.source, DEVICE, compute_type=COMPUTE_TYPE)
    for language in languages:
        whisperx.load_align_model(language_code=language, device=DEVICE)
    if hf_token:
        # The diarization models are gated on Hugging Face and are never part
        # of the image; constructing the pipeline downloads them.
        from whisperx.diarize import DiarizationPipeline

        DiarizationPipeline(DIARIZATION_MODEL, token=hf_token, device=DEVICE)


def main() -> None:
    prefetch(
        load_registry(config.models_file()),
        config.align_languages(),
        config.hf_token(),
    )


if __name__ == "__main__":
    main()
