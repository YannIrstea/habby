:: activate native conda
if exist %USERPROFILE%\Miniconda3\Scripts\activate.bat call %USERPROFILE%\Miniconda3\Scripts\activate.bat
if exist %USERPROFILE%\AppData\Local\Continuum\miniconda3\Scripts\activate.bat call %USERPROFILE%\AppData\Local\Continuum\miniconda3\Scripts\activate.bat
if exist C:\ProgramData\Miniconda3\Scripts\activate.bat call C:\ProgramData\Miniconda3\Scripts\activate.bat

:: PATHS
SET habby_path=C:\habby_dev\habby
SET envir_virtuels_path=C:\habby_dev\env_virtuels
SET envir_virtuel_name=env_habby_dev

::::::::::: ACTIVATE VIRTUAL ENV ::::::::::::::
:: not conda
::call %envir_virtuels_path%\%envir_virtuel_name%\Scripts\activate 
:: conda
call conda activate %envir_virtuels_path%\%envir_virtuel_name%
::call %envir_virtuel_path%\Scripts\activate.bat

::::::::::: RUN COMPILATION :::::::::::::::::::
set /p VarQuestion= Do you want to create an installer after the creation of the executable ? (y/n) : 

ECHO if build\pyinstaller folder exist, remove it
if exist build\pyinstaller rmdir /Q /S build\pyinstaller

ECHO pyinstaller ##  --windowed remove console  --specpath=pyinstaller_config.spec  --add-binary C:\users\quentin.royer\documents\taf\environnements_virtuels\env_habby_dev2\lib\site-packages\shapely\DLLs\geos.dll;geos.dll 
::pyinstaller --icon=translation\habby_icon.ico --windowed --distpath=build\pyinstaller --workpath=build\pyinstaller\temp --name=habby habby.py
pyinstaller habby.spec --distpath=build\pyinstaller --workpath=build\pyinstaller\temp

ECHO if build folder exist, remove it
if exist build\pyinstaller\temp rmdir /Q /S build\pyinstaller\temp
if exist __pycache__ rmdir /Q /S __pycache__

ECHO copy folders
robocopy biology build\pyinstaller\habby\biology /E > nul
robocopy doc build\pyinstaller\habby\doc /E > nul
robocopy model_hydro build\pyinstaller\habby\model_hydro /E > nul
robocopy translation build\pyinstaller\habby\translation /E > nul
robocopy files_dep build\pyinstaller\habby\files_dep /E > nul

if %VarQuestion%== n ECHO run executable to see errors
if %VarQuestion%== n cd build\pyinstaller\habby\
if %VarQuestion%== n habby.exe
if %VarQuestion%== n cd ..\..\..
if %VarQuestion%== n ECHO executable created in ..\habby\build\pyinstaller

if %VarQuestion%== n ECHO Executable successfully created (not setup)
if %VarQuestion%== y ECHO Executable successfully created and setup file creating..
if %VarQuestion%== y start "" /w "C:\Program Files (x86)\Inno Script Studio\isstudio.exe" -compile setup_from_pyinstaller.iss
if %VarQuestion%== y ECHO Setup successfully created

:: Get console open to see details
@pause 
