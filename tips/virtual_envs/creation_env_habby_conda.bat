:: activate native conda
if exist %USERPROFILE%\Miniconda3\Scripts\activate.bat call %USERPROFILE%\Miniconda3\Scripts\activate.bat
if exist %USERPROFILE%\AppData\Local\Continuum\miniconda3\Scripts\activate.bat call %USERPROFILE%\AppData\Local\Continuum\miniconda3\Scripts\activate.bat
if exist C:\ProgramData\Miniconda3\Scripts\activate.bat call C:\ProgramData\Miniconda3\Scripts\activate.bat

:: PATHS
SET habby_path=C:\habby_dev\habby
SET envir_virtuels_path=C:\habby_dev\env_virtuels
SET envir_virtuel_name=env_habby_dev

call conda update conda --yes
:: add channels
call conda config --add channels conda-forge
call conda config --add channels anaconda
call conda config --add channels ramonaoptics

:: remove virtual env folder
if exist %envir_virtuels_path%\%envir_virtuel_name% rmdir /Q /S %envir_virtuels_path%\%envir_virtuel_name%

:: CONDA and PIP (virtual env + packages installation)
call conda create --prefix %envir_virtuels_path%\%envir_virtuel_name% python=3.6 --yes
call conda activate %envir_virtuels_path%\%envir_virtuel_name%
call conda install -c conda-forge numpy conda-forge::blas=*=openblas --yes 
call conda install pyinstaller gdal h5py --yes
pip install PyQt5 triangle appdirs qdarkstyle matplotlib numpy-stl lxml scipy mplcursors pillow pandas

:::::::::::::::::::::::::::: RUN HABBY :::::::::::::::
python %habby_path%\habby.py

:: EXPORT TO YML
::conda env export > env_habby_dev.yml

:: CREATE env_habby_dev VIRTUAL ENV CONDA FROM .yml
::call conda env create --file env_habby_dev.yml
:: CREATE A NEW NAME env_habby_dev2 VIRTUAL ENV CONDA FROM .yml
::call conda env create --file env_habby_dev.yml --prefix C:\habby_dev\env_virtuels\env_habby_dev2

:: Get console open to see details
@pause 