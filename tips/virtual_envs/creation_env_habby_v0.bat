:::::::::::::::::::::::::::: PYTHON PATH and GDAL wheel filename ::::::::::::::::::::::::::::
SET python_source_path=%USERPROFILE%\AppData\Local\Programs\Python\Python36\python.exe

:::::::::::::::::::::::::::: HABBY PYTHON VIRTUAL ENV PATH :::::::::::::::
SET habby_dev_path=C:\habby_dev
SET envir_virtuel_path=%habby_dev_path%\env_virtuels\env_habby_v0_pip
SET habby_path=%habby_dev_path%\habby_v0

:::::::::::::::::::::::::::: HABBY PYTHON VIRTUAL ENV CREATION :::::::::::::::
%python_source_path% -m venv %envir_virtuel_path%

:::::::::::::::::::::::::::: HABBY PYTHON VIRTUAL ENV CREATION ACTIVATION :::::::::::::::
::call %envir_virtuel_path%\Scripts\activate.bat
::call %envir_virtuel_path%\Scripts\Deactivate

:::::::::::::::::::::::::::: HABBY PYTHON VIRTUAL ENV CREATION MODULE INSTALLATION :::::::::::::::
%envir_virtuel_path%/Scripts/python.exe -m pip install --upgrade pip
%envir_virtuel_path%/Scripts/pip install setuptools --upgrade
%envir_virtuel_path%/Scripts/pip install numpy
%envir_virtuel_path%/Scripts/pip install PyQt5
%envir_virtuel_path%/Scripts/pip install h5py
%envir_virtuel_path%/Scripts/pip install matplotlib
%envir_virtuel_path%/Scripts/pip install triangle
%envir_virtuel_path%/Scripts/pip install scipy
%envir_virtuel_path%/Scripts/pip install pyshp

:::::::::::::::::::::::::::: RUN HABBY :::::::::::::::
cd %habby_path%
%envir_virtuel_path%/Scripts/python habby.py

:: Get console open to see details
@pause 