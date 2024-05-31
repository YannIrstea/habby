:::::::::::::::::::::::::::: PYTHON PATH and GDAL wheel filename ::::::::::::::::::::::::::::
SET python_source_path=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe
SET gdal_wheel_path="C:\habby_dev\dependence\GDAL-3.8.4-cp311-cp311-win_amd64.whl"

:::::::::::::::::::::::::::: HABBY PYTHON VIRTUAL ENV PATH :::::::::::::::
SET habby_dev_path=C:\habby_dev
SET envir_virtuel_path=%habby_dev_path%\env_virtuels\env_habby_dev_pip_py311
SET habby_path=%habby_dev_path%\habby

:::::::::::::::::::::::::::: HABBY PYTHON VIRTUAL ENV CREATION :::::::::::::::
%python_source_path% -m venv %envir_virtuel_path%

:::::::::::::::::::::::::::: HABBY PYTHON VIRTUAL ENV CREATION ACTIVATION :::::::::::::::
::call %envir_virtuel_path%\Scripts\activate.bat
::call %envir_virtuel_path%\Scripts\Deactivate

:::::::::::::::::::::::::::: HABBY PYTHON VIRTUAL ENV CREATION MODULE INSTALLATION :::::::::::::::
%envir_virtuel_path%/Scripts/python.exe -m pip install --upgrade pip
%envir_virtuel_path%/Scripts/pip install setuptools --upgrade
%envir_virtuel_path%/Scripts/pip install -r %habby_path%\requirements.txt
:: gdal dowload wheel from : https://github.com/cgohlke/geospatial-wheels/releases and set install it with pip
%envir_virtuel_path%/Scripts/pip install %gdal_wheel_path%

:::::::::::::::::::::::::::: RUN HABBY :::::::::::::::
cd %habby_path%
%envir_virtuel_path%/Scripts/python habby.py

:: Get console open to see details
@pause 