from contextlib import contextmanager
from nodejs.npx import Popen
from os import getpgid, killpg
from os.path import exists, join
from requests_unixsocket import Session
from signal import SIGINT
from tempfile import TemporaryDirectory
from polling2 import poll

@contextmanager
def Evaluator():
	"""Create a JavaScript evaluator.

	This function returns a context manager. To use:

	    with Evaluator() as e:
	    	e.eval('return 6*7;')
	"""

	tmpDir = TemporaryDirectory('nodejs-eval')
	try:
		sockName = join(tmpDir.name, 'http.sock')
		escaped = sockName.replace('/', '%2F')
		sockUrl = f'http+unix://{escaped}/run'

		p = Popen(
			['http-eval', 'http-eval', '--udsPath', sockName],
			start_new_session=True)
		try:
			# Wait for the server to open the socket:
			poll(lambda: exists(sockName), timeout=5, step=0.1)

			with Session() as session:
				yield _Evaluator(session, sockUrl)
		finally:
			pgrp = getpgid(p.pid)
			killpg(pgrp, SIGINT)
			p.wait()
	finally:
		tmpDir.cleanup()

class _Evaluator:
	def __init__(self, session, sockUrl):
		self.__session = session
		self.__sockUrl = sockUrl

	def eval(self, cmd, isAsync=False):
		res = self.__session.post(
			self.__sockUrl,
			json={'code': cmd},
			params={'async': str(isAsync).lower()})
		j = res.json()

		if 'error' in j:
			raise RuntimeError(f"Error evaluating JavaScript: {j['error']}")

		return j['result']
