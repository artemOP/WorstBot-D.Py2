from __future__ import annotations

import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import Bot


class QueueHandler(logging.Handler):
    def __init__(self, **kwargs):
        print(kwargs)
        super().__init__(logging.ERROR)
        # self.bot = bot

    def emit(self, record: logging.LogRecord) -> None:
        # self.bot.logging_queue.put_nowait(record)
        ...
