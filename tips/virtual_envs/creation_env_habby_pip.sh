## PIP
pip3 install pip --upgrade
pip3 install virtualenv

#python3.6 -m venv /local/AIX/quentin.royer/Documents/habby_dev/env_virtuels/env_habby_dev_pip

cd /datas/habby_dev/env_virtuels/

#virtualenv --python /local/AIX/quentin.royer/Documents/habby_dev/dependances/Python-3.9.2/python env_habby_dev_pip
virtualenv --python /usr/bin/python3.6 env_habby_dev_pip

## activate
source /datas/habby_dev/env_virtuels/env_habby_dev_pip/bin/activate

pip3 install pip --upgrade

pip3 install gdal==2.2.3 --global-option=build_ext --global-option="-I/usr/include/gdal/"

pip3 install -r /datas/habby_dev/habby/requirements.txt

## RUN HABBY
python /datas/habby_dev/habby/habby.py

