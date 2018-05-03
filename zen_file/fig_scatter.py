"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V / 
|  _  ||  _  || ___ \ ___ \ \ /  
| | | || | | || |_/ / |_/ / | |  
\_| |_/\_| |_/\____/\____/  \_/  

Copyright (c) IRSTEA-EDF-AFB 2017-2018

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
import matplotlib.pyplot as plt

plt.figure()
        cm = plt.cm.get_cmap('gist_ncar')
        for r in range(0, len(inter_vel_all)):
            inter_vel = inter_vel_all[r]
            point_c = point_c_all[r]
            if len(point_c) > 0 and len(point_c) == len(inter_vel):
                sc = plt.scatter(point_c[:, 0], point_c[:, 1], c=inter_vel, vmin=np.nanmin(inter_vel), vmax=np.nanmax(inter_vel), cmap=cm, edgecolors='none', s=50000/len(point_c[:,0]))
            else:
                print('Warning: The velocity in one reach could not be drawn. \n')
                sc = plt.scatter([0,1], [0,1], c=[0,1], cmap=cm)
        cbar = plt.colorbar(sc)
        cbar.ax.set_ylabel('Velocity [m/sec]')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Interpolated velocity')
        plt.savefig(os.path.join(path_im, "Vel_inter_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"))
        plt.savefig(os.path.join(path_im, "Vel_inter_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"))
        plt.close()

        plt.figure()
        cm = plt.cm.get_cmap('terrain')
        for r in range(0, len(inter_h_all)):
            inter_h = inter_h_all[r]
            point_c = point_c_all[r]
            if len(point_c) > 0 and len(point_c) == len(inter_h):
                sc = plt.scatter(point_c[:, 0], point_c[:, 1], c=inter_h, vmin=0, vmax=np.nanmax(inter_h),
                                     cmap=cm, edgecolors='none',  s=50000/len(point_c[:, 0]))
            else:
                print('Warning: The water height in one reach could not be drawn. \n')
                sc = plt.scatter([0, 1], [0, 1], c=[0,1], cmap=cm)
        cbar = plt.colorbar(sc)
        cbar.ax.set_ylabel(' Water height [m]')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Interpolated water height')
        plt.savefig(os.path.join(path_im, "Water_height_inter" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"))
        plt.savefig(os.path.join(path_im, "Water_height_inter" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"))
        plt.close()
