## PIP
pip3 install pip --upgrade
pip3 install virtualenv

cd /datas/habby_dev/env_virtuels/

virtualenv --python /usr/bin/python3.10 env_habby_dev_pip

## activate
source /datas/habby_dev/env_virtuels/env_habby_dev_pip/bin/activate

pip3 install pip --upgrade
## install first gdal linux and then gdal python
## sudo apt-get install gdal-bin
## sudo apt-get install libgdal-dev
## and for pip3 specify the good version of gdal
pip3 install gdal==3.4.1 --global-option=build_ext --global-option="-I/usr/include/gdal/"

pip3 install -r $HOME/habby/requirements.txt

## RUN HABBY
python $HOME/habby/habby.py

