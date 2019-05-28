::::::::::: ACTIVATE VIRTUAL ENV ::::::::::::::
SET envir_virtuel_path=C:\Users\quentin.royer\Documents\TAF\ENVIRONNEMENTS_VIRTUELS\env_habby_dev
call %envir_virtuel_path%\Scripts\activate.bat

::::::::::: RUN COMPILATION :::::::::::::::::::
set /p VarQuestion= Do you want to create an installer after the creation of the executable ? (y/n) : 

ECHO if build\pyinstaller folder exist, remove it
if exist build\pyinstaller rmdir /Q /S build\pyinstaller

ECHO pyinstaller ##  --windowed get error output
pyinstaller --icon=translation\habby_icon.ico --distpath=build\pyinstaller --workpath=build\pyinstaller\temp --windowed --specpath=build\pyinstaller\temp --name=habby habby.py

ECHO if build folder exist, remove it
if exist build\pyinstaller\temp rmdir /Q /S build\pyinstaller\temp
if exist __pycache__ rmdir /Q /S __pycache__

ECHO copy folders
robocopy biology build\pyinstaller\habby\biology /E
robocopy doc build\pyinstaller\habby\doc /E
robocopy model_hydro build\pyinstaller\habby\model_hydro /E
robocopy translation build\pyinstaller\habby\translation /E
robocopy files_dep build\pyinstaller\habby\files_dep /E

ECHO run executable to see errors
cd build\pyinstaller\habby\
habby.exe
cd ..\..\..
ECHO executable created in ..\habby\build\pyinstaller

if %VarQuestion%== n ECHO executable created (not setup)
if %VarQuestion%== y ECHO Setup running..
if %VarQuestion%== y start "" /w "C:\Program Files (x86)\Inno Script Studio\isstudio.exe" -compile setup_from_pyinstaller.iss
if %VarQuestion%== y ECHO Setup successfully created in ..\habby\build\pyinstaller
if not %VarQuestion%== n ECHO Setup not started

:: Get console open to see details
@pause 
