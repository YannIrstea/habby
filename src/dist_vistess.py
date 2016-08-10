import numpy as np
from src import mascaret
from src import rubar
import matplotlib.pyplot as plt
from src import Hec_ras06


def dist_velocity_hecras(coord_pro, xhzv_data_all, manning_pro, nb_point=-99, on_profile=[], eng=1.0):
    """
    This function distribute the velocity along the profile using the method from hec-ras
    described in the hydraulic reference manual p 4-20 (Flow distribtion calculation)
    :param coord_pro: the coordinates and elevation of the river bed for each profile (x,y, h, dist along the profile)
    !!!!!!this list is flatten compred to the usual coord_pro !!!!!! No reach info
    :param xhzv_data_all: water height and velocity at each profile, 1D
    :param manning_pro the manning coefficient for zone between point of each profile
    for a particular profile, the length of manning_pro is the length of coord_pro[0]
    :param nb_point: number of velocity points (-99 takes the profil form as the velocity points)
    :param on_profile: Mascaret also gives outputs in poitns between profile. on_profile is true if the results are
     close or on the profile (les than 3cm of difference), not important for rubar or other
    :param eng: in case the output from hec-ras are in US unit (eng=1 for SI unit and 1.486 for US unit)
    :return: the velocity for each profile by time step (x,v)
    """
    vh_pro = []

    for t in range(0, len(xhzv_data_all)):

        # get the data for this time step
        v_pro_t = []
        xhzv_data = xhzv_data_all[t]
        if len(on_profile) > 1:
            xhzv_data = xhzv_data[on_profile]
        warn_point = True

        for p in range(0, len(coord_pro)):

            # (x_p, h_p) points btween which the velocity will be calculated
            h_w_p = xhzv_data[p, 1] + xhzv_data[p, 2]
            if nb_point == -99:
                h_p = coord_pro[p][2]
                x_p = coord_pro[p][3]
            elif nb_point > 2:
                x_ini = coord_pro[p][3]
                h_ini = coord_pro[p][2]
                x_p = np.arange(x_ini[0], x_ini[-1], (x_ini[-1] - x_ini[0])/nb_point)
                h_p = np.zeros((len(x_p),))
                for i in range(0, len(x_p)):
                    indh = np.where(x_ini <= x_p[i])
                    indh = max(indh[0])
                    xhmin = x_ini[indh]
                    xhmax = x_ini[indh+1]
                    hmin = h_ini[indh]
                    hmax = h_ini[indh+1]
                    a = (hmax - hmin) / (xhmax - xhmin)
                    b = hmax - a * xhmax
                    h_p[i] = a * x_p[i] + b
            else:
                print('Error: Number of point is not sufficient. \n')

            n = np.array(manning_pro[p], dtype=np.float)  # need a float even if manning input might be an int.

            # add extra point where the profile is getting out of the water
            # possibility of an island, so no easy [h_wp h[h>h_wp] h_wp]
            for i in range(0, len(h_p)-1):

                # if the profile is not regular
                if x_p[i] > x_p[i+1]:
                    if warn_point:
                        warn_point = False
                        print('Warning: the x-coordinates of the profile decreases. Some points are neglected.\n')
                    x_p[i+1] = x_p[i]
                    h_p[i+1] = h_p[i]
                    n[i+1] = n[i]

                if h_p[i + 1] < h_w_p < h_p[i] or h_p[i + 1] > h_w_p > h_p[i]:
                    if x_p[i] < x_p[i+1]:
                        a = (h_p[i] - h_p[i+1]) / (x_p[i] - x_p[i+1])   # lin interpolation
                        b = h_p[i] - a*x_p[i]
                        new_x = (h_w_p - b)/a
                    elif x_p[i] == x_p[i+1]:
                        new_x = x_p[i]
                    else:
                        # theorically mot useful, but
                        print('Error: x-coordinates are not increasing.\n')
                    h_p = np.concatenate((h_p[:i + 1], [h_w_p], h_p[i + 1:]))
                    x_p = np.concatenate((x_p[:i+1], [new_x], x_p[i+1:]))
                    n = np.concatenate((n[:i+1], [n[i+1]], n[i+1:]))
            ind = np.where(h_p <= h_w_p)
            ind = ind[0]

            # if the profile is not totally dry
            if len(ind) > 0:

                # prep
                h_p0 = h_p
                h_p = h_p[ind]
                x_p0 = x_p
                x_p = x_p[ind]
                n = n[ind]
                n = n[:-1]  # we need the manning of the zones between each point
                x0 = x_p[:-1]
                h0 = h_p[:-1]
                x1 = x_p[1:]
                hmax = np.max([h0, h_p[1:]], axis=0)
                hmin = np.min([h0, h_p[1:]], axis=0)

                # profil with vertical x
                vert = np.where(x0 != x1)
                x0 = x0[vert]
                x1 = x1[vert]
                hmax = hmax[vert]
                hmin = hmin[vert]
                n = n[vert]

                # get wetted perimeter, area, hydraulic radius
                wet_pro = np.sqrt((hmax - hmin)**2 + (x1 - x0)**2) + (h_w_p - hmin) + (h_w_p - hmax) + (x1-x0)
                area = 0.5 * (hmax - hmin) * (x1 - x0) + (x1 - x0) * (h_w_p - hmax)
                area[area == 0] = 0.000001  # should not be needed but just in case
                hyd_rad = area / wet_pro

                # conveyance k for each slice of the profile
                k_s = eng * n**(-1.0) * hyd_rad**(2.0/3.0) * area

                # conveyance K for the whole profile
                a = np.sum(area)
                wp = np.sum(np.sqrt((hmax - hmin)**2 + (x1 - x0)**2)) + (x_p[-1] - x_p[0])  # wet perimeter profile
                r = a/wp
                k_tot = eng/np.mean(n) * r**(2.0/3.0) * a

                # correcting conveyance by slice
                k_s_tot = np.sum(k_s)
                ratio = k_tot / k_s_tot
                k_s = ratio * k_s

                # slope of the energy gradeline
                sqrt_sf = (xhzv_data[p, 3] * a) / k_tot

                # distributed velocity for this profile
                v = (k_s * sqrt_sf) / area

                # need to get a velocity of zero in place without water (hence without velocity)
                x_here = np.concatenate(([x_p0[min(ind) - 1]], x0, [x_p0[max(ind)]]))
                h_here = np.concatenate(([h_p0[min(ind) - 1]], h0, [h_p0[max(ind)]]))
                v_here = np.concatenate(([0], v, [0]))
                v_pro_t.append([x_here, h_here, v_here])
            else:
                x_here = [x_p[0]] + x_p
                v_pro_t.append([x_here, [-99] * len(x_here)])

        vh_pro.append(v_pro_t)

    return vh_pro

def plot_dist_vit(v_pro, coord_pro, xhzv_data, plot_timestep, pro, name_pro=[], on_profile=[]):
    """
    this function plot the calculated velocity distribution
    :param v_pro: the calculated velcocity distribution by time step
    :param coord_pro: the coordinate of the profiles
    :param xhzv_data: the output data from the model, before the velocity distrbution
    :param plot_timestep: which time step to be plottied
    :param name_pro: the name of the profile (optionnal just for the title)
    :param pro: which porfile to be plotted
    :param on_profile, select the data which is on the profile
    :return: figures
    """

    for t in plot_timestep:
        xhzv_data_t = xhzv_data[t]
        if len(on_profile) > 1:
            xhzv_data_t = xhzv_data_t[on_profile]
        for p in pro:
            plt.figure()
            if name_pro:
                plt.suptitle('Profile ' + name_pro[p] + ' at the time step ' + str(t))
            else:
                plt.suptitle('Profile ' + str(p) + ' at the time step ' + str(t))
            ax1 = plt.subplot(211)
            try:
                coord_pro_p = coord_pro[p]
            except IndexError:
                print('Error: The profile number exceed the total number of profiles. Cannot be plotted.\n')
                return
            h_here = xhzv_data_t[p][1] + xhzv_data_t[p][2]
            plt.fill_between(coord_pro_p[3], coord_pro_p[2], h_here, where=coord_pro_p[2] < h_here,
                             facecolor='blue', alpha=0.5, interpolate=True)
            plt.plot(coord_pro_p[3], coord_pro_p[2], 'k')
            a = 0.95 * min(coord_pro_p[3])
            if a == 0:
                plt.xlim(-0.05, 1.05 * max(coord_pro_p[3]))
            else:
                plt.xlim(a, 1.05 * max(coord_pro_p[3]))
            plt.xlabel('Distance along the profile [m]')
            plt.ylabel('Height of the river bed [m]')
            plt.title(' ')
            ax1 = plt.subplot(212)
            v_pro_p = v_pro[t][p]
            plt.step(v_pro_p[0], v_pro_p[2], where='post')
            plt.axhline(y=xhzv_data_t[p][3], linewidth=0.5, color='k')
            if a == 0:
                plt.xlim(-0.05, 1.05 * max(coord_pro_p[3]))
            else:
                plt.xlim(a, 1.05 * max(coord_pro_p[3]))
            if np.sum(v_pro_p[2]) != 0:
                plt.ylim(0, max(v_pro_p[2])*1.05)
            plt.legend(('distributed vel.', 'original velocity'))
            plt.xlabel('Distance along the profile [m]')
            plt.ylabel('Velocity [m/sec]')

        plt.show()


def main():

        # distrbution vitesse mascaret
        path = r'D:\Diane_work\output_hydro\mascaret'
        path = r'D:\Diane_work\output_hydro\mascaret\Bort-les-Orgues'
        file_geo = r'mascaret0.geo'
        file_res = r'mascaret0_ecr.opt'
        file_gen = 'mascaret0.xcas'
        [coord_pro, coord_r, xhzv_data, name_pro, name_reach, on_profile, nb_pro_reach] = \
                            mascaret.load_mascaret(file_gen, file_geo, file_res, path, path, path)
        manning_value = 0.025
        manning = []
        nb_point = 145
        for p in range(0, len(coord_pro)):
            manning.append([manning_value] * nb_point)

        v_pro = dist_velocity_hecras(coord_pro, xhzv_data, manning, nb_point, on_profile)
        plot_dist_vit(v_pro, coord_pro, xhzv_data, [3], [3, 4], name_pro, on_profile)

        # # hec-ras test
        # path_test = r"C:\Users\diane.von-gunten\Documents\HEC Data\HEC-RAS\1D Steady Flow Hydraulics\Chapter 4 Example Data"
        # name_geo = r"EX1.g01"
        # name_xml = r"EX1.O01.xml"
        # [xyh, zone_v] = Hec_ras06.open_hecras(name_geo, name_xml, path_test, path_test, '.', False)
        # manning_value = 0.035
        # manning = []
        # xyh0 = xyh[0]  # first time step first reach
        # zone_v0 = zone_v[0]
        # coord_pro = []
        # xhzv_data = np.zeros((len(xyh0), 4))
        # nb_point = 45
        # for p in range(0, len(xyh0)):
        #     manning.append([manning_value] * nb_point)
        #     xyh0_p = xyh0[p]
        #     x = []
        #     y = []
        #     z = []
        #     for i in range(0, len(xyh0_p)):
        #         x.append(xyh0[p][i][0])
        #         y.append(xyh0[p][i][1])
        #         z.append(xyh0[p][i][2])
        #     coord_pro.append([x, y, z])
        #     if p == 0:
        #         xhzv_data[p, :] = [0, xyh0[p][0][2], 0, zone_v0[0][0][2]]
        #     else:
        #         xriv = np.sqrt((xyh0[p][0][0] - xyh0[p-1][0][0])**2 + (xyh0[p][0][1] - xyh0[p-1][0][1])**2 )
        #         xhzv_data[p, :] = [xriv, xyh0[p][0][2], 0, zone_v0[p-1][0][3]]
        # v_pro = dist_velocity_hecras(coord_pro, [xhzv_data], manning, nb_point)
        # plot_dist_vit(v_pro, coord_pro, xhzv_data, [0], [2,3])



        # # the same with rubar
        # path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\Gregoire\1D\LE2013\LE2013\LE13'
        # mail = 'mail.LE13'
        # geofile = 'LE13.rbe'
        # data = 'profil.LE13'
        # [xhzv_data_all, coord_pro, lim_riv] = rubar.load_rubar1d(geofile, data, path, path, path, False)
        #
        # manning_value_center = 0.025
        # manning_value_border = 0.06
        # manning = []
        # # write this function better
        # for p in range(0, len(coord_pro)):
        #     x_manning = coord_pro[p][0]
        #     manning_p = [manning_value_border] * len(x_manning)
        #     lim1 = lim_riv[p][0]
        #     lim2 = lim_riv[p][2]
        #     ind = np.where((coord_pro[p][0] < lim2[0]) & (coord_pro[p][1] < lim2[1]) &\
        #               (coord_pro[p][0] > lim1[0]) & (coord_pro[p][1] > lim1[1]))
        #     ind = ind[0]
        #
        #     for i in range(0, len(ind)):
        #         manning_p[ind[i]] = manning_value_center
        #     manning.append(manning_p)
        #
        # v_pro = dist_velocity_hecras(coord_pro, xhzv_data_all, manning, -99)
        # if v_pro:
        #     plot_dist_vit(v_pro, coord_pro, xhzv_data_all, [3], [1,2,3])


if __name__ == '__main__':
    main()



