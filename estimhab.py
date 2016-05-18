import numpy as np
import xml.etree.ElementTree as ET
import os
import matplotlib.pyplot as plt
import time


def estimhab(qmes, width, height, q50, qrange, substrat, path_bio, fish_name, pict=False, save_pict=False):
    """
    A function to run the estimhab model. Unit in meter amd m^3/sec
    :param qmes the two measured discharge
    :param width the two measured width
    :param height the two measured height
    :param q50 the natural median discharge
    :param qrange the range of discharge
    :param substrat mean height of substrat
    :param pict if true the figure is shown. If false, the figure is not shown
    :param save_pict if true the figure is save. If false, the figure is not save
    :param path_bio the path to the xml file with the information on the fishes
    :param fish_name the name of the fish which have to be analyzed
    :return Habitat value and useful surface (VH and SPU) as a function of discharge
    """
    # matplotlib is hard to manage with more than one figure
    plt.close()

    # Q
    nb_q = 20  # number of calculated q
    if qrange[1] > qrange[0]:
        diff = (qrange[1] - qrange[0]) / nb_q
        q_all = np.arange(qrange[0], qrange[1]+diff, diff)
    else:
        print('Error: The mininum discharge is higher or equal than the maximum')
        return [-99], [-99]

    # height
    slope = (np.log(height[1]) - np.log(height[0])) / (np.log(qmes[1]) - np.log(qmes[0]))
    exp_cte = np.exp(np.log(height[0]) - slope*np.log(qmes[0]))
    h_all = exp_cte * q_all**slope
    h50 = exp_cte * q50**slope

    # width
    slope = (np.log(width[1]) - np.log(width[0])) / (np.log(qmes[1]) - np.log(qmes[0]))
    exp_cte = np.exp(np.log(width[0]) - slope*np.log(qmes[0]))
    w_all = exp_cte * q_all**slope
    l50 = exp_cte * q50**slope

    # velocity
    vel = (q_all/h_all)/w_all
    v50 = (q50/h50)/l50
    re = q_all/(10 * w_all)
    re50 = q50/(10*l50)

    # extra-data related to q50
    fr50 = q50 / (9.81**0.5 * h50**1.5*l50)
    dh50 = substrat / h50
    q50_data = [q50, h50, l50, v50, re50, fr50, dh50, np.exp(dh50)]

    # prepare figure0
    if pict:
        c = ['b', 'm', 'r', 'c', '#9932CC', '#800000', 'b', 'm', 'r', 'c', '#9932CC', '#800000']
        plt.figure()
        plt.suptitle("ESTIMHAB2008 - HABBY", fontsize=14)

    # get fish data
    VH = []
    SPU = []
    for f in range(0, len(fish_name)):
        # load xml file
        filename = os.path.join(path_bio, fish_name[f] + '.xml')
        if os.path.isfile(filename):
            doc = ET.parse(filename)
            root = doc.getroot()
        else:
            print('the xml file for the fish'+fish_name[f]+' does not exist')
            return [-99], [-99]

        # get data
        try:
            coeff_q = pass_to_float_estimhab(".//coeff_q", root)
            func_q = pass_to_float_estimhab(".//func_q", root)
            coeff_const = pass_to_float_estimhab(".//coeff_const", root)
            var_const = pass_to_float_estimhab(".//var_const", root)
        except ValueError:
            print('Error: Some data can not be read or are not number. Check the xml file '+ fish_name[f])
            return [-99], [-99]

        # calculate VH
        if func_q[0] == 0.:
            part_q = re**coeff_q[0]*np.exp(coeff_q[1] * re)
        elif func_q[0] == 1.:
            part_q = 1 + coeff_q[0]*np.exp(coeff_q[1] * re)
        else:
            print('Error: no function defined for Q')
        const = coeff_const[0]
        for i in range(0, len(var_const)):
            const += coeff_const[i+1] * np.log(q50_data[int(var_const[i])])
        VH_f = const*part_q
        SPU_f = VH_f*w_all*100
        if pict:
            plt.subplot(2, 1, 1)
            plt.plot(q_all, VH_f, color=c[f])
            plt.grid(True)
            plt.xlabel('discharge [m3/sec]')
            plt.ylabel('Valeur habitat []')
            plt.ylim(0, 1)

            plt.subplot(2, 1, 2)
            plt.plot(q_all, SPU_f, color=c[f])
            plt.grid(True)
            plt.xlabel('discharge [m3/sec]')
            plt.ylabel('SPU by 100 m')

        VH.append(VH_f)
        SPU.append(SPU_f)

    if pict:
        plt.legend(fish_name)
        # saving with date and time
        if save_pict:
            name_pict = "Estimhab_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            plt.savefig(name_pict + '.pdf')

            txt_header = 'Q [m3/sec] '
            data = q_all
            for f in range(0, len(fish_name)):
                txt_header += ' VH_' + fish_name[f] + ' SPU_' + fish_name[f]
                data = np.vstack((data, VH[f]))
                data = np.vstack((data, SPU[f]))
            np.savetxt(name_pict+'.txt', data.T, newline=os.linesep, header=txt_header)

        plt.show()

    return VH, SPU


def pass_to_float_estimhab(var_name, root):
    """
    a small function to pass from xml element to float
    :param root: the root of the open xml file
    :param var_name: the name of the attribute in the xml file
    :return: the float data
    """
    coeff_qe = root.findall(var_name)
    coeff_str = coeff_qe[0].text
    coeff = coeff_str.split()
    coeff = list(map(float, coeff))

    return coeff


def main():

    # data from the estimahab2008.xls found in http://www.irstea.fr/en/estimhab
    q = [2, 60]
    w = [29, 45]
    h = [0.21, 1.12]
    q50 = 25
    qrange = [1, 38]
    substrat = 0.25
    fish = ['TRF_ADU', 'TRF_JUV', 'BAF', 'CHA', 'GOU']
    path = r'.\biologie'

    [VH, SPU] = estimhab(q, w, h, q50, qrange, substrat, path, fish, True, True)


if __name__ == '__main__':
    main()
