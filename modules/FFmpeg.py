import discord
import logging
from io import BufferedIOBase


class FFmpegPCMAudio(discord.FFmpegPCMAudio):
    _log = logging.getLogger("discord.player")
    _log.setLevel(logging.ERROR)

    # def __init__(self, source, *, executable: str = None, pipe: bool = False, stderr: bool = None, before_options: str = None, options: str = None, **kwargs):
    #     super().__init__(source, executable = executable, pipe = pipe, stderr = stderr, before_options = before_options, options = options, **kwargs)

    def _pipe_writer(self, source: BufferedIOBase) -> None:
        while self._process:
            # arbitrarily large read size
            data = source.read(8192)
            if not data:
                self._stdin.close()
                self._process.wait(timeout=10)
                return
            try:
                if self._stdin is not None:
                    self._stdin.write(data)
            except Exception:
                self._log.debug("Write error for %s, this is probably not a problem", self, exc_info=True)
                # at this point the source data is either exhausted or the process is fubar
                self._process.terminate()
                return
