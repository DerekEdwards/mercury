from logging import *
import sys

#for mac the platform value is what OS it is. For windows it is win32,
#for linux it's linux2.
if sys.platform.find("linux") == -1:
    from logging import critical, debug, error, info, warn

import logging.handlers
#logging.basicConfig(level=logging.DEBUG,
formatter = logging.Formatter('%(asctime)s %(name)-10s %(levelname)-8s %(pathname)s %(lineno)d %(process)d %(module)s ridecell_log %(message)s')

#the highest level so that console does not have other level messages - for easy visual debugging
logging.addLevelName(60, 'notice')
CONSOLE = 60

console = logging.StreamHandler()
console.setLevel(CONSOLE)
console.setFormatter(formatter)

logging.getLogger('').addHandler(console)

rootLogger = logging.getLogger('')
rootLogger.setLevel(logging.DEBUG)

if sys.platform.find("linux") == -1:
    syslog = logging.handlers.SysLogHandler()
else:
    syslog = logging.handlers.SysLogHandler("/dev/log")
syslog.setLevel(logging.DEBUG)
syslog.setFormatter(formatter)

logging.getLogger('').addHandler(syslog)

tripapi_logger = logging.getLogger('')
