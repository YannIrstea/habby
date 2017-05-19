ECHO OFF

ECHO Load hydrological models and put them in the command_cmd folder

SET p=C:\Users\diane.von-gunten\HABBY\output_cmd\result_cmd2

:: python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv4\*.g0* D:\Diane_work\file_test\hecrasv4\*.xml 0 path_prj=%p%
:: python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv4\*.g0* D:\Diane_work\file_test\hecrasv4\*.xml 1 5 path_prj=%p%
:: python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv5\*.g0* D:\Diane_work\file_test\hecrasv5\*.sdf 0 path_prj=%p%
:: python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv5\*.g0* D:\Diane_work\file_test\hecrasv5\*.sdf 1 5 path_prj=%p%
:: python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv5\rep\*.g0* D:\Diane_work\file_test\hecrasv5\rep\*.rep 0 path_prj=%p%
:: python habby_cmd.py ALL LOAD_HECRAS_1D D:\Diane_work\file_test\hecrasv5\rep\*.g0* D:\Diane_work\file_test\hecrasv5\rep\*.rep 1 5 path_prj=%p%
:: python habby_cmd.py ALL LOAD_HECRAS_2D D:\Diane_work\file_test\2Dmodel\hec_ras2D\*.hdf path_prj=%p%
:: python habby_cmd.py ALL LOAD_MASCARET D:\Diane_work\file_test\mascaret\*.xcas D:\Diane_work\file_test\mascaret\*.geo D:\Diane_work\file_test\mascaret\*.opt 0.025 0 path_prj=%p%
:: python habby_cmd.py ALL LOAD_MASCARET D:\Diane_work\file_test\mascaret\*.xcas D:\Diane_work\file_test\mascaret\*.geo D:\Diane_work\file_test\mascaret\*.opt 0.025 1 5 path_prj=%p%
:: python habby_cmd.py ALL LOAD_RUBAR_1D D:\Diane_work\file_test\rubar\*.rbe D:\Diane_work\file_test\rubar\profil.* 0.025 1 5 path_prj=%p%
:: python habby_cmd.py ALL LOAD_RUBAR_2D D:\Diane_work\file_test\2Dmodel\rubar2D\*.dat D:\Diane_work\file_test\2Dmodel\rubar2D\*.tps path_prj=%p%
python habby_cmd.py ALL LOAD_RIVER_2D D:\Diane_work\file_test\2Dmodel\river2D_test1\* path_prj=%p%
:: python habby_cmd.py ALL LOAD_TELEMAC D:\Diane_work\file_test\2Dmodel\telemac\*.res path_prj=%p%

ECHO Create a random substrate and merge the files
python habby_cmd.py ALL MERGE_GRID_RAND_SUB C:\Users\diane.von-gunten\HABBY\output_cmd\result_cmd2\*.h5 path_prj=%p%

ECHO Calculate the habitat  
python habby_cmd.py ALL RUN_HAB_COARSE C:\Users\diane.von-gunten\HABBY\output_cmd\result_cmd2\MERGE_*.h5 BAM01.xml path_prj=%p%