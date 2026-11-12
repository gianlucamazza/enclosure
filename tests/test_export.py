from enclosure.export import sanitize


def test_nested_tokens_removed_from_free_text_and_errors():
    source = {
        "metadata": {"token": "synthetic-secret"},
        "events": [
            {"message": "error synthetic-secret Bearer abc123 user@example.org /home/alice/repo"}
        ],
        "sample": "grid.T2",
    }
    result = sanitize(source)
    text = str(result)
    assert all(
        s not in text for s in ["synthetic-secret", "abc123", "user@example.org", "/home/alice"]
    )
    assert result["sample"] == "grid.T2"
    assert source["metadata"]["token"] == "synthetic-secret"


def test_token_usage_and_limits_are_preserved():
    assert sanitize({"input_tokens": 100, "max_tokens": 512, "api_key": "secret"}) == {
        "input_tokens": 100,
        "max_tokens": 512,
        "api_key": "[REDACTED]",
    }


def test_prefixed_api_keys_and_custom_workspace_paths_are_removed():
    source = {
        "metadata": {"DEEPSEEK_API_KEY": "synthetic-prefixed-secret"},
        "error": "synthetic-prefixed-secret /srv/private/repo/evals/wire.py",
    }
    result = sanitize(source, private_paths=("/srv/private/repo",))
    assert "synthetic-prefixed-secret" not in str(result)
    assert "/srv/private/repo" not in str(result)
