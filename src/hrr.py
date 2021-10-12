from src.hdf5_mod import Hdf5Management


if __name__ == '__main__':
    # set working directory to "C:\habby_dev\habby"
    path_prj = r"C:\Users\Quentin\Documents\HABBY_projects\DefaultProj"

    # first file
    input_filename_1 = "d1.hyd"
    hdf5_1 = Hdf5Management(path_prj, input_filename_1, new=False, edit=False)
    hdf5_1.load_hdf5()
    hdf5_1.data_2d[0][0].c_mesh_height()  # compute h mesh from h node (memory)

    # get tin first reach first unit
    tin = hdf5_1.data_2d[0][0]["mesh"]["tin"]
    xy = hdf5_1.data_2d[0][0]["node"]["xy"]
    z_fond_node = hdf5_1.data_2d[0][0]["node"]["z"]
    h_node = hdf5_1.data_2d[0][0]["node"]["data"]["h"]
    h_mesh = hdf5_1.data_2d[0][0]["mesh"]["data"]["h"]