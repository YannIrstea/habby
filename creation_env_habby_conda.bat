:: add channels
call conda config --add channels conda-forge
call conda config --add channels anaconda
call conda config --add channels ramonaoptics

:: CONDA and PIP
call conda create --prefix C:\habby_dev\env_virtuels\env_habby_dev python=3.6 --yes
call conda activate C:\habby_dev\env_virtuels\env_habby_dev
call conda install -c conda-forge numpy conda-forge::blas=*=openblas --yes
call conda install gdal=3.0.2 --yes
call conda install pyqt=5.9.2 --yes
call conda install triangle=20170429 --yes
pip install appdirs==1.4.3
pip install qdarkstyle==2.8
pip install matplotlib==3.1.3
pip install h5py==2.10.0
pip install numpy-stl==2.10.1
pip install lxml==4.5.0
pip install scipy==1.4.1
pip install mplcursors==0.3
pip install pillow==7.0.0
pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip

:::::::::::::::::::::::::::: RUN HABBY :::::::::::::::
python habby.py

:: Get console open to see details
@pause 