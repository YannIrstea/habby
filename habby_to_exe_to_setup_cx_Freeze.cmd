ECHO OFF
set /p VarQuestion= Do you want to create an installer after the creation of the executable ? (y/n) : 

:::::::::::::::::::: put your python path ::::::::::::::::::::::::::::::::::
SET pythonpath=C:\Users\quentin.royer\AppData\Local\Programs\Python\Python36
:::::::::::::::::::: put your python path ::::::::::::::::::::::::::::::::::

ECHO if build\cx_Freeze folder exist, remove it
if exist build\cx_Freeze rmdir /Q /S build\cx_Freeze

ECHO cx_Freeze
%pythonpath%\python.exe cx_Freeze_config.py build -b build\cx_Freeze

ECHO copy folders
robocopy biology build\cx_Freeze\exe.win-amd64-3.6\biology /E
robocopy doc build\cx_Freeze\exe.win-amd64-3.6\doc /E
robocopy model_hydro build\cx_Freeze\exe.win-amd64-3.6\model_hydro /E
robocopy translation build\cx_Freeze\exe.win-amd64-3.6\translation /E

ECHO run executable to see errors
cd build\cx_Freeze\exe.win-amd64-3.6
habby.exe
cd ..\..\..
ECHO executable created in ..\habby\build\cx_Freeze

if %VarQuestion%== y ECHO Setup running..
if %VarQuestion%== y start "" /w "C:\Program Files (x86)\Inno Script Studio\isstudio.exe" -compile setup_from_cx_Freeze.iss
if %VarQuestion%== y ECHO Setup successfully created in ..\habby\build\cx_Freeze
if not %VarQuestion%== y ECHO Setup not started

:: Get console open to see details
@pause 
