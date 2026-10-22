from benchlab.settings import redact


def test_nested_credentials_and_environment_echo_are_redacted(monkeypatch):
    monkeypatch.setenv("MY_API_KEY", "private-provider-value")
    original = {
        "api_key": "sensitive",
        "api_key_env": "MY_API_KEY",
        "events": [
            {"output": "private-provider-value sk-abcdefgh1234", "Authorization": "Bearer a"}
        ],
    }
    value = redact(original)
    assert value["api_key"] == "[REDACTED]"
    assert value["api_key_env"] == "MY_API_KEY"
    assert "private-provider-value" not in str(value)
    assert "sk-abcdefgh1234" not in str(value)
    assert original["api_key"] == "sensitive"
