## PIP
pip3 install pip --upgrade
pip3 install virtualenv

cd /datas/habby_dev/env_virtuels/

virtualenv --python /usr/bin/python3.10 env_habby_dev_pip

## activate
source /datas/habby_dev/env_virtuels/env_habby_dev_pip/bin/activate

pip3 install pip --upgrade

pip3 install gdal==2.2.3 --global-option=build_ext --global-option="-I/usr/include/gdal/"

pip3 install -r $HOME/habby_dev/habby/requirements.txt

## RUN HABBY
python $HOME/habby_dev/habby/habby.py

