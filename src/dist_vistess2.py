import numpy as np
from src import mascaret
from src import rubar
import matplotlib.pyplot as plt
from src import Hec_ras06
import time
import bisect


def dist_velocity_hecras(coord_pro, xhzv_data_all, manning_pro, nb_point=-99, eng=1.0, on_profile=[]):
    """
    This function distribute the velocity along the profile using the method from hec-ras
    described in the hydraulic reference manual p 4-20 (Flow distribtion calculation)
    :param coord_pro: the coordinates and elevation of the river bed for each profile (x,y, h, dist along the profile)
    this list is flatten No reach info.
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
    warn1 = True
    for t in range(0, len(xhzv_data_all)):

        # get the data for this time step
        v_pro_t = []
        xhzv_data = xhzv_data_all[t]
        if len(on_profile) > 1:
            xhzv_data = xhzv_data[on_profile]
        warn_point = True
        for p in range(0, len(coord_pro)):
            # (x_p, h_p) points between which the velocity will be calculated
            h_w_p = xhzv_data[p, 1] + xhzv_data[p, 2]
            if nb_point == -99:  # by default use the same point than in coord_pro
                h_p = coord_pro[p][2]
                x_p = coord_pro[p][3]
            elif nb_point > 2:
                x_ini = coord_pro[p][3]
                h_ini = coord_pro[p][2]
                x_p = np.linspace(x_ini[0], x_ini[-1], num=nb_point)
                #x_p = np.arange(x_ini[0], x_ini[-1], (x_ini[-1] - x_ini[0]) / (nb_point-1))
                h_p = np.zeros((len(x_p),))
                for i in range(0, len(x_p)):
                    #indh = np.where(x_ini <= x_p[i])
                    #indh = max(indh[0])
                    indh = bisect.bisect(x_ini, x_p[i]) - 1  # about 3 time quick than max(np.where(x_ini <= x_p[i]))
                    xhmin = x_ini[indh]
                    hmin = h_ini[indh]
                    if indh < len(x_ini)-1:
                        xhmax = x_ini[indh + 1]
                        hmax = h_ini[indh+1]
                        a1 = (hmax - hmin) / (xhmax - xhmin)
                        b1 = hmax - a1 * xhmax
                    else:
                        if warn1:
                            print('Warning: length of the x-coordinate array is too short. \n')
                            warn1 = False
                        a1 = 100000
                        b1 = 100000
                    h_p[i] = a1 * x_p[i] + b1
            else:
                print('Error: Number of point is not sufficient. \n')
                return [-99]
            n = np.array(manning_pro[p], dtype=np.float)  # need a float even if manning input might be an int.
            if len(n) != len(x_p):
                print('Error: Length of Manning data is not coherent with the length of the profil.\n')
                return [-99]

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
                # test if pass from wet to dry or dry to wet
                if h_p[i + 1] < h_w_p < h_p[i] or h_p[i + 1] > h_w_p > h_p[i]:
                    if x_p[i] < x_p[i+1]:
                        a = (h_p[i] - h_p[i+1]) / (x_p[i] - x_p[i+1])   # lin interpolation
                        b = h_p[i] - a*x_p[i]
                        new_x = (h_w_p - b)/a
                    elif x_p[i] == x_p[i+1]:
                        new_x = x_p[i]
                    else:
                        # theorically not useful
                        print('Error: x-coordinates are not increasing.\n')
                        return [-99]
                    h_p = np.concatenate((h_p[:i + 1], [h_w_p], h_p[i + 1:]))
                    x_p = np.concatenate((x_p[:i+1], [new_x], x_p[i+1:]))
                    n = np.concatenate((n[:i+1], [n[i+1]], n[i+1:]))
                # quickly maanged if a profile start under water
                # just add a small bump a the height h_w_p
                # keen h_w_p at the ind 1 to be coherent (used by manage_grid)
            if h_p[0] < h_w_p:
                new_x = (x_p[1] - x_p[0])/2
                h_p = np.concatenate(([h_w_p], h_p[1:]))
                x_p = np.concatenate(([x_p[0]], x_p[1:]))
                n = np.concatenate(([n[0]], [n[1]], n[1:]))

            ind = np.where(h_p <= h_w_p)[0]

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
                # find the min / max height
                hmax = np.max([h0, h_p[1:]], axis=0)
                hmin = np.min([h0, h_p[1:]], axis=0)

                # profil with vertical x (theorically corrected before, but here as extra control)
                vert = np.where(x0 != x1)
                h0 = h0[vert]
                hmax = hmax[vert]
                hmin = hmin[vert]
                x0 = x0[vert]
                x1 = x1[vert]
                n = n[vert]

                # get wetted perimeter, area, hydraulic radius
                wet_pro = np.sqrt((hmax - hmin)**2 + (x1 - x0)**2)
                area = 0.5 * (hmax - hmin) * (x1 - x0) + (x1 - x0) * (h_w_p - hmax)
                area[area == 0] = 0.000001  # should not be needed but just in case
                hyd_rad = area / wet_pro

                # conveyance k for each slice of the profile
                k_s = eng * n**(-1.0) * hyd_rad**(2.0/3.0) * area

                # conveyance K for the whole profile
                a = np.sum(area)
                wp = np.sum(np.sqrt((hmax - hmin)**2 + (x1 - x0)**2))   # wet perimeter profile
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
                if min(ind) > 0:
                    x_here = np.concatenate(([x_p0[min(ind) - 1]], x0, [x_p0[max(ind)]]))
                    h_here = np.concatenate(([h_p0[min(ind) - 1]], h0, [h_p0[max(ind)]]))
                else:
                    if x_p0[0] > 0:
                        x_here = np.concatenate(([x_p0[0]*0.99], x0, [x_p0[max(ind)]]))
                    elif x_p0[0] == 0:
                        x_here = np.concatenate(([-1e-5], x0, [x_p0[max(ind)]]))
                    else:
                        x_here = np.concatenate(([x_p0[0] * 1.01], x0, [x_p0[max(ind)]]))
                    h_here = np.concatenate(([h_p0[0]*1.01], h0, [h_p0[max(ind)]]))
                h_here = h_w_p - h_here  # water hieght and not elevation
                v_here = np.concatenate(([0], v, [0]))
                v_pro_t.append([x_here, h_here, v_here])
            else:
                x_here = [x_p[0]] + x_p
                v_pro_t.append(([], [], []))

        vh_pro.append(v_pro_t)

    return vh_pro


def plot_dist_vit(v_pro, coord_pro, xhzv_data, plot_timestep, pro, name_pro=[], on_profile=[], zone_v_all =[], data_profile = [], xy_h_all = []):
    """
    this function plot the calculated velocity distribution
    :param v_pro: the calculated velcocity distribution by time step
    :param coord_pro: the coordinate of the profiles
    :param xhzv_data: the output data from the model, before the velocity distrbution
    :param plot_timestep: which time step to be plottied
    :param name_pro: the name of the profile (optionnal just for the title)
    :param pro: which porfile to be plotted
    :param on_profile, select the data which is on the profile
    :param zone_v: output from hec-ras used to test dist_vitesse
    :param data_profile: output from hec-ras used to test dist_vitesse
    :param xy_h: output from hec-ras used to test dist_vitesse
    :return: figures
    """
    # are we here to test the output
    if zone_v_all:
        test_v = True
    else:
        test_v = False

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
                return [-99]
            h_here = xhzv_data_t[p][1] + xhzv_data_t[p][2]
            plt.fill_between(coord_pro_p[3], coord_pro_p[2], h_here, where=coord_pro_p[2] < h_here,
                             facecolor='blue', alpha=0.5, interpolate=True)
            plt.plot(coord_pro_p[3], coord_pro_p[2], 'k')
            a = 0.95 * min(coord_pro_p[3])
            if a == 0:
                plt.xlim(-0.05, 1.05 * max(coord_pro_p[3]))
            else:
                plt.xlim(a, 1.05 * max(coord_pro_p[3]))
            plt.xlabel('Distance along the profile [m or ft]')
            plt.ylabel('Height of the river bed [m or ft]')
            plt.title(' ')
            ax1 = plt.subplot(212)
            v_pro_p = v_pro[t][p]
            plt.step(v_pro_p[0], v_pro_p[2], where='post')
            plt.axhline(y=xhzv_data_t[p][3], linewidth=0.5, color='k')
            if a == 0:
                plt.xlim(-0.05, 1.05 * max(coord_pro_p[3]))
            else:
                plt.xlim(a, 1.05 * max(coord_pro_p[3]))
            #if np.sum(v_pro_p[2]) != 0:
              #  plt.ylim(0, max(v_pro_p[2])*1.05)
            plt.xlabel('Distance along the profile [m or ft]')
            plt.ylabel('Velocity [m/sec or ft/sec]')
            # only if use this fonction to compare velocity output
            if test_v:
                # directly copied from hec_ras06.py
                xy_h = xy_h_all[t]
                zone_v = zone_v_all[t]
                xz = data_profile[p]
                xyh_i = xy_h[p]
                v_xy_i = zone_v[p]
                hi = xyh_i[:, 3]
                # find the water limits
                h0 = hi[0] + xz[0, 1]
                wet = np.squeeze(np.where(hi > 0))
                p1 = wet[0]
                p2 = wet[-1]
                if xz[p1, 0] != xz[p1 - 1, 0]:  # not vertical profile
                    a1 = (xz[p1, 1] - xz[p1 - 1, 1]) / (xz[p1, 0] - xz[p1 - 1, 0])
                    b1 = xz[p1, 1] - a1 * xz[p1, 0]
                    xint1 = (h0 - b1) / a1
                else:  # vertical profile
                    xint1 = xz[p1, 0]
                if wet[0] == 0:  # if the left overbank is totally wet
                    xint1 = xz[0, 0]
                if p2 < len(xz) - 1:  # if at the end of the profile
                    if xz[p2, 0] != xz[p2 + 1, 0]:  # not vertical profile
                        a2 = (xz[p2, 1] - xz[p2 + 1, 1]) / (xz[p2, 0] - xz[p2 + 1, 0])
                        b2 = xz[p2, 1] - a2 * xz[p2, 0]
                        xint2 = (h0 - b2) / a2
                    else:
                        xint2 = xz[p2 + 1, 0]
                else:
                    xint2 = xz[p2, 0]
                v_xy_i_wet = v_xy_i[(xint1 <= v_xy_i[:, 2]) & (v_xy_i[:, 2] <= xint2), 2:]
                if len(v_xy_i_wet) > 0:
                    v_xy_i_wet = np.vstack(([[0, 0], [xint1, v_xy_i[0, 3]], v_xy_i_wet, [xint2, 0]]))
                else:  # case with no velocity in the water
                    v_xy_i_wet = np.vstack(([[0, 0], [xint1, v_xy_i[0, 3]], [xint2, 0]]))
                # print velocity
                plt.step(v_xy_i_wet[:, 0], v_xy_i_wet[:, 1], where='post', color='r')
            plt.legend(('distributed vel.', 'original velocity', 'hec-ras velocity'))
        plt.show()


def preparetest_velocity(coord_pro, vh_pro_orr, v_in):
        """
        This function takes the output from hec-ras, with the velocity distrbution already present, and
        transform these output into input for dist_vel.
        :param coord_pro: the coordinate of the profile (x,y,h,dist along profile)
        :param vh_pro_orr: the velocity distribution which is the output from hec ras (produced by hec-ras06.py)
        :param v_in the uni-dimensional velocity
        :return:
        """
        xhzv_data = []
        for t in range(0, len(vh_pro_orr)):
            vh_pro_t = vh_pro_orr[t]
            xhzv_data_t = []
            for p in range(0, len(coord_pro)):
                coord_pro_p = coord_pro[p]
                vh_p = vh_pro_t[p]
                ind = np.argmin(coord_pro_p[2])
                z = min(coord_pro_p[2])
                #ind_vh = np.argmin(abs(vh_p[0] - coord_pro_p[3][ind]))
                ind_vh = np.argmax(vh_p[1])
                distx = vh_p[0][ind_vh]
                h = vh_p[1][ind_vh]
                v = v_in[p]
                xhzv_data_t.append([distx, h, z, v])
            xhzv_data.append(np.array(xhzv_data_t))

        return xhzv_data


def get_manning(manning1, nb_point, nb_profil):
    """
    A fucntion to create an array with the different manning value. Having one manning value for each point will be useful
    if one has a river with various manning value, even if it is longer now
    NOT FINISHED
    :param manning1: the manning value (can be a value or an array)
    :param nb_point: the number of velocity point by profile
    :param nb_profil: the number of profile
    :return:
    """
    manning_array = []
    if not isinstance(nb_point, int):
        print('Error: The number of velocity point is not understood (int needed) \n')
        return
    if nb_point == -99:
        print('Error: Manning not finished yet \n')
    if isinstance(manning1, float):
        for p in range(0, nb_profil):
             manning_array.append([manning1] * nb_point)
    else:
        print('Error: Manning not finished yet \n')

    return manning_array


def main():

        # # distrbution vitesse mascaret
        # path = r'D:\Diane_work\output_hydro\mascaret'
        # #path = r'D:\Diane_work\output_hydro\mascaret\Bort-les-Orgues'
        # file_geo = r'mascaret0.geo'
        # file_res = r'mascaret0_ecr.opt'
        # file_gen = 'mascaret0.xcas'
        # [coord_pro, coord_r, xhzv_data, name_pro, name_reach, on_profile, nb_pro_reach] = \
        #                     mascaret.load_mascaret(file_gen, file_geo, file_res, path, path, path)
        # manning_value = 0.025
        # manning = []
        # nb_point = 70
        # for p in range(0, len(coord_pro)):
        #     manning.append([manning_value] * nb_point)
        #
        # v_pro = dist_velocity_hecras(coord_pro, xhzv_data, manning, nb_point, 1.0, on_profile)
        # plot_dist_vit(v_pro, coord_pro, xhzv_data, [1], [-1], name_pro, on_profile)

        # hec-ras test
        # path_test = r"C:\Users\diane.von-gunten\Documents\HEC Data\HEC-RAS\1D Steady Flow Hydraulics\Chapter 4 Example Data"
        # path_im = r'D:\Diane_work\Grid\distribution_vitesse\fig_hec'
        # name_geo = r"EX1_dist_m.g01"
        # name_xml = r"EX1_dist_m.RASexport.sdf"
        # [coord_pro, vh_pro_orr, nb_pro_reach, zone_v, data_profile, xy_h] = Hec_ras06.open_hecras(name_geo, name_xml, path_test, path_test, path_im, False)
        # # case EX1
        # # v for t = 0 based on cross section output (in hec_ras: View-> detailed output table. Find Avg. Vel)
        # #v_in = [2.04, 1.95, 1.98, 3.06, 2.98, 2.94, 2.90, 2.28, 2.42, 2.42]  #feet
        # v_in = [1.49, 1.42, 1.44, 2.30, 2.24,2.22, 2.19, 1.72, 1.84, 1.84] #m
        # xhzv_data = preparetest_velocity(coord_pro, vh_pro_orr, v_in)
        # manning_value = 0.040
        # manning = []
        # nb_point = 200#40
        # for p in range(0, len(coord_pro)):
        #      manning.append([manning_value] * nb_point)
        # vh_pro = dist_velocity_hecras(coord_pro,xhzv_data, manning, nb_point)
        # plot_dist_vit(vh_pro, coord_pro, xhzv_data, [0], range(0, 9),[],[], zone_v, data_profile, xy_h)



        # the same with rubar
        path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\Gregoire\1D\LE2013\LE2013\LE13'
        mail = 'mail.LE13'
        geofile = 'LE13.rbe'
        data = 'profil.LE13'
        #path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\trubarbe\1D\RubarBE_four_0'
        #mail = 'mail.LE13'
        #geofile = 'four.rbe'
        #data = 'profil.four'
        [xhzv_data_all, coord_pro, lim_riv] = rubar.load_rubar1d(geofile, data, path, path, path, False)

        manning_value_center = 0.025
        manning_value_border = 0.06
        manning = []
        # write this function better
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

        manning = []
        nb_point = 200
        manning = get_manning(manning_value_center, nb_point, len(coord_pro))
        v_pro = dist_velocity_hecras(coord_pro, xhzv_data_all, manning, nb_point)
        if v_pro:
            plot_dist_vit(v_pro, coord_pro, xhzv_data_all, [3], [1,2,3])


if __name__ == '__main__':
    main()



