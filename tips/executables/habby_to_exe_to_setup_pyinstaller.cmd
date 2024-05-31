:: activate native conda
::if exist %USERPROFILE%\Miniconda3\Scripts\activate.bat call %USERPROFILE%\Miniconda3\Scripts\activate.bat
::if exist %USERPROFILE%\AppData\Local\Continuum\miniconda3\Scripts\activate.bat call %USERPROFILE%\AppData\Local\Continuum\miniconda3\Scripts\activate.bat
::if exist C:\ProgramData\Miniconda3\Scripts\activate.bat call C:\ProgramData\Miniconda3\Scripts\activate.bat

:: PATHS
SET habby_path=C:\habby_dev\habby
SET envir_virtuels_path=C:\habby_dev\env_virtuels
SET envir_virtuel_name=env_habby_dev_pip_py311

::::::::::: ACTIVATE VIRTUAL ENV ::::::::::::::
:: not conda
call %envir_virtuels_path%\%envir_virtuel_name%\Scripts\activate
:: conda
::call conda activate %envir_virtuels_path%\%envir_virtuel_name%
::call %envir_virtuel_path%\Scripts\activate.bat

cd %habby_path%

::::::::::: RUN COMPILATION :::::::::::::::::::
set /p VarQuestion= Do you want to create an installer after the creation of the executable ? (y/n) : 

ECHO if build\pyinstaller folder exist, remove it
if exist build\pyinstaller rmdir /Q /S build\pyinstaller

ECHO pyinstaller ##  --windowed remove console  --specpath=pyinstaller_config.spec  --add-binary C:\users\quentin.royer\documents\taf\environnements_virtuels\env_habby_dev2\lib\site-packages\shapely\DLLs\geos.dll;geos.dll 
::pyinstaller --icon=file_dep\habby_icon.ico --windowed --distpath=build\pyinstaller --workpath=build\pyinstaller\temp --name=habby habby.py
pyinstaller tips\executables\habby.spec --distpath=build\pyinstaller --workpath=build\pyinstaller\temp --noconfirm

ECHO remove temp folder
if exist build\pyinstaller\temp rmdir /Q /S build\pyinstaller\temp
if exist __pycache__ rmdir /Q /S __pycache__

if %VarQuestion%== n ECHO run executable to see errors
if %VarQuestion%== n build\pyinstaller\habby\habby.exe
if %VarQuestion%== n ECHO executable created in ..\habby\build\pyinstaller

if %VarQuestion%== n ECHO Executable successfully created (not setup)
if %VarQuestion%== y ECHO Executable successfully created and setup file creating..
if %VarQuestion%== y start "" /w "C:\Program Files (x86)\Inno Script Studio\isstudio.exe" -compile tips\executables\setup_from_pyinstaller.iss
:: .exe to zip with tar.exe (-C: directory, -a: gzip mode, -c: create, -f: file, full path to ouptput file, filename to zip in specified directory)
if %VarQuestion%== y tar.exe -C build\pyinstaller -a -c -f build\pyinstaller\HABBY-setup-64.zip HABBY-setup-64.exe
if %VarQuestion%== y ECHO Setup file and archive successfully created

:: Get console open to see details, press enter
@pause 
