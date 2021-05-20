source /datas/habby_dev/env_virtuels/env_habby_dev_pip/bin/activate

cd /datas/habby_dev/habby

pyinstaller tips/executables/habby.spec --distpath=build/pyinstaller --workpath=build/pyinstaller/temp

cp -r biology build/pyinstaller/habby/biology
cp -r doc build/pyinstaller/habby/doc
cp -r model_hydro build/pyinstaller/habby/model_hydro
cp -r translation build/pyinstaller/habby/translation
cp -r file_dep build/pyinstaller/habby/file_dep

cd build/pyinstaller/habby
./habby

cd ..
zip -r habby.zip habby


