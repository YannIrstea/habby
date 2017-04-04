import numpy as np
import os

def load_manning_txt(filename_path):
    """
    This function loads the manning data in case where manning number is not simply a constant. In this case, the manning
    parameter is given in a .txt file. The manning parameter used by 1D model such as mascaret or Rubar BE to distribute
    velocity along the profiles. The format of the txt file is "p, dist, n" where  p is the profile number (start at zero),
    dist is the distance along the profile in meter and n is the manning value (in SI unit). White space is neglected
    and a line starting with the character # is also neglected.

    There is a very similar function as a method in the class Sub_HydroW() in hydro_GUI.py but it used by the GUI
    and it includes a way to select the file using the GUI and it used a lot of class attribute. So it cannot be used
    by the command line. Changes should be copied in both functions if necessary.

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


def load_fstress_text(path_fstress):
    """
    This function loads the data for fstress from text files. The data is composed of the name of the rive, the
    discharge range, and the [discharge, height, width]. To read the files, the files listriv.txt is given. Form then,
    the function looks for the other files in the same folder. The other files are rivdeb.txt and rivqwh.txt. If more
    than one river is given in listriv.txt, it load the data for all rivers.

    There is a very similar function as a method in the class FStressW() in fstress_GUI.py but it ised by the GUI
    and it includes a way to select the file using the GUI. Changes should be copied in both functions if necessary.

    :param path_fstress: the path to the listriv.txt function (the other fil should be in the same folder)

    """

    found_file = []
    riv_name = []

    # filename_path
    filename = 'listriv.txt'
    filename_path = os.path.join(path_fstress, filename)

    if not os.path.isfile(filename_path):
        print('Error: listriv.txt could not be found.')
        return [-99],[-99],[-99]

    # get the river name
    with open(filename_path, 'rt') as f:
        for line in f:
            riv_name.append(line.strip())

    # add the file names (deb and qhw.txt)
    for r in riv_name:
        f_found = [None, None]
        # discharge range
        debfilename = r + 'deb.txt'
        if os.path.isfile(os.path.join(path_fstress, debfilename)):
            f_found[1] = debfilename
        elif os.path.isfile(os.path.join(path_fstress, r + 'DEB.TXT')):
            debfilename = r[:-7] + 'DEB.TXT'
            f_found[1] = debfilename
        else:
            f_found[1] = None
        # qhw
        qhwname = r + 'qhw.txt'
        if os.path.isfile(os.path.join(path_fstress, qhwname)):
            f_found[0] = qhwname
        elif os.path.isfile(os.path.join(path_fstress, r + 'QHW.TXT')):
            qhwname = r + 'QHW.TXT'
            f_found[0] = qhwname
        else:
            print('Error: qhw file not found for river ' + r + '.')
            return
        found_file.append(f_found)

    # if not river found
    if len(riv_name) == 0:
        print('Warning: No river found in files')
        return [-99],[-99],[-99]

    # load the data for each river
    qrange = []
    qhw = []
    for ind in range(0, len(found_file)):
        fnames = found_file[ind]

        # discharge range
        if fnames[1] is not None:
            fname_path = os.path.join(path_fstress, fnames[1])
            if os.path.isfile(fname_path):
                with open(fname_path, 'rt') as f:
                    data_deb = f.read()
                data_deb = data_deb.split()
                try:
                    data_deb = list(map(float, data_deb))
                except ValueError:
                    print('Error: Data cannot be converted to float in deb.txt')
                    return
                qmin = min(data_deb)
                qmax = max(data_deb)

                qrange.append([qmin, qmax])
            else:
                print('Error: deb.txt file not found.(1)')
                return [-99], [-99], [-99]
        else:
            print('Error: deb.txt file not found.(2)')
            return [-99], [-99], [-99]

        # qhw
        fname_path = os.path.join(path_fstress, fnames[0])
        if os.path.isfile(fname_path):
            with open(fname_path, 'rt') as f:
                data_qhw = f.read()
            data_qhw = data_qhw.split()
            # useful to pass in float to check taht we have float
            try:
                data_qhw = list(map(float, data_qhw))
            except ValueError:
                print('Error: Data cannot be concerted to float in qhw.txt')
                return [-99], [-99], [-99]
            if len(data_qhw) < 6:
                print('Error: FStress needs at least two discharge measurement.')
                return [-99], [-99], [-99]
            if len(data_qhw)%3 != 0:
                print('Error: One discharge measurement must be composed of three data (q,w, and h).')
                return [-99], [-99], [-99]

            qhw.append([[data_qhw[0], data_qhw[1], data_qhw[2]],[data_qhw[3], data_qhw[4], data_qhw[5]]])
        else:
            print('Error: qwh.txt file not found.(2)')
            return [-99], [-99], [-99]

    return riv_name, qhw, qrange