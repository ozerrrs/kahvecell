"""Yerel saat (dükkân saat dilimi). Testlerde zamanı sabitlemek için tek noktadan alınır."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.shop_timezone))
