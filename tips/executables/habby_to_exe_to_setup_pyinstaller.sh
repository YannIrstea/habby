habby_dev_path=$HOME

source /datas/habby_dev/env_virtuels/env_habby_dev_pip/bin/activate

cd $habby_dev_path/habby

rm -rf build/pyinstaller/temp
rm -rf build/pyinstaller/habby
rm build/pyinstaller/habby.zip

/datas/habby_dev/env_virtuels/env_habby_dev_pip/bin/pyinstaller tips/executables/habby.spec --distpath=build/pyinstaller --workpath=build/pyinstaller/temp --noconfirm

cp -r biology build/pyinstaller/habby/biology
cp -r doc build/pyinstaller/habby/doc
cp -r model_hydro build/pyinstaller/habby/model_hydro
cp -r translation build/pyinstaller/habby/translation
cp -r file_dep build/pyinstaller/habby/file_dep

cd build/pyinstaller/habby
./habby

cd ..
zip -r habby.zip habby

echo "Get console open to see details, press enter!"
read a
