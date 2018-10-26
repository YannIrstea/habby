ECHO OFF

ECHO if build\pyinstaller folder exist, remove it
if exist build\pyinstaller rmdir /Q /S build\pyinstaller

ECHO pyinstaller 
pyinstaller --windowed --icon=translation\habby_icon.ico --distpath=build\pyinstaller --workpath=build\pyinstaller\temp --specpath=build\pyinstaller\temp --name=habby habby.py

ECHO if build folder exist, remove it
if exist build\pyinstaller\temp rmdir /Q /S build\pyinstaller\temp
if exist __pycache__ rmdir /Q /S __pycache__

ECHO copy folders
robocopy biology build\pyinstaller\habby\biology /E
robocopy doc build\pyinstaller\habby\doc /E
robocopy model_hydro build\pyinstaller\habby\model_hydro /E
robocopy translation build\pyinstaller\habby\translation /E

ECHO run executable to see errors
cd build\pyinstaller\habby\
habby.exe
cd ..\..\..
ECHO executable created in ..\habby\build\pyinstaller

set /p VarQuestion= Start the creation of the setup ? (yes/no) : 
if %VarQuestion%== yes ECHO Setup running..
if %VarQuestion%== yes start "" /w "C:\Program Files (x86)\Inno Script Studio\isstudio.exe" -compile setup_from_pyinstaller.iss
if %VarQuestion%== yes ECHO Setup successfully created in ..\habby\build\pyinstaller
if %VarQuestion%== no ECHO Setup not started

:: Get console open to see details
@pause 
