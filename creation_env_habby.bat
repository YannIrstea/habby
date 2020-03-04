:: install python + pip install virtualenv if use


:::::::::::::::::::::::::::: CREATION ENVIRONNEMENT VIRTUEL POUR HABBY :::::::::::::::
SET python_source_path=%USERPROFILE%\AppData\Local\Programs\Python\Python36\python.exe
SET envir_virtuel_path=C:\habby_dev\env_virtuels\env_habby_dev2
SET habby_path=C:\habby_dev\habby

:::::::::::::::::::::::::::: CREATION ENVIRONNEMENT VIRTUEL POUR HABBY :::::::::::::::
%python_source_path% -m venv %envir_virtuel_path%

:::::::::::::::::::::::::::: ACTIVATION ENVIRONNEMENT VIRTUEL :::::::::::::::
::call %envir_virtuel_path%\Scripts\activate.bat
::call %envir_virtuel_path%\Scripts\Deactivate


:::::::::::::::::::::::::::: INSTALLATION MODULES POUR HABBY :::::::::::::::
%envir_virtuel_path%/Scripts/python.exe -m pip install --upgrade pip
%envir_virtuel_path%/Scripts/pip install setuptools --upgrade
%envir_virtuel_path%/Scripts/pip install -r requ_windows.txt
::%envir_virtuel_path%/Scripts/pip install numpy==1.15.3
::%envir_virtuel_path%/Scripts/pip install PyQt5==5.11.3
::%envir_virtuel_path%/Scripts/pip install h5py==2.8.0rc1
::%envir_virtuel_path%/Scripts/pip install matplotlib==3.0.0
::%envir_virtuel_path%/Scripts/pip install scipy==1.1.0
:: pour triangle : avoir prealablement installer ca : "go.microsoft.com/fwlink/?LinkId=691126&fixForIE=.exe." ou via la .whl
::%envir_virtuel_path%/Scripts/pip install triangle==20170429  
::%envir_virtuel_path%/Scripts/pip install %envir_virtuel_path%/packages_python_wheel/GDAL-2.4.1-cp36-cp36m-win_amd64.whl
%envir_virtuel_path%/Scripts/pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip
::%envir_virtuel_path%/Scripts/pip install cx_Freeze==5.1.1


:::::::::::::::::::::::::::: RUN HABBY :::::::::::::::
cd %habby_path%
%envir_virtuel_path%/Scripts/python habby.py



::pyinstaller --windowed --onefile --icon=homer.ico PyProcessMemoryAnalysis.py



:: Get console open to see details
@pause 