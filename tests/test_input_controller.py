import sys
import types

from darlybot.input_controller import DJMaxInputController


def test_page_key_aliases(monkeypatch):
    stub = types.SimpleNamespace()
    stub.pressed = []
    stub.scrolled = []

    def press(key: str) -> None:
        stub.pressed.append(key)

    def scroll(amount: int) -> None:
        stub.scrolled.append(amount)

    stub.press = press
    stub.scroll = scroll

    monkeypatch.setitem(sys.modules, "pyautogui", stub)

    controller = DJMaxInputController(key_delay=0)
    controller.send_keys(["pageup", "pagedown", "a"])

    assert stub.pressed == ["pgup", "pgdn", "a"]
    assert stub.scrolled == []
