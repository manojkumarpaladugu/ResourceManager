# ResourceManager

Install below PIP packages:
    pip3 install customtkinter
    pip install artifactory==0.1.17
    pip uninstall pathlib

How to convert python script to Windows executable?
    pip3 install pyinstaller
    Open PowerShell window here
    copy pyinstaller path from the output of "pip3 show pyinstaller"
    pyinstaller --noconfirm --onefile --noconsole --add-data "c:\users\<username>\appdata\local\programs\python\python39\lib\site-packages\customtkinter;customtkinter\" 'ResourceManager.py'
    .exe will be in dist directory
