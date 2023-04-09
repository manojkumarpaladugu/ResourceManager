import subprocess
import functools
import threading
import json
import threading
import time
import queue
import ArtifactoryManager
import FiberScheduler
import UserInterface
from MiscLib import *

class ResourceManager:
    def __init__(self):
        with open('ResourceManager.ini', "r") as resource_manager_ini_file:
            for line in resource_manager_ini_file:
                line = line.replace('\n', '')
                if line == 'Variables:' or line == '----------':
                    continue
                lhs = line.split(' = ')[0].replace(' ', '')
                rhs = line.split(' = ')[1]
                exec("self.{0} = {1}".format(lhs, rhs))

        self.WAIT_TIME_SECONDS = 5

        self.artifactory_server_status_queue = queue.Queue()
        self.create_rdp_request_queue = queue.Queue()

        self.artifactory_server_prev_status = OFFLINE
        self.artifactory_manager = ArtifactoryManager.ArtifactoryManager(repository=self.ARTIFACTORY_REPOSITORY,
                                                                         username=self.ARTIFACTORY_USERNAME,
                                                                         password=self.ARTIFACTORY_PASSWORD)
        self.fiber_scheduler = FiberScheduler.FiberScheduler()
        self.gui = UserInterface.UserInterface(self)
        self.sync_lock = False

    def WaitOnLock(self):
        while(self.sync_lock):
            pass

    def UpdateToJson(self, resource_frame):
        if resource_frame.resource_status == 'Busy':
            resource_frame.active_user = GetActiveUser()
        elif resource_frame.resource_status == 'Available':
            resource_frame.active_user = ''

        resource_list = self.artifactory_manager.FetchResourceList(self.RESOURCE_CONFIG_JSON)
        with open(self.RESOURCE_CONFIG_JSON, "w") as json_file:
            resource_list[resource_frame.setup][resource_frame.resource_category]['Status'] = resource_frame.resource_status
            resource_list[resource_frame.setup][resource_frame.resource_category]['Active User'] = resource_frame.active_user
            resource_list[resource_frame.setup][resource_frame.resource_category]['Timestamp'] = resource_frame.timestamp
            json.dump(resource_list, json_file, indent=4)
            json_file.close()
            status = self.artifactory_manager.UploadFile(self.RESOURCE_CONFIG_JSON)

    def CreateRdpSession(self, resource_frame):
        self.WaitOnLock()
        self.sync_lock = True
        self.fiber_scheduler.DeactivateFiber(self.TimerCallback)
        resource_frame.resource_status = 'Busy'
        resource_frame.timestamp = GetCurrentDateTime()
        resource_frame.UpdateToUi()
        self.UpdateToJson(resource_frame)
        self.fiber_scheduler.ActivateFiber(self.TimerCallback)
        self.sync_lock = False

        command = 'cmdkey /generic:"{0}" /user:"{1}" /pass:"{2}"'.format(resource_frame.resource_ip,
                                                                            resource_frame.resource_username,
                                                                            resource_frame.resource_password)
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)

        DebugLog(LOG_DEBUG, 'Launching RDP session for {}'.format(resource_frame.resource_name))
        command = 'mstsc /v:{}'.format(resource_frame.resource_ip)
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        DebugLog(LOG_DEBUG, 'RDP session ended for {}'.format(resource_frame.resource_name))

        command = 'cmdkey /delete LegacyGeneric:target={}'.format(resource_frame.resource_ip)
        subprocess.run(command, check=False, stdout=subprocess.DEVNULL)

        self.WaitOnLock()
        self.sync_lock = True
        self.fiber_scheduler.DeactivateFiber(self.TimerCallback)
        resource_frame.resource_status = 'Available'
        resource_frame.timestamp = ''
        resource_frame.UpdateToUi()
        self.UpdateToJson(resource_frame)
        self.fiber_scheduler.ActivateFiber(self.TimerCallback)
        self.sync_lock = False

    def HandleCreateRdpRequestQueue(self):
        DebugLog(LOG_DEBUG, 'HandleCreateRdpRequestQueue entry {}'.format(time.ctime()))
        if self.create_rdp_request_queue.empty():
            return
        resource_frame = self.create_rdp_request_queue.get()
        self.create_rdp_request_queue.task_done()
        resource_frame.resource_thread = threading.Thread(target=functools.partial(self.CreateRdpSession, resource_frame))
        resource_frame.resource_thread.start()

    def HandleArtifactoryServerStatusQueue(self):
        DebugLog(LOG_DEBUG, 'HandleArtifactoryServerStatusQueue entry {}'.format(time.ctime()))
        if self.artifactory_server_status_queue.empty():
            return
        status_msg = self.artifactory_server_status_queue.get()
        self.artifactory_server_status_queue.task_done()
        if status_msg == 'Online':
            self.gui.RemoveResourceFrames()
            self.gui.AddResourceFrames()
        elif status_msg == 'Offline':
            self.gui.RemoveResourceFrames()

    def TimerCallback(self):
        DebugLog(LOG_DEBUG, 'TimerCallback triggered {}'.format(time.ctime()))
        resource_list = self.artifactory_manager.FetchResourceList(self.RESOURCE_CONFIG_JSON)

        if self.artifactory_manager.IsStatusChanged():
            self.artifactory_server_status_queue.put(self.artifactory_manager.GetCurrentStatus())
            return

        if self.gui.resource_frame_count != len(resource_list) * 2:
            self.gui.RemoveResourceFrames()
            self.gui.AddResourceFrames(resource_list)

        for resource_frame in self.gui.resource_frame_list:
            try:
                resource_status = resource_list[resource_frame.setup][resource_frame.resource_category]['Status']
                if resource_status == resource_frame.resource_status:
                    continue
                resource_frame.active_user = resource_list[resource_frame.setup][resource_frame.resource_category]['Active User']
                resource_frame.timestamp   = resource_list[resource_frame.setup][resource_frame.resource_category]['Timestamp']
                resource_frame.resource_status = resource_status
                resource_frame.UpdateToUi()
            except KeyError:
                break

    def RunMainLoop(self):
        self.fiber_scheduler.RegisterFiber(fiber=self.HandleCreateRdpRequestQueue, activation_status=True)
        self.fiber_scheduler.RegisterFiber(fiber=self.HandleArtifactoryServerStatusQueue, activation_status=True)
        self.fiber_scheduler.RegisterFiber(fiber=self.TimerCallback, interval=self.WAIT_TIME_SECONDS, activation_status=True)
        self.fiber_scheduler.Run()
        self.gui.mainloop()
        self.fiber_scheduler.Stop()

if __name__ == "__main__":
    rm = ResourceManager()
    rm.RunMainLoop()