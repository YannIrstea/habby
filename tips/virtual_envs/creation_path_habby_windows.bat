:: habby python project paths creation
SET habby_project_path=C:\habby_dev
SET virtual_envs_folder_path=C:\habby_dev\env_virtuels
SET dependence_folder_path=C:\habby_dev\dependence
IF not exist %habby_project_path% (mkdir %habby_project_path%)
IF not exist %virtual_envs_folder_path% (mkdir %virtual_envs_folder_path%)
IF not exist %dependence_folder_path% (mkdir %dependence_folder_path%)

:: Get console open to see details
@pause 