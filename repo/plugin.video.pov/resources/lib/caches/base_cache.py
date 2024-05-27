import time
from datetime import datetime
from modules.kodi_utils import database
#from modules.kodi_utils import logger

class BaseCache:
	db_file = ':memory:'

	def __init__(self):
		self.dbcon = database.connect(self.db_file, isolation_level=None)
		self.dbcur = self.dbcon.cursor()
		self._set_PRAGMAS()

	def _set_PRAGMAS(self):
		self.dbcur.execute('''PRAGMA synchronous = OFF''')
		self.dbcur.execute('''PRAGMA journal_mode = OFF''')

	def _get_timestamp(self, date_time):
		return int(time.mktime(date_time.timetuple()))

