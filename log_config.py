import logging
from datetime import datetime
import sys
import os
from logging.handlers import RotatingFileHandler
formatter = logging.Formatter(
    '%(threadName)s | %(asctime)s | %(levelname)-8s | %(message)s')
log = logging.getLogger('log')
log.setLevel(logging.DEBUG)
mainlog_filename = datetime.now().strftime('Log/log_%d_%m_%Y.log')
os.makedirs('Log', exist_ok=True)
mainLogFile_handler = RotatingFileHandler(mainlog_filename, mode='a', maxBytes=52428800,
                                                           backupCount=10, encoding=None, delay=False,
                                                           errors=None)
mainLogFile_handler.setFormatter(formatter)
mainLogPrinting = logging.StreamHandler(sys.stdout)
log.addHandler(mainLogFile_handler)
log.addHandler(mainLogPrinting)
