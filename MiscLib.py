import time
import getpass
import datetime
import hashlib

DEBUG_LOG_ENABLE = True
LOG_DEBUG        = False
LOG_INFO         = False

OFFLINE          = 'Offline'
ONLINE           = 'Online'

if DEBUG_LOG_ENABLE == True:
    def DebugLog(level, message):
        if level:
            print('[{0}] {1}'.format(time.ctime(), message))
else:
    def DebugLog(level, message):
        pass

def GetActiveUser():
    return getpass.getuser()

def GetCurrentDateTime():
    now = datetime.datetime.now()
    return now.strftime("%d/%m/%Y %H:%M:%S")

def GetMd5OfFile(file):
    with open(file, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)
    return file_hash.hexdigest()