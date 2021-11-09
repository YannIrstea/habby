from src.hdf5_mod import Hdf5Management


if __name__ == '__main__':
    # set working directory to "C:\habby_dev\habby"
    path_prj = r"C:\Users\Quentin\Documents\HABBY_projects\DefaultProj"

    # first file
    input_filename_1 = "d1.hyd"

    # load file
    hdf5_1 = Hdf5Management(path_prj, input_filename_1, new=False, edit=False)
    hdf5_1.load_hdf5(whole_profil=True)

    # for all reach
    for reach_number in range(0, hdf5_1.data_2d.reach_number):
        # for all units
        for unit_number in range(0, hdf5_1.data_2d[reach_number].unit_number):
            # c_mesh_height
            hdf5_1.data_2d[reach_number][unit_number].c_mesh_height()  # compute h mesh from h node (memory)

            # get tin first reach first unit
            tin = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["tin"]
            xy = hdf5_1.data_2d[reach_number][unit_number]["node"]["xy"]
            z_fond_node = hdf5_1.data_2d[reach_number][unit_number]["node"]["z"]
            h_node = hdf5_1.data_2d[reach_number][unit_number]["node"]["data"]["h"]
            h_mesh = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]["h"]
            i_whole_profile = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"]
            i_split = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"]["i_split"]

            # get tin first reach first unit whole_profile
            xy_whole_profile = hdf5_1.data_2d_whole[reach_number][unit_number]["node"]["xy"]
            tin_whole_profile = hdf5_1.data_2d_whole[reach_number][unit_number]["mesh"]["tin"]

