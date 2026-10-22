import pytest
from pydantic import ValidationError


def test_experiment_requires_systems_and_positive_budget():
    from benchlab.schemas import ExperimentConfig

    with pytest.raises(ValidationError):
        ExperimentConfig(name="invalid", systems=[], budget_seconds=0)


def test_endpoint_rejects_credentials_and_unsafe_schemes():
    from benchlab.schemas import ModelConfig

    for address in [
        "file:///etc/passwd",
        "http://user:password@localhost:8000",
        "https://api.example.com?key=secret",
    ]:
        with pytest.raises(ValidationError):
            ModelConfig(name="bad", adapter="openai-compatible", model="test", base_url=address)


def test_secret_reference_is_environment_variable_name():
    from benchlab.schemas import ModelConfig

    with pytest.raises(ValidationError):
        ModelConfig(name="bad", adapter="openai-compatible", model="test", api_key_env="sk-secret")
