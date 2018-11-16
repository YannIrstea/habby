ECHO OFF
:: This is a quick test for habby on only one file. It should take less than two minutes.

ECHO set the folders and files
:: this part should be modified
SET p=C:\Users\quentin.royer\Documents\TAF\DATA\HABBY\file_test\compare_test_quick\results
SET pex=C:\Users\quentin.royer\Documents\TAF\DATA\HABBY\file_test\compare_test_quick\expected
SET hydroin=C:\Users\quentin.royer\Documents\TAF\DATA\HABBY\file_test\yann_durance\TELEMAC\a1.slf
SET subin=C:\Users\quentin.royer\Documents\TAF\DATA\HABBY\file_test\compare_test_quick\substrate_for_quick_test\random_sub.shp

ECHO Load hydrological models and put them in the project folder
python habby.py LOAD_TELEMAC %hydroin% path_prj=%p%

ECHO Load substrate
python habby.py LOAD_SUB_SHP %subin% Cemagref path_prj=%p%

ECHO Merge the files
python habby.py ALL MERGE_GRID_SUB %p%\Hydro*.h5 %p%\Sub*.h5 1 path_prj=%p%

ECHO Calculate the habitat  
python habby.py ALL RUN_HABITAT %p%\Merge*.h5 BAM01.xml juvenile,fry 0 path_prj=%p%

ECHO Check the quick test
python habby.py COMPARE_TEST %pex% %p%

:: Get console open to see details
@pause 
