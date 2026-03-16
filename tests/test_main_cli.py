import sys
from pathlib import Path
from types import SimpleNamespace
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

rgw_cli_contract = types.ModuleType("rgw_cli_contract")
rgw_cli_contract.AppSpec = lambda **kwargs: SimpleNamespace(**kwargs)
rgw_cli_contract.resolve_install_script_path = lambda _path: Path("install.sh")


def _run_app(_spec, args, dispatch):
    return dispatch(args)


rgw_cli_contract.run_app = _run_app
sys.modules.setdefault("rgw_cli_contract", rgw_cli_contract)

import main


def test_build_terminal_launch_command_uses_double_dash_for_xdg_terminal_exec():
    command = main._build_terminal_launch_command(
        ["xdg-terminal-exec"],
        ["vim", "/tmp/test.md"],
    )

    assert command == ["xdg-terminal-exec", "--", "vim", "/tmp/test.md"]


def test_build_terminal_launch_command_uses_dash_e_for_regular_terminals():
    command = main._build_terminal_launch_command(
        ["alacritty"],
        ["vim", "/tmp/test.md"],
    )

    assert command == ["alacritty", "-e", "vim", "/tmp/test.md"]


def test_dispatch_opens_positional_file_detached(monkeypatch, tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("hello\n", encoding="utf-8")

    opened = []

    monkeypatch.setattr(
        main,
        "_open_file_detached",
        lambda path: (opened.append(path) or True, ""),
    )

    class FailOrchestrator:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("orchestrator should not start for file targets")

    monkeypatch.setattr(main, "Orchestrator", FailOrchestrator)

    result = main._dispatch([str(target)])

    assert result == 0
    assert opened == [str(target.resolve())]


def test_dispatch_opens_multiple_positional_files_detached(monkeypatch, tmp_path):
    first = tmp_path / "one.bin"
    second = tmp_path / "two.bin"
    first.write_text("one\n", encoding="utf-8")
    second.write_text("two\n", encoding="utf-8")

    opened = []

    def fake_open(path):
        opened.append(path)
        return True, ""

    monkeypatch.setattr(main, "_open_file_detached", fake_open)

    class FailOrchestrator:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("orchestrator should not start for file targets")

    monkeypatch.setattr(main, "Orchestrator", FailOrchestrator)

    result = main._dispatch([str(first), str(second)])

    assert result == 0
    assert opened == [str(first.resolve()), str(second.resolve())]


def test_dispatch_opens_multiple_text_files_in_internal_vim(monkeypatch, tmp_path):
    first = tmp_path / "one.md"
    second = tmp_path / "two.py"
    first.write_text("# one\n", encoding="utf-8")
    second.write_text("print('two')\n", encoding="utf-8")

    launched = []

    monkeypatch.setattr(
        main.shutil,
        "which",
        lambda name: "/usr/bin/vim" if name == "vim" else None,
    )
    monkeypatch.setattr(
        main.config,
        "USER_CONFIG",
        SimpleNamespace(
            get_handler_spec=lambda _name: main.config.HandlerSpec(
                commands=[],
                is_internal=False,
            )
        ),
        raising=False,
    )
    monkeypatch.setattr(
        main.subprocess,
        "call",
        lambda argv: launched.append(list(argv)) or 0,
    )
    monkeypatch.setattr(
        main,
        "_open_file_detached",
        lambda _path: (_ for _ in ()).throw(
            AssertionError("detached open should not be used for multi-file vim")
        ),
    )

    result = main._dispatch([str(first), str(second)])

    assert result == 0
    assert launched == [["vim", str(first.resolve()), str(second.resolve())]]


def test_dispatch_rejects_non_file_multi_target(monkeypatch, tmp_path, capsys):
    target = tmp_path / "note.txt"
    target.write_text("hello\n", encoding="utf-8")
    folder = tmp_path / "docs"
    folder.mkdir()

    class FailOrchestrator:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError(
                "orchestrator should not start for invalid multi-target input"
            )

    monkeypatch.setattr(main, "Orchestrator", FailOrchestrator)

    result = main._dispatch([str(target), str(folder)])
    captured = capsys.readouterr()

    assert result == 1
    assert "Multiple positional targets must all be files" in captured.err


def test_open_file_detached_uses_terminal_for_editor(monkeypatch, tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("hello\n", encoding="utf-8")

    launches = []

    def fake_launch(command, *, cwd=None, env=None):
        launches.append((list(command), cwd))
        return True

    monkeypatch.setattr(main, "_launch_terminal_command", fake_launch)
    monkeypatch.setattr(
        main.config,
        "USER_CONFIG",
        SimpleNamespace(
            get_handler_spec=lambda name: (
                main.config.HandlerSpec(commands=[["nvim"]], is_internal=False)
                if name == "editor"
                else main.config.HandlerSpec(commands=[], is_internal=False)
            )
        ),
        raising=False,
    )

    assert main._open_file_detached(str(target)) == (True, "")
    assert launches == [(["nvim", str(target)], str(tmp_path))]
