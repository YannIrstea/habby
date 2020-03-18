:: activate native conda
if exist %USERPROFILE%\Miniconda3\Scripts\activate.bat call %USERPROFILE%\Miniconda3\Scripts\activate.bat
if exist %USERPROFILE%\AppData\Local\Continuum\miniconda3\Scripts\activate.bat call %USERPROFILE%\AppData\Local\Continuum\miniconda3\Scripts\activate.bat

call conda update conda --yes
:: add channels
call conda config --add channels conda-forge
call conda config --add channels anaconda
call conda config --add channels ramonaoptics

:: CONDA and PIP (virtual env + packages installation)
call conda create --prefix C:\\habby_dev\\env_virtuels\\env_habby_dev python=3.6 --yes
call conda activate C:\\habby_dev\\env_virtuels\\env_habby_dev
call conda install -c conda-forge numpy conda-forge::blas=*=openblas --yes 
call conda install pyinstaller=3.6 --yes
call conda install gdal=3.0.2 --yes
call conda install pyqt=5.9.2 --yes
::call conda install triangle=20170429 --yes
call conda install h5py=2.10.0 --yes
pip install git+git://github.com/drufat/triangle@master
pip install appdirs==1.4.3
pip install qdarkstyle==2.8
pip install matplotlib==3.1.3
pip install numpy-stl==2.10.1
pip install lxml==4.5.0
pip install scipy==1.4.1
pip install mplcursors==0.3
pip install pillow==7.0.0

:::::::::::::::::::::::::::: RUN HABBY :::::::::::::::
python habby.py

:: EXPORT TO YML
conda env export > env_habby_dev.yml

:: CREATE env_habby_dev VIRTUAL ENV CONDA FROM .yml
::call conda env create --file env_habby_dev.yml
:: CREATE A NEW NAME env_habby_dev2 VIRTUAL ENV CONDA FROM .yml
::call conda env create --file env_habby_dev.yml --prefix C:\habby_dev\env_virtuels\env_habby_dev2

:: Get console open to see details
@pause 