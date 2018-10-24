:: put your python path
SET pythonpath=C:\Users\quentin.royer\AppData\Local\Programs\Python\Python36

:: if build folder exist, remove it
if exist build rmdir /Q /S build

:: cx_Freeze
%pythonpath%\python.exe executable.py build

:: copy folders
robocopy biology build\exe.win-amd64-3.6\biology /E
robocopy doc build\exe.win-amd64-3.6\doc /E
robocopy model_hydro build\exe.win-amd64-3.6\model_hydro /E
robocopy translation build\exe.win-amd64-3.6\translation /E

:: create setup installer via isstudio
start "" /w "C:\Program Files (x86)\Inno Script Studio\isstudio.exe" -compile set_up3.iss

ECHO executable and installer successfully created in ..\habby\build folder !!!!!!!!!!!!

:: Get console open to see details
@pause 
