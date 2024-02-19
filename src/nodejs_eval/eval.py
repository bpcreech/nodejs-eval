from aiohttp import ClientSession, UnixConnector
from asyncio import sleep
from contextlib import asynccontextmanager
from nodejs.npx import Popen
from os import getpgid, killpg
from os.path import exists, join
from signal import SIGINT
from tempfile import TemporaryDirectory
from time import time


async def _poll(checker, step, timeout):
	start = time()
	while True:
		if checker():
			return

		if time() - start > timeout:
			raise RuntimeError('Timed out')

		await sleep(step)

@asynccontextmanager
async def Evaluator():
	"""Create a JavaScript evaluator.

	This function returns an async context manager. To use:

	    async with Evaluator() as e:
	    	await e.eval('return 6*7;')
	"""

	tmpDir = TemporaryDirectory('nodejs-eval')
	try:
		sockName = join(tmpDir.name, 'http.sock')

		p = Popen(
			['http-eval', 'http-eval', '--udsPath', sockName],
			start_new_session=True)
		try:
			# Wait for the server to open the socket:
			await _poll(lambda: exists(sockName), timeout=5, step=0.1)

			async with UnixConnector(path=sockName) as conn:
				async with ClientSession(connector=conn) as session:
					yield _Evaluator(session)
		finally:
			# npx creates subprocesses. If we just interrupt our child,
			# subprocesses will remain behind. Instead we interrupt the whole
			# process group:
			pgrp = getpgid(p.pid)
			killpg(pgrp, SIGINT)
			p.wait()
	finally:
		tmpDir.cleanup()

class _Evaluator:
	def __init__(self, session):
		self.__session = session

	async def eval(self, cmd, isAsync=False):
		async with self.__session.post(
				'http://bogus/run',
				json={'code': cmd},
				params={'async': str(isAsync).lower()}) as res:
			j = await res.json()

			if 'error' in j:
				raise RuntimeError(f"Error evaluating JavaScript: {j['error']}")

			return j['result']
