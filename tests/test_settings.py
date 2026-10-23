from benchlab.settings import Settings, environment_setting


def test_product_environment_wins_and_legacy_configuration_remains_compatible(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("BENCHLAB_DATA_DIR", str(tmp_path / "legacy"))
    monkeypatch.setenv("BENCHLAB_ALLOW_HOST_PROCESS", "1")
    monkeypatch.delenv("BENCH_AGENTS_DATA_DIR", raising=False)
    monkeypatch.delenv("BENCH_AGENTS_ALLOW_HOST_PROCESS", raising=False)
    assert Settings.from_env().data_dir == (tmp_path / "legacy").resolve()
    assert Settings.from_env().allow_host_process
    monkeypatch.setenv("BENCH_AGENTS_DATA_DIR", str(tmp_path / "new"))
    monkeypatch.setenv("BENCH_AGENTS_ALLOW_HOST_PROCESS", "0")
    assert Settings.from_env().data_dir == (tmp_path / "new").resolve()
    assert not Settings.from_env().allow_host_process
    assert environment_setting("MISSING_SETTING", "fallback") == "fallback"
