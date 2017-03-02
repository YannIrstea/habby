import numpy as np


def load_manning_txt(filename_path):
    """
    This function loads the manning data in case where manning number is not simply a constant. In this case, the manning
    parameter is given in a .txt file. The manning parameter used by 1D model such as mascaret or Rubar BE to distribute
    velocity along the profiles. The format of the txt file is "p, dist, n" where  p is the profile number (start at zero),
    dist is the distance along the profile in meter and n is the manning value (in SI unit). White space is neglected
    and a line starting with the character # is also neglected.

    There is a very similar function as a method in the class Sub_HydroW() in hydro_GUI.py but it ised by the GUI
    and it includes a way to select the file using the GUI. Changes should be copied in both functions if necessary.

    :param filename_path: the path and the name of the file containing the manning data
    :return: the manning as an array form
    """

    try:
        with open(filename_path, 'rt') as f:
            data = f.read()
    except IOError:
        print('Error: The selected file for manning can not be open.')
        return
    # create manning array (to pass to dist_vitess)
    data = data.split('\n')
    manning = np.zeros((len(data), 3))
    com = 0
    for l in range(0, len(data)):
        data[l] = data[l].strip()
        if len(data[l])>0:
            if data[l][0] != '#':
                data_here = data[l].split(',')
                if len(data_here) == 3:
                    try:
                        manning[l - com, 0] = np.int(data_here[0])
                        manning[l - com, 1] = np.float(data_here[1])
                        manning[l - com, 2] = np.float(data_here[2])
                    except ValueError:
                        print('Error: The manning data could not be converted to float or int.'
                                           ' Format: p,dist,n line by line.')
                        return
                else:
                    print('Error: The manning data was not in the right format.'
                                       ' Format: p,dist,n line by line.')
                    return

            else:
                manning = np.delete(manning, -1, 0)
                com += 1

    return manning