import os
import json
import urllib
import base64
import artifactory
from MiscLib import *

class ArtifactoryManager:
    def __init__(self, repository, username, password):
        self.repository             = repository
        self.username               = username
        self.password               = password
        self.server_previous_status = OFFLINE
        self.server_current_status  = OFFLINE

    def IsStatusChanged(self):
        return self.server_current_status != self.server_previous_status

    def GetCurrentStatus(self):
        return self.server_current_status

    def IsServerUp(self):
        try:
            req =  urllib.request.Request(self.repository)
            base64string = base64.b64encode(bytes('{}:{}'.format(self.username, self.password), 'ascii'))
            req.add_header('Authorization', 'Basic {}'.format(base64string.decode('utf-8')))
            resp = urllib.request.urlopen(req)
            status = (resp.getcode() == 200)
        except urllib.error.HTTPError as ex:
            status = False
            if ex.code == 401: # authentication error
                DebugLog(LOG_DEBUG, ex.msg)
        except urllib.error.URLError as ex: # No internet
            status = False
        except:
            status = False

        self.server_previous_status = self.server_current_status
        if status:
            self.server_current_status = ONLINE
        else:
            self.server_current_status = OFFLINE

        return status

    def UploadFile(self, file_name):
        if not self.IsServerUp():
            return False
        path = artifactory.ArtifactoryPath(self.repository, auth=(self.username, self.password))
        try:
            path.mkdir()
        except OSError:
            pass
        path.deploy_file(file_name)
        DebugLog(LOG_INFO, 'Uploaded {}'.format(file_name))
        return True

    def DownloadFile(self, file_name):
        if not self.IsServerUp():
            return False
        try:
            artifactory_full_path = '{0}/{1}'.format(self.repository, file_name)
            path = artifactory.ArtifactoryPath(artifactory_full_path, auth=(self.username, self.password))
            with path.open() as fd:
                with open(file_name, "wb") as out:
                    out.write(fd.read())
                DebugLog(LOG_INFO, 'Downloaded {}'.format(artifactory_full_path))
            status = True
        except RuntimeError as ex:
            status = False
        except:
            status = False
        return status

    def FetchResourceList(self, json_file_name):
        resource_list = {}
        status = self.DownloadFile(json_file_name)
        if status:
            with open(json_file_name, "r") as json_file:
                resource_list = json.load(json_file)
                json_file.close()
        return resource_list