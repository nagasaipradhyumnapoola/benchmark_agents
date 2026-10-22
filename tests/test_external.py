import pytest

from benchlab.benchmarks.external import (
    build_lm_eval_command,
    parse_lm_eval_results,
    run_inspect_starter,
)


def test_lm_eval_argv_and_scores(tmp_path):
    args = build_lm_eval_command("hf", "pretrained=gpt2", ["hellaswag"], tmp_path, limit=2)
    assert args[:3] == ["lm-eval", "run", "--model"]
    assert args[args.index("--tasks") + 1] == "hellaswag"
    result = parse_lm_eval_results(
        {
            "results": {"hellaswag": {"acc,none": 0.5, "acc_stderr,none": 0.1}},
            "versions": {"hellaswag": 1},
        }
    )
    assert result["metrics"]["hellaswag"]["acc,none"] == 0.5
    with pytest.raises(ValueError):
        parse_lm_eval_results({"results": {}})


@pytest.mark.asyncio
async def test_inspect_real_framework_mock_model(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCHLAB_ALLOW_HOST_PROCESS", "1")
    pytest.importorskip("inspect_ai")
    result = await run_inspect_starter("mockllm/model", tmp_path, allow_host_process=True)
    assert result["framework"] == "inspect-ai"
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_lm_eval_subprocess_result_artifact(tmp_path, monkeypatch):
    import os
    import sys

    from benchlab.benchmarks import external

    monkeypatch.setenv("BENCHLAB_ALLOW_HOST_PROCESS", "1")
    script = tmp_path / "fixture.py"
    script.write_text(
        "import json,sys\nfrom pathlib import Path\nout=Path(sys.argv[sys.argv.index('--output_path')+1]);out.mkdir(parents=True)\n(out/'results_fixture.json').write_text(json.dumps({'results':{'fixture':{'acc,none':0.25}},'versions':{'fixture':1}}))"
    )
    build = external.build_lm_eval_command
    monkeypatch.setattr(
        external,
        "build_lm_eval_command",
        lambda *args: [sys.executable, str(script), *build(*args)[2:]],
    )
    result = await external.run_lm_eval(
        "hf", "pretrained=fixture", ["fixture"], tmp_path / "run", allow_host_process=True, limit=2
    )
    assert result["metrics"]["fixture"]["acc,none"] == 0.25
    assert result["sample_limit"] == 2 and os.path.isfile(result["artifact"])
