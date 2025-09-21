from darlybot.input_controller import DJMaxInputController
from darlybot.song_index import SCROLL_DOWN_KEY, SCROLL_UP_KEY


class _FakeKey:
    page_up = object()
    page_down = object()


class _FakeKeyCode:
    @staticmethod
    def from_char(char: str) -> str:
        return f"char:{char}"


class _FakeKeyboardModule:
    Key = _FakeKey
    KeyCode = _FakeKeyCode


class _FakeKeyboardController:
    def __init__(self) -> None:
        self.tapped: list[str | object] = []

    def tap(self, key: str | object) -> None:
        self.tapped.append(key)


class _FakeMouseController:
    def __init__(self) -> None:
        self.scroll_events: list[tuple[int, int]] = []

    def scroll(self, dx: int, dy: int) -> None:
        self.scroll_events.append((dx, dy))


def test_send_keys_translates_special_keys() -> None:
    controller = DJMaxInputController(key_delay=0.0)
    controller._keyboard_module = _FakeKeyboardModule()  # type: ignore[attr-defined]
    controller._keyboard_controller = _FakeKeyboardController()  # type: ignore[attr-defined]
    controller._mouse_controller = _FakeMouseController()  # type: ignore[attr-defined]

    controller.send_keys(["a", "pageup", SCROLL_DOWN_KEY, SCROLL_UP_KEY])

    keyboard = controller._keyboard_controller  # type: ignore[attr-defined]
    mouse = controller._mouse_controller  # type: ignore[attr-defined]

    assert keyboard.tapped == ["char:a", _FakeKey.page_up]
    assert mouse.scroll_events == [(0, -1), (0, 1)]
