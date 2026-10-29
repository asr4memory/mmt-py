"""The registry of whisper models: the only module that knows its file format."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_TOP_LEVEL_KEYS = {"default", "models"}
_MODEL_DEFAULTS = {"compute_type": "float16", "batch_size": 16, "description": ""}
_MODEL_TYPES = {
    "source": str,
    "compute_type": str,
    "batch_size": int,
    "description": str,
}


class RegistryError(Exception):
    """The registry file is missing or violates the format."""


@dataclass(frozen=True)
class ModelSpec:
    name: str
    source: str
    compute_type: str
    batch_size: int
    description: str

    @property
    def is_local(self) -> bool:
        """True if `source` is a local directory, not a Hugging Face model name."""
        return self.source.startswith("/")


@dataclass(frozen=True)
class Registry:
    default: ModelSpec
    models: tuple[ModelSpec, ...]

    def get(self, name: str | None) -> ModelSpec | None:
        """The model named `name`, the default for None, None if unknown."""
        if name is None:
            return self.default
        return next((spec for spec in self.models if spec.name == name), None)


def load_registry(path: Path) -> Registry:
    try:
        data = tomllib.loads(Path(path).read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RegistryError(f"cannot read {path}: {exc}") from exc

    unknown = set(data) - _TOP_LEVEL_KEYS
    if unknown:
        raise RegistryError(f"unknown top-level keys: {', '.join(sorted(unknown))}")
    entries = data.get("models")
    if not isinstance(entries, dict) or not entries:
        raise RegistryError("models: at least one model is required")

    models = tuple(_model_spec(name, entry) for name, entry in entries.items())
    default = next((spec for spec in models if spec.name == data.get("default")), None)
    if default is None:
        raise RegistryError(f"default: {data.get('default')!r} is not in models")
    return Registry(default=default, models=models)


def _model_spec(name: str, entry: object) -> ModelSpec:
    if not _NAME.match(name):
        raise RegistryError(f"model {name!r}: invalid name")
    if not isinstance(entry, dict):
        raise RegistryError(f"model {name!r}: must be a table")
    unknown = set(entry) - set(_MODEL_TYPES)
    if unknown:
        raise RegistryError(
            f"model {name!r}: unknown keys: {', '.join(sorted(unknown))}"
        )
    if "source" not in entry:
        raise RegistryError(f"model {name!r}: source is required")

    fields = _MODEL_DEFAULTS | entry
    for key, expected in _MODEL_TYPES.items():
        # bool is a subclass of int, but `batch_size = true` is not a batch size.
        if not isinstance(fields[key], expected) or isinstance(fields[key], bool):
            raise RegistryError(f"model {name!r}: {key} must be a {expected.__name__}")

    spec = ModelSpec(name=name, **fields)
    if spec.is_local and not Path(spec.source).is_dir():
        raise RegistryError(f"model {name!r}: {spec.source} is not a directory")
    return spec
