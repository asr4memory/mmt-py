from pathlib import Path

import pytest

from models import ModelSpec, RegistryError, load_registry

HERE = Path(__file__).parent


def write(tmp_path, text):
    path = tmp_path / "models.toml"
    path.write_text(text)
    return path


def test_a_valid_file_is_loaded_in_file_order(tmp_path):
    local = tmp_path / "verbatim"
    local.mkdir()
    path = write(
        tmp_path,
        f"""
default = "large-v3"

[models.small]
source = "small"
compute_type = "int8"
batch_size = 4
description = "Whisper small"

[models.large-v3]
source = "large-v3"

[models.large-v3-verbatim-v1]
source = "{local}"
compute_type = "int8_float16"
batch_size = 8
""",
    )

    registry = load_registry(path)

    assert [spec.name for spec in registry.models] == [
        "small",
        "large-v3",
        "large-v3-verbatim-v1",
    ]
    assert registry.default.name == "large-v3"
    assert registry.models[0] == ModelSpec(
        name="small",
        source="small",
        compute_type="int8",
        batch_size=4,
        description="Whisper small",
    )
    assert registry.models[2].source == str(local)


def test_model_keys_take_their_defaults(tmp_path):
    path = write(tmp_path, 'default = "a"\n[models.a]\nsource = "large-v3"\n')

    assert load_registry(path).default == ModelSpec(
        name="a",
        source="large-v3",
        compute_type="float16",
        batch_size=16,
        description="",
    )


@pytest.mark.parametrize("name", ["models.toml", "models.dev.toml"])
def test_the_shipped_files_are_valid(name):
    registry = load_registry(HERE / name)

    assert registry.default in registry.models


def test_get_none_returns_the_default(tmp_path):
    path = write(
        tmp_path,
        'default = "b"\n[models.a]\nsource = "small"\n[models.b]\nsource = "large-v3"\n',
    )
    registry = load_registry(path)

    assert registry.get(None) is registry.default
    assert registry.get("a").source == "small"


def test_get_an_unknown_name_returns_none(tmp_path):
    path = write(tmp_path, 'default = "a"\n[models.a]\nsource = "small"\n')

    assert load_registry(path).get("medium") is None


@pytest.mark.parametrize(
    "text, message",
    [
        (
            'default = "a"\nextra = 1\n[models.a]\nsource = "small"\n',
            "extra",
        ),
        (
            'default = "a"\n[models.a]\nsource = "small"\ndevice = "cpu"\n',
            "device",
        ),
        ('default = "a"\n[models.a]\ncompute_type = "int8"\n', "source"),
        ('default = "A"\n[models.A]\nsource = "small"\n', "A"),
        ('default = "a"\n[models.a]\nsource = "/does/not/exist"\n', "a"),
        ('default = "b"\n[models.a]\nsource = "small"\n', "default"),
        ('default = "a"\nmodels = {}\n', "models"),
    ],
    ids=[
        "unknown top-level key",
        "unknown model key",
        "missing source",
        "invalid name",
        "missing local directory",
        "default not in models",
        "no models",
    ],
)
def test_an_invalid_file_raises(tmp_path, text, message):
    with pytest.raises(RegistryError, match=message):
        load_registry(write(tmp_path, text))
