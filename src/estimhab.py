"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V / 
|  _  ||  _  || ___ \ ___ \ \ /  
| | | || | | || |_/ / |_/ / | |  
\_| |_/\_| |_/\____/\____/  \_/  

Copyright (c) IRSTEA-EDF-AFB 2017

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
import numpy as np
import xml.etree.ElementTree as ET
import os
import matplotlib.pyplot as plt
import time
from src_GUI import output_fig_GUI
import matplotlib as mpl


def estimhab(qmes, width, height, q50, qrange, substrat, path_bio, fish_xml, path_im, pict=False, fig_opt={},
             path_txt=[], fish_name=''):
    """
    This the function which forms the Estimhab model in HABBY. It is a reproduction in python of the excel file which
    forms the original Estimhab model.. Unit in meter amd m^3/sec

    :param qmes: the two measured discharge
    :param width: the two measured width
    :param height: the two measured height
    :param q50: the natural median discharge
    :param qrange: the range of discharge
    :param substrat: mean height of substrat
    :param path_im: the path where the image should be saved
    :param path_bio: the path to the xml file with the information on the fishes
    :param fish_xml: the name of the xml file to be analyzed
    :param pict: if true the figure is shown. If false, the figure is not shown
    :param fig_opt: a dictionnary with the figure option
    :param path_txt: the path where to send the text data
    :param fish_name: the name fo the fish to be analysed (if not there, use the xml name)
    :return: habitat value and useful surface (VH and SPU) as a function of discharge

    **Technical comments and walk-through**

    First, we get all the discharges on which we want to calculate the SPU (surface ponderée utile),
    using the inputs from the user.

    Next we use hydrological rating curves (info on google if needed) to get the height and the width of the river for
    all discharge. The calculation is based on the width and height of the river measured at two discharges (given by the
    user).

    Next, we get other parameters which are used in the preference curves such as the Froude number of
    the mean discharge or the Reynolds number.

    Next, we load the fish data contains in the xml files in the biology folder. Careful, this is not the xml project
    file. This are the xml files described above in the “Class EstimhabW” section. There are one xml file per fish and
    they described the preference curves. For the argumentation on the form of the relationship, report yourself to the
    documentation of Estimhab (one pdf file should in the folder “doc “ in HABBY).

    Then, we calculate the habitat values (VH and SPU). Finally, we plot the results in a figure and we save it as
    a text file.
    """
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    if pict:
        plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
        plt.rcParams['font.size'] = fig_opt['font_size']
        plt.rcParams['lines.linewidth'] = fig_opt['line_width']
        format1 = int(fig_opt['format'])
        plt.rcParams['axes.grid'] = fig_opt['grid']
        if fig_opt['font_size'] > 7:
            plt.rcParams['legend.fontsize'] = fig_opt['font_size'] - 2
        plt.rcParams['legend.loc'] = 'best'
    erase1 = fig_opt['erase_id']
    if erase1 == 'True':  # xml in text
        erase1 = True
    else:
        erase1 = False
    if not fish_name:
        fish_name = fish_xml

    # Q
    nb_q = 20  # number of calculated q
    if qrange[1] > qrange[0]:
        diff = (qrange[1] - qrange[0]) / nb_q
        if qrange[0] == 0:
            qrange[0] = 10**-10   # if exactly zero, you cannot divide anymore
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

    # prepare figure
    if pict:
        c = ['b', 'm', 'r', 'c', '#9932CC', '#800000', 'k', 'g', 'y', '#9F81F7', '#BDBDBD', '#F7819F', 'b', 'm', 'r',
             'c', '#9932CC', '#800000', 'k', 'g', 'y', '#810D0D', '#810D0D', '#9F81F7']
        plt.figure()
        plt.suptitle("ESTIMHAB - HABBY")
        mpl.rcParams['pdf.fonttype'] = 42

    # get fish data
    VH = []
    SPU = []
    for f in range(0, len(fish_xml)):
        # load xml file
        filename = os.path.join(path_bio, fish_xml[f])
        if os.path.isfile(filename):
            doc = ET.parse(filename)
            root = doc.getroot()
        else:
            print('Error: the xml file for the file '+fish_xml[f]+" does not exist")
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
            if not fig_opt:
                fig_opt = output_fig_GUI.create_default_figoption()

            plt.subplot(2, 1, 1)
            plt.grid(True)
            plt.plot(q_all, VH_f, color=c[f])
            if fig_opt['language'] == 0:
                plt.xlabel('Discharge [m$^{3}$/sec]')
                plt.ylabel('Habitat Value[]')
            elif fig_opt['language'] == 1:
                plt.xlabel('Débit [m$^{3}$/sec]')
                plt.ylabel('Valeur habitat []')
            else:
                plt.xlabel('Discharge [m$^{3}$/sec]')
                plt.ylabel('Habitat Value[]')
            plt.legend(fish_name, fancybox=True, framealpha=0.5)
            plt.ylim(0, 1)

            plt.subplot(2, 1, 2)
            plt.grid(True)
            plt.plot(q_all, SPU_f, color=c[f])
            if fig_opt['language'] == 0:
                plt.xlabel('Discharge [m$^{3}$/sec]')
                plt.ylabel('WUA by 100 m')
            elif fig_opt['language'] == 1:
                plt.xlabel('Débit [m$^{3}$/sec]')
                plt.ylabel('SPU par 100 m')
            else:
                plt.xlabel('Discharge [m$^{3}$/sec]')
                plt.ylabel('WUA by 100 m')

        VH.append(VH_f)
        SPU.append(SPU_f)

    if pict:

        # name with date and time
        if not erase1:
            name_pict = "Estimhab_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            name_input = "Estimhab_input_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
        # name without data and time, erase old files
        else:
            name_pict = "Estimhab"
            name_input = "Estimhab_input"
            if os.path.isfile(name_pict + '.png'):
                os.remove(name_pict + '.png')
            if os.path.isfile(name_pict + '.pdf'):
                os.remove(name_pict + '.pdf')
            if os.path.isfile(name_pict + '.jpg'):
                os.remove(name_pict + '.jpg')
            if os.path.isfile(name_pict + '.txt'):
                os.remove(name_pict + '.txt')
            if os.path.isfile(name_input + '.txt'):
                os.remove(name_input + '.txt')


        # save image
        if format1 == 0 or format1 == 1:
            plt.savefig(os.path.join(path_im, name_pict + '.png'), dpi=fig_opt['resolution'], transparent=True)
        if format1 == 0 or format1 == 3:
            plt.savefig(os.path.join(path_im, name_pict + '.pdf'), dpi=fig_opt['resolution'], transparent=True)
        if format1 == 2:
            plt.savefig(os.path.join(path_im, name_pict + '.jpg'), dpi=fig_opt['resolution'], transparent=True)
            # plt.show()

        # text files output
        txt_header = 'Q '
        data = q_all
        for f in range(0, len(fish_name)):
            txt_header += '\tVH_' + fish_name[f] + '\tSPU_' + fish_name[f]
            data = np.vstack((data, VH[f]))
            data = np.vstack((data, SPU[f]))
        txt_header += '\n[m3/sec]'
        for f in range(0, len(fish_name)):
            txt_header += '\t[-]\t[m2/100m]'
        np.savetxt(os.path.join(path_txt, name_pict+'.txt'), data.T, newline=os.linesep, header=txt_header,
                   delimiter='\t')

        # text file input
        txtin = 'Discharge [m3/sec]:\t' + str(qmes[0]) + '\t' + str(qmes[1]) + '\n'
        txtin += 'Width [m]:\t' + str(width[0]) + '\t' + str(width[1]) + '\n'
        txtin += 'Height [m]:\t' + str(height[0]) + '\t' + str(height[1]) + '\n'
        txtin += 'Median discharge [m3/sec]:\t' + str(q50) + '\n'
        txtin += 'Mean substrate size [m]:\t' + str(substrat)+ '\n'
        txtin += 'Minimum and maximum discharge [m3/sec]:\t' + str(qrange[0]) + '\t' + str(qrange[1]) + '\n'
        txtin += 'Fish chosen:\t'
        for n in fish_name:
            txtin += n + '\t'
        txtin = txtin[:-1]
        txtin += '\n'
        txtin += 'Output file:\t' + name_pict+'.txt\n'
        with open(os.path.join(path_txt,name_input + '.txt'), 'wt') as f:
            f.write(txtin)

    del fish_name

    return VH, SPU


def pass_to_float_estimhab(var_name, root):
    """
    This is a function to pass from an xml element to a float

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
    """
    Used to test this module.
    """

    # data from the estimahab2008.xls found in http://www.irstea.fr/en/estimhab
    q = [2, 60]
    w = [29, 45]
    h = [0.21, 1.12]
    q50 = 25
    qrange = [1, 38]
    substrat = 0.25
    fish = ['TRF_ADU', 'TRF_JUV', 'BAF', 'CHA', 'GOU']
    path =  os.path.join('.', 'biology')


    [VH, SPU] = estimhab(q, w, h, q50, qrange, substrat, path, fish, True, True)


if __name__ == '__main__':
    main()
