
REM load all hydrological model available and put them in the command_cmd folder
REM python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv4\*.g0* D:\Diane_work\file_test\hecrasv4\*.xml 0
REM python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv4\*.g0* D:\Diane_work\file_test\hecrasv4\*.xml 1 5
REM python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv5\*.g0* D:\Diane_work\file_test\hecrasv5\*.sdf 0
REM python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv5\*.g0* D:\Diane_work\file_test\hecrasv5\*.sdf 1 5
REM python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv5\rep\*.g0* D:\Diane_work\file_test\hecrasv5\rep\*.rep 0
REM python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv5\rep\*.g0* D:\Diane_work\file_test\hecrasv5\rep\*.rep 1 5
REM python habby_cmd.py ALL LOAD_HECRAS_2D D:\Diane_work\file_test\2Dmodel\hec_ras2D\*.hdf
REM python habby_cmd.py ALL LOAD_MASCARET D:\Diane_work\file_test\mascaret\*.xcas D:\Diane_work\file_test\mascaret\*.geo D:\Diane_work\file_test\mascaret\*.opt 0.025 0
REM python habby_cmd.py ALL LOAD_MASCARET D:\Diane_work\file_test\mascaret\*.xcas D:\Diane_work\file_test\mascaret\*.geo D:\Diane_work\file_test\mascaret\*.opt 0.025 1 5
REM python habby_cmd.py ALL LOAD_RUBAR_1D D:\Diane_work\file_test\rubar\*.rbe D:\Diane_work\file_test\rubar\profil.* 0.025 0
REM python habby_cmd.py ALL LOAD_RUBAR_1D D:\Diane_work\file_test\rubar\*.rbe D:\Diane_work\file_test\rubar\profil.* 0.025 1 5
REM python habby_cmd.py ALL LOAD_RUBAR_2D D:\Diane_work\file_test\2Dmodel\rubar2D\*.dat D:\Diane_work\file_test\2Dmodel\rubar2D\*.tps
REM python habby_cmd.py ALL LOAD_RIVER_2D D:\Diane_work\file_test\2Dmodel\river2D_test1\*
REM python habby_cmd.py ALL LOAD_TELEMAC D:\Diane_work\file_test\2Dmodel\telemac\*.res

python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\mychoice\*.g0* D:\Diane_work\file_test\mychoice\*.xml 0
python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\mychoice\*.g0* D:\Diane_work\file_test\mychoice\*.xml 1 5

REM create a random substrate and merge the files
python habby_cmd.py ALL MERGE_GRID_RAND_SUB C:\Users\diane.von-gunten\HABBY\output_cmd\result_cmd\*.h5

REM calculate the habitat
python habby_cmd.py ALL RUN_HAB_COARSE C:\Users\diane.von-gunten\HABBY\output_cmd\result_cmd\Hydro_MERGE_cmd*.h5 BAM01.xml