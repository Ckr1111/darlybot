"""Bridge between the Lopebot web application and DJMAX RESPECT V."""

from .navigator import NavigationPlan, SongNavigator
from .controller import DJMaxController

try:  # pragma: no cover - optional dependency (aiohttp)
    from .server import create_app
except ModuleNotFoundError:  # pragma: no cover
    create_app = None  # type: ignore

__all__ = [
    "SongNavigator",
    "NavigationPlan",
    "DJMaxController",
    "create_app",
]
