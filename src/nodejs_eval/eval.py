from asyncio import sleep
from contextlib import asynccontextmanager
from os import getpgid, killpg
from os.path import exists, join
from signal import SIGINT
from tempfile import TemporaryDirectory
from time import time

from aiohttp import ClientSession, UnixConnector
from nodejs.npx import Popen


class JavaScriptError(Exception):
    def __init__(self, err):
        super(f"Error evaluating JavaScript: {err}")
        self.error = err


async def _poll(checker, step, timeout):
    start = time()
    while True:
        if checker():
            return

        if time() - start > timeout:
            raise TimeoutError

        await sleep(step)


@asynccontextmanager
async def evaluator():
    """Create a JavaScript evaluator.

    This function returns an async context manager. To use:

        async with evaluator() as e:
          await e.run('return 6*7;')
    """

    tmp_dir = TemporaryDirectory("nodejs-eval")
    try:
        sock_name = join(tmp_dir.name, "http.sock")

        p = Popen(["http-eval", "http-eval", "--udsPath", sock_name], start_new_session=True)
        try:
            # Wait for the server to open the socket:
            await _poll(lambda: exists(sock_name), timeout=5, step=0.1)

            async with UnixConnector(path=sock_name) as conn, ClientSession(connector=conn) as session:
                yield _Evaluator(session)
        finally:
            # npx creates subprocesses. If we just interrupt our child,
            # subprocesses will remain behind. Instead we interrupt the whole
            # process group:
            pgrp = getpgid(p.pid)
            killpg(pgrp, SIGINT)
            p.wait()
    finally:
        tmp_dir.cleanup()


class _Evaluator:
    def __init__(self, session):
        self.__session = session

    async def run(self, code):
        """Evaluate synchronous JavaScript code.

        The the given code will be run within an ECMAScript module, as
        a synchronous function body. (Note that on the Python side, this method
        always runs async, by construction.)

        Because the code is run as an ECMAScript module, to import other
        JavaScript modules, you must use the dynamic `await import()` operator
        (not a CommonJS `require()`). *This works better under runAsync().*

        Returns:
          The result of the JavaScript code execution, if any, as returned
          by the JavaScript "return" keyword. Note that the code must return
          a JSON-serializable (JSON.stringify'able) output.
        """

        return await self._run(code, is_async=False)

    async def run_async(self, code):
        """Evaluate asynchronous JavaScript code.

        The the given code will be run within an ECMAScript module, as
        an asynchronous function body.

        Because the code is run as an ECMAScript module, to import other
        JavaScript modules, you must use the dynamic `await import()` operator
        (not a CommonJS `require()`).

        Returns:
          The result of the JavaScript code execution, if any, as returned
          by the JavaScript "return" keyword. Note that the code must return
          a JSON-serializable (JSON.stringify'able) output.
        """

        return await self._run(code, is_async=True)

    async def _run(self, code, is_async):
        async with self.__session.post(
            "http://bogus/run", json={"code": code}, params={"async": str(is_async).lower()}
        ) as res:
            j = await res.json()

            if "error" in j:
                raise JavaScriptError(j["error"])

            return j.get("result")
