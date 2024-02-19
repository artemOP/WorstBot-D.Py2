import asyncio
import logging


class QueueHandler(logging.Handler):
    queue: asyncio.Queue

    def __init__(self, **kwargs):
        super().__init__(level=kwargs.get("level", logging.ERROR))

    def emit(self, record: logging.LogRecord) -> None:
        # self.bot.logging_queue.put_nowait(record)
        if not self.queue:
            raise ValueError("Queue has not been passed to handler yet")  # todo: raise custom error

        self.queue.put_nowait(record)
