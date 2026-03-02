import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import HandlerSpec, UserConfig
from file_actions import FileActionService


def _make_nav() -> SimpleNamespace:
    config = UserConfig()
    renderer = SimpleNamespace(stdscr=None)
    dir_manager = SimpleNamespace(current_path=".")

    def _open_terminal(_base=None, _command=None):
        return False

    return SimpleNamespace(
        config=config,
        renderer=renderer,
        dir_manager=dir_manager,
        open_terminal=_open_terminal,
        status_message="",
        need_redraw=False,
    )


def test_invoke_handler_uses_internal_runner_when_flagged():
    nav = _make_nav()
    service = FileActionService(nav)

    spec = HandlerSpec(commands=[["vixl"]], is_internal=True)

    with (
        patch.object(
            service, "_run_internal_handler", return_value=True
        ) as mock_internal,
        patch.object(
            service, "_run_terminal_handlers", return_value=False
        ) as mock_terminal,
    ):
        result = service._invoke_handler(
            spec, "example.csv", default_strategy="terminal"
        )

    assert result is True
    mock_internal.assert_called_once()
    mock_terminal.assert_not_called()


def test_invoke_handler_delegates_to_terminal_when_external():
    nav = _make_nav()
    service = FileActionService(nav)

    spec = HandlerSpec(commands=[["vixl"]], is_internal=False)

    with (
        patch.object(
            service, "_run_terminal_handlers", return_value=True
        ) as mock_terminal,
        patch.object(
            service, "_run_internal_handler", return_value=False
        ) as mock_internal,
    ):
        result = service._invoke_handler(
            spec, "example.csv", default_strategy="terminal"
        )

    assert result is True
    mock_terminal.assert_called_once()
    mock_internal.assert_not_called()


def test_open_file_uses_audio_player_for_audio_files():
    nav = _make_nav()
    spec = HandlerSpec(commands=[["ffplay", "-nodisp", "-autoexit"]])
    nav.config.handlers["audio_player"] = spec
    service = FileActionService(nav)

    with (
        patch("file_actions.mimetypes.guess_type", return_value=("audio/mpeg", None)),
        patch.object(service, "_invoke_handler", return_value=True) as mock_invoke,
    ):
        service.open_file("song.mp3")

    mock_invoke.assert_called_once_with(
        spec,
        "song.mp3",
        default_strategy="external_background",
    )


def test_open_file_uses_media_player_for_video_files():
    nav = _make_nav()
    spec = HandlerSpec(commands=[["ffplay", "-autoexit"]])
    nav.config.handlers["video_player"] = spec
    service = FileActionService(nav)

    with (
        patch("file_actions.mimetypes.guess_type", return_value=("video/mp4", None)),
        patch.object(service, "_invoke_handler", return_value=True) as mock_invoke,
    ):
        service.open_file("clip.mp4")

    mock_invoke.assert_called_once_with(
        spec,
        "clip.mp4",
        default_strategy="external_background",
    )


def test_open_file_falls_back_to_media_player_for_audio():
    nav = _make_nav()
    spec = HandlerSpec(commands=[["mpv"]])
    nav.config.handlers["media_player"] = spec
    service = FileActionService(nav)

    with (
        patch("file_actions.mimetypes.guess_type", return_value=("audio/ogg", None)),
        patch.object(service, "_invoke_handler", return_value=True) as mock_invoke,
    ):
        service.open_file("song.ogg")

    mock_invoke.assert_called_once_with(
        spec,
        "song.ogg",
        default_strategy="external_background",
    )


def test_open_file_prefers_video_player_over_media_player():
    nav = _make_nav()
    media_spec = HandlerSpec(commands=[["mpv"]])
    video_spec = HandlerSpec(commands=[["vlc"]])
    nav.config.handlers["media_player"] = media_spec
    nav.config.handlers["video_player"] = video_spec
    service = FileActionService(nav)

    with (
        patch("file_actions.mimetypes.guess_type", return_value=("video/mp4", None)),
        patch.object(service, "_invoke_handler", return_value=True) as mock_invoke,
    ):
        service.open_file("clip.mp4")

    mock_invoke.assert_called_once_with(
        video_spec,
        "clip.mp4",
        default_strategy="external_background",
    )
