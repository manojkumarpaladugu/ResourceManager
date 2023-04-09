import customtkinter
import subprocess
from MiscLib import *

class ResourceFrame(customtkinter.CTkFrame):
    def __init__(self, ui, setup, category, resource, **kwargs):
        super().__init__(ui.vertical_scrollable_frame, fg_color='white', **kwargs)

        self.main_frame           = self
        self.gui                   = ui
        self.setup                = setup
        self.resource_category    = category
        self.resource             = resource
        self.resource_name        = "{0} - {1}".format(self.setup, self.resource_category)
        self.resource_ip          = self.resource['IP Address']
        self.resource_username    = self.resource['Username']
        self.resource_password    = self.resource['Password']
        self.resource_status      = self.resource['Status']
        self.active_user          = GetActiveUser()
        self.resource_thread      = None
        self.pop_up_window        = None
        self.timestamp            = ''

        self.resource_open_button = customtkinter.CTkButton(self, text=self.resource_name, command=self.OpenButtonCallback)
        self.resource_open_button.grid(row=0, column=0, padx=10, pady=10)

        self.resource_unlock_button = customtkinter.CTkButton(self, text='Unlock', command=self.UnlockButtonCallback, width=50)
        self.resource_unlock_button.grid(row=1, column=0, padx=10, pady=10)

        self.resource_status_label = customtkinter.CTkLabel(self, text='Status: Unknown')
        self.resource_status_label.grid(row=2, column=0, padx=5, pady=5)

        self.label_ip = customtkinter.CTkLabel(self, text="IP: {}".format(self.resource_ip))
        self.label_ip.grid(row=3, column=0, padx=1, pady=1)

        self.label_username = customtkinter.CTkLabel(self, text="Username: {}".format(self.resource_username), width=300)
        self.label_username.grid(row=4, column=0, padx=1, pady=1)

        self.label_password = customtkinter.CTkLabel(self, text="Password: {}".format(self.resource_password))
        self.label_password.grid(row=5, column=0, padx=1, pady=1)

        self.UpdateToUi()

    def UpdateToUi(self):
        if self.resource_status == 'Busy':
            self.active_user = GetActiveUser()
            message = 'User: {0} since {1}'.format(self.active_user, self.timestamp)
            status_color = 'red'
            open_button_state = customtkinter.DISABLED
            open_button_color = 'gray'
            unlock_button_state = customtkinter.NORMAL
            unlock_button_color = '#3a7ebf'
        elif self.resource_status == 'Available':
            self.active_user = ''
            message = 'Status: {}'.format(self.resource_status)
            status_color = 'green'
            open_button_state = customtkinter.NORMAL
            open_button_color = '#3a7ebf'
            unlock_button_state = customtkinter.DISABLED
            unlock_button_color = 'gray'
        else:
            self.active_user = ''
            message = 'Status: Unknown'
            status_color = 'black'
            open_button_state = customtkinter.NORMAL
            open_button_color = '#3a7ebf'
            unlock_button_state = customtkinter.DISABLED
            unlock_button_color = 'gray'

        self.resource_status_label.configure(text=message, text_color=status_color)
        self.resource_open_button.configure(fg_color=open_button_color, state=open_button_state)
        self.resource_unlock_button.configure(fg_color=unlock_button_color, state=unlock_button_state)
        DebugLog(LOG_DEBUG, 'Updated resource frame {}'.format(self.resource_name))

    def OpenPopUpWindow(self):
        self.pop_up_window = customtkinter.CTkToplevel(self.main_frame)
        self.pop_up_window.geometry('300x55')
        self.pop_up_window.title("Error")
        self.pop_up_window.resizable(False, False)
        label = customtkinter.CTkLabel(self.pop_up_window, text='Your RDP session is already in open!')
        label.pack(padx=20, pady=20)
        x = self.main_frame.winfo_x()
        y = self.main_frame.winfo_y()
        self.pop_up_window.geometry("+%d+%d" %(x,y))
        self.pop_up_window.wm_transient(self.main_frame)   # Keep the toplevel window in front of the root window
        self.pop_up_window.grab_set()

    def OpenButtonCallback(self):
        if (self.resource_thread is not None) and (self.resource_thread.is_alive()):
            self.gui.resource_manager.fiber_scheduler.DeactivateFiber(self.gui.resource_manager.TimerCallback)
            self.resource_status = 'Busy'
            self.UpdateToUi()
            self.gui.resource_manager.fiber_scheduler.ActivateFiber(self.gui.resource_manager.TimerCallback)
            self.OpenPopUpWindow() # Already RDP is running
            return
        # submit the request to create RDP session
        self.gui.resource_manager.create_rdp_request_queue.put(self)

    def UnlockButtonCallback(self):
        self.gui.resource_manager.fiber_scheduler.DeactivateFiber(self.gui.resource_manager.TimerCallback)
        self.resource_status = 'Available'
        self.UpdateToUi()
        self.gui.resource_manager.fiber_scheduler.ActivateFiber(self.gui.resource_manager.TimerCallback)

class UserInterface(customtkinter.CTk):
    def __init__(self, resource_manager):
        super().__init__()

        self.SCROLLABLE_FRAME_HEIGHT = 520
        self.SCROLLABLE_FRAME_WIDTH  = 680
        self.resource_frame_list = []
        self.resource_manager = resource_manager
        self.resource_manager.gui = self
        self.resource_frame_count = 0

        customtkinter.set_appearance_mode('light') # system (default), dark, light
        customtkinter.set_default_color_theme('blue')  # Themes: "blue" (standard), "green", "dark-blue"
        self.title(self.resource_manager.APPLICATION_NAME)
        self.resizable(False, False)

        self.static_frame = customtkinter.CTkFrame(self,
                                                   width=self.SCROLLABLE_FRAME_WIDTH,
                                                   height=30,
                                                   corner_radius=5,
                                                   fg_color='white',
                                                   bg_color='white')
        self.static_frame.grid(row=0, column=0, sticky="ns")

        self.app_status_label = customtkinter.CTkLabel(self.static_frame,
                                                       width=337,
                                                       text='Status: Unknwon',
                                                       corner_radius=5,
                                                       fg_color='white',
                                                       font=customtkinter.CTkFont(weight='bold'))
        self.app_status_label.grid(row=0, column=0, padx=5, pady=5, sticky = customtkinter.W+customtkinter.E)

        self.update_resource_config_button = customtkinter.CTkButton(self.static_frame,
                                                                     width=337,
                                                                     text='Update {}'.format(self.resource_manager.RESOURCE_CONFIG_JSON),
                                                                     text_color='white',
                                                                     fg_color='#3a7ebf',
                                                                     command=self.UpdateResourceConfigButton)
        self.update_resource_config_button.grid(row=0, column=1, padx=5, pady=5, sticky = customtkinter.W+customtkinter.E)

        self.vertical_scrollable_frame = customtkinter.CTkScrollableFrame(self,
                                                                          width=self.SCROLLABLE_FRAME_WIDTH,
                                                                          height=self.SCROLLABLE_FRAME_HEIGHT,
                                                                          corner_radius=0,
                                                                          fg_color='#46555b',
                                                                          scrollbar_button_color='#7d888c',
                                                                          scrollbar_button_hover_color='#b5bbbd',
                                                                          orientation='vertical')
        self.vertical_scrollable_frame.grid(row=1, column=0, sticky="ns")

        self.AddResourceFrames()

        self.bind('<FocusIn>', self.HandleFocusIn)
        self.bind('<FocusOut>', self.HandleFocusOut)

    def RemoveResourceFrames(self):
        for resource_frame in self.resource_frame_list:
            resource_frame.grid_remove()
        self.resource_frame_list = []
        self.resource_frame_count = 0
        self.app_status_label.configure(text='Status: Offline', text_color='red')
        self.update_resource_config_button.configure(state=customtkinter.DISABLED, fg_color='gray')

    def AddResourceFrames(self, resource_list=dict()):
        row_num = 0
        if not len(resource_list):
            resource_list = self.resource_manager.artifactory_manager.FetchResourceList(self.resource_manager.RESOURCE_CONFIG_JSON)
        for setup in resource_list:
            col_num = 0
            for category in resource_list[setup]:
                resource_frame = ResourceFrame(self,
                                               setup,
                                               category,
                                               resource_list[setup][category])
                resource_frame.grid(row=row_num, column=col_num, padx=20, pady=20)
                self.resource_frame_list.append(resource_frame)
                self.resource_frame_count += 1
                col_num += 1
            row_num += 1
            self.app_status_label.configure(text='Status: Online', text_color='green')
            self.update_resource_config_button.configure(state=customtkinter.NORMAL, fg_color='#3a7ebf')

    def UpdateResourceConfigButton(self):
        self.resource_manager.fiber_scheduler.DeactivateFiber(self.resource_manager.TimerCallback)
        md5_before_file_update = GetMd5OfFile(self.resource_manager.RESOURCE_CONFIG_JSON)
        command = 'notepad.exe {}'.format(self.resource_manager.RESOURCE_CONFIG_JSON)
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        md5_after_file_update = GetMd5OfFile(self.resource_manager.RESOURCE_CONFIG_JSON)
        if md5_after_file_update != md5_before_file_update:
            self.resource_manager.UploadFile(self.resource_manager.RESOURCE_CONFIG_JSON)
            self.RemoveResourceFrames()
            self.AddResourceFrames()
        self.resource_manager.fiber_scheduler.ActivateFiber(self.resource_manager.TimerCallback)

    def HandleFocusIn(self, event):
        DebugLog(LOG_DEBUG, 'I have focus')
        self.resource_manager.fiber_scheduler.Resume()

    def HandleFocusOut(self, event):
        DebugLog(LOG_DEBUG, "I DON'T have focus")
        self.resource_manager.fiber_scheduler.Stop()