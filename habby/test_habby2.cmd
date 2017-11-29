ECHO OFF
:: This is a longer test for HABBY, where most of the module are used at least once. It might take one or two hours to run

ECHO Set the different folders
:: This should be modified when run on a new computer
:: folder with result, folder with the expected result, folder with the inputs in various folder
SET p=D:\Diane_work\file_test\compare_test_long\result
SET pex=D:\Diane_work\file_test\compare_test_long\expected
SET pin=D:\Diane_work\file_test\

ECHO Load hydrological models and put them in the command_cmd folder
python habby.py LOAD_LAMMI %pin%\Lammi\Entree %pin%\Lammi\Resu\SimHydro
python habby.py ALL LOAD_HECRAS_1D %pin%hecrasv4\*.g0* %pin%hecrasv4\*.xml 0 path_prj=%p%
python habby.py LOAD_HECRAS_1D %pin%\hecrasv4\BOGCHIT.g01 D:\Diane_work\file_test\hecrasv4\BOGCHIT.O01.xml 1 5 path_prj=%p%
python habby.py ALL LOAD_HECRAS_1D %pin%\hecrasv5\*.g0* %pin%\hecrasv5\*.sdf 0 path_prj=%p%
REM python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv5\*.g0* D:\Diane_work\file_test\hecrasv5\*.sdf 1 5 path_prj=%p%
python habby.py ALL LOAD_HECRAS_1D %pin%\hecrasv5\rep\*.g0* %pin%\hecrasv5\rep\*.rep 0 path_prj=%p%
python habby.py ALL LOAD_HECRAS_1D %pin%\rep\*.g0* %pin%\rep\*.rep 1 5 path_prj=%p%
REM careful, 800 time steps - 50Gig result!
REM python habby.py ALL LOAD_HECRAS_2D %pin%\2Dmodel\hec_ras2D\*.hdf path_prj=%p%
python habby.py ALL LOAD_HECRAS_2D %pin%\2Dmodel\hec_ras2D\Muncie.p04.hdf path_prj=%p%
python habby.py ALL LOAD_MASCARET %pin%\mascaret\*.xcas %pin%\mascaret\*.geo %pin%\mascaret\*.opt 0.025 0 path_prj=%p%
python habby.py ALL LOAD_MASCARET %pin%mascaret\*.xcas %pin%\mascaret\*.geo %pin%\mascaret\*.opt 0.025 1 5 path_prj=%p%
python habby.py ALL LOAD_MASCARET %pin%\mascaret\*.xcas %pin%\mascaret\*.geo %pin%\mascaret\*.opt 0.025 1 5 path_prj=%p%
python habby.py ALL LOAD_RUBAR_1D %pin%\rubar\*.rbe %pin%\rubar\profil.* 0.025 1 5 path_prj=%p%
python habby.py ALL LOAD_RUBAR_2D %pin%\2Dmodel\rubar2D\*.dat %pin%\2Dmodel\rubar2D\*.tps path_prj=%p%
python habby.py ALL LOAD_RIVER_2D %pin%\2Dmodel\river2D_test1\* path_prj=%p%
python habby.py ALL LOAD_TELEMAC %pin%\big_file_yann\*.slf path_prj=%p%
python habby.py ALL LOAD_TELEMAC %pin%\yann_durance\TELEMAC\*.slf path_prj=%p%

ECHO Load one substrate
python habby.py LOAD_SUB_SHP %pin%\substrate\bogchitte_sub.shp Cemagref path_prj=%p%

ECHO Merge the files
python habby.py ALL MERGE_GRID_SUB %p%\Hydro#.h5 %p%\Sub#.h5 1 path_prj=%p%

ECHO Calculate the habitat  
python habby.py ALL RUN_HABITAT %p%\Merge*.h5 BAM01.xml juvenile,fry 0 path_prj=%p%

ECHO Test statisitcal model
python habby.py RUN_ESTIMHAB 2 60 29 45 0.21 1.12 25 1 38 0.25 path_prj=%p%
python habby.py RUN_FSTRESS D:\Diane_work\file_test\input_fstress path_prj=%p%
python habby.py RUN_STATHAB D:\Diane_work\file_test\input_stathab path_prj=%p%

ECHO check with past results
python habby.py COMPARE_TEST %pex% %p%