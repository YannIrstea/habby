.. HABBY documentation master file, created by
   sphinx-quickstart on Tue Jan  3 14:37:35 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to HABBY's documentation!
==================================

.. toctree::
   :maxdepth: 4
   :caption: Contents
  
HABBY is a program to estimate the habitat of fish using various hydrological models and preference curve as input. 

How to execute HABBY
================================
To execute HABBY:
	* Go to folder which contains habby.py using the command line.
	* Open the command line and type python habby.py.
	
The python version should be 3.4. HABBY should also function with most of the python 3 distributions.

If a module is missing, it is possible to install it using pip ("pip install -m *module_name*"). Obviously, pip needs to installed, which should be done by default in python 3.4. If you want to be sure to have the same version of the module than originally, go to the folder zen_file/wheele with the command line and install the missing module from there (something similar to "pip install -m *.whl*"). Not all modules are in this folder, only the ones which were difficult to install.

Main(	) and source code
==========================
The source code is separated in two folders: one folder which contain the code source for the graphical user interface (GUI) and one folder for the rest of the code source. 

The dependency between the different part of the source code can be visualized in the mindmap real_GUI.xmind (xmind should be installed).

The main of HABBY is habby.py. It has the usual form for an application using PyQt5.  The main() creates an application of QWidget and call the Main_Windows class, which we will discuss shortly. The last line closes the application. 


Graphical interface
===================================
Here is the list of all modules contains in the src_GUI folder.

Main_windows of HABBY
--------------------------------
in src_GUI/Main_Windows_1.py

.. automodule:: src_GUI
   :members:
   :undoc-members:
   
.. automodule:: src_GUI.Main_windows_1
   :members:
   :undoc-members:
   
Hydrological information - GUI
---------------------------------
in src_GUI/hydro_GUI_2.py

This python module contains the class which forms the hydrological tab in HABBY.
It contains the information for the graphical interface and make the link with the scripts
used for the hydrological calculations.
   
.. automodule:: src_GUI.hydro_GUI_2
   :members:
   :undoc-members:
   :show-inheritance:
   
Figure Option - GUI
------------------------------
 in src_GUI/output_fig_GUI.py
 
 This part is not finished. The idea is to let the user select various options to create
 the figures, notably the colour or the size of the text. 
 
.. automodule:: src_GUI.output_fig_GUI
   :members:
   :undoc-members:
   
The Stathab model - GUI
------------------------------

.. automodule:: src_GUI.stathab_GUI
   :members:
   :undoc-members:
   
Estimhab - GUI
----------------------------------
in src_GUI/estimhab_GUI.py

.. automodule:: src_GUI.estimhab_GUI
   :members:
   :undoc-members:
   
Biological data - Estimhab
""""""""""""""""""""""""""""""""""""""

The biological data, i.e., the preference curves of Estimhab, are saved in xml files
situated in the folder given by the path written in the xml project file under the 
attribute Path_bio. By default, it is HABBY/biology. It is possible to change this folder
using the GUI. 

Estimhab is a statistical model, which functions using mathematical regressions. 
The different regressions (or preference curve) of each fish are described in an xml file 
whose format is given here.

Conceptually, the regressions R are of two types:

*	Type 0	 	R = C * Q^{m1} * exp(m2*Q)
*	Type 1		R = C * (1+m1*exp(m2*Q))

Where Q is the discharge, m1 and m2 are coefficients which depend on the fish type, and C is a
constant which depends on the stream characteristic and the fish type. 

The constant C is of the form C = a + ∑ ai * ln(Si) where a and ai are coefficients which depend on 
the fish type. Si are particular stream characteristics. Which characteristics should be used is a 
function of the fish type and is so given in the xml file. The value of S i is a function of the stream
and is calculated by the program.
 
In the xml file, 

*	Attribute coeff_q: Give the main coefficients of the regression (m1 and m2)
*	Attribute func_q : Give the type of regression R used.  Type 0 and type 1, as described above, are known by HABBY.
*	Attribute coeff_const: Give the coefficient used to construct the constant C (a, a1, a2, a3,…). The number of coefficient differs for each fish, but should be at least one.
*	Attribute var_const: Give which type of stream characteristics is used. This is not the value of the particular characteristic, but only which type is used. The following list of type is accepted:

	*	0 for Q50, natural median discharge
	*	1 for H50, the height of the stream at q50
	*	2 for L50, the width of the stream at q50
	*	3 for V50, the velocity of the stream at q50
	*	4 for Re50, the discharge divided by 10 times the width at Q50
	*	5 for Fr50, the Froude number at Q50
	*	6 for Dh50, the mean substrate height divided by h50
	*	7 for Exp(Dh50). Erase the log() of this particular term of the constant

   
Calculation of fish's habitat
=============================================
The src folder contains the python module which are not linked with the graphical user interface.

.. automodule:: src
   :members:
   :undoc-members:

Hec-ras model 1D
----------------------------------
in src/Hec_ras06.py

This module contains the functions used to load the outputs from the hec-ras model in 1.5D.

.. automodule:: src.Hec_ras06
   :members:
   :undoc-members:

Notes on hec-ras outputs
""""""""""""""""""""""""""""""""""""""

*	Data in HEC-RAS can be geo-referenced or not georeferenced. It is advised to geo-reference
	all model in HEC-RAS. If the model is not geo-referenced, the function makes some assumptions to 
	load the data: 1) the river profile are straight and perpendicular to the river.  
	2) the last profile is at the end of the river. 
*	To geo-reference a model in hec_ras: In the “geometric data” window, GIS tool, GIS Cut Line, Accept Display location, choose all profile
*	Numerical data are sometime not separated (0.4556 0.3453233.454 05.343). In this case, the number of digit is assumed to be 8 for the profile and 16 for the river coordinates. 
*	Part of the profile can be vertical: The function also functions in this case.
*	There is sometimes more than one reach in the modelled river and these reaches sometimes form loops: The function load each reach one after the other.
*	The river reaches are sometimes not in the same order in the xml file and in the .goX file. The order of the .goX is used by the function. Reach are automatically re-ordered.
*	If the river is straight, the coordinates of the river are given differently. The function try to load the river in the “straight” style if the usual style fail. 
*	The .goX file includes data on bridges and culvert. Currently, the function neglects this information.
*	Sometimes distances between profiles are not given in the .goX file. The function neglects the distance data of this profile as long as it is not the last profile. 
*	The velocity data for the end and the beginning of the river profile is indicated by a large number (example 1.23e35 or -1.234e36). The function considers that velocity info is situated at the start of the profile if x>-1e30 and at the end of the profile if x> 1e30.
*	There are two concepts called “profile” in HEC-RAS: The river profiles and the simulation profiles. The river profiles are the geometry perpendicular to the river and the simulation profile are the different simulations. 
*	Data in many of the example cases of HEC-RAS are in foot and miles. 1 miles = 5280 foot, and not 1000 foot.


Hec-ras model 2D
----------------------------------
in src/Hec_ras2D.py

This module contains the functions used to load the outputs from the hec-ras model in 2D.

.. automodule:: src.hec_ras2D
   :members:
   :undoc-members:

Mascaret
-------------------------

This module contains the functions used to load the outputs from the mascaret model.

.. automodule:: src.mascaret
   :members:
   :undoc-members:

River 2D
-------------------------


This module contains the functions used to load the outputs from the River2D model.

.. automodule:: src.river2d
   :members:
   :undoc-members:

Rubar
---------------------------

This module contains the functions used to load the Rubar data in 2D and 1D.

.. automodule:: src.rubar
   :members:
   :undoc-members:

Telemac
--------------------------

This module contains the function used to load the Telemac data.

.. automodule:: src.selafin_habby1
   :members:
   :undoc-members:


Load HABBY hdf5 file
--------------------------------------
This module contains some functions to load and manage hdf5 input/outputs. This is still in progress.

.. automodule:: src.load_hdf5
   :members:
   :undoc-members:

Form of the hdf5 files
""""""""""""""""""""""""""""""""""""
Here is the actual form of the hdf5 containing the 2D hydrological data.

*	Number of timestep: Data_gen/Nb_timestep
*	Number of reach: Data_gen/Nb_reach
*	Connectivity table for the whole profile: Data_2D/Whole_Profile/Reach_<r>/ikle
*	Connectivity table for the wetted area (by time step): Data_2D/Timestep<t>/Reach_<r>/ikle
*	Coordinates for the whole profile: Data_2D/Whole_Profile/Reach_<r>/point_all
*	Coordinates for the wetted area (by time steps): Data_2D/Timestep<t>/Reach_<r>/point_all
*	Data for the velocity: Data_2D/Timestep<t>/Reach_<r>/inter_vel_all
*	Data for the height:  Data_2D/Timestep<t>/Reach_<r>/inter_h_all

Here is the actual form of the hdf5 containing the substrate data.

*	the coordinate of the point forming the substrate "grid": coord_p_sub/
*	the connectivity table of the substrate "grid": ikle_sub/
*       Substrate data; not done yet



Velocity distribution
--------------------------------
.. automodule:: src.dist_vistess2
   :members:
   :undoc-members:

.. automodule:: src.manage_grid_8.py
   :members:
   :undoc-members:
.. automodule:: src.estimhab
   :members:
   :undoc-members:
.. automodule:: src.stathab_c
   :members:
   :undoc-members:
.. automodule:: src.substrate
   :members:
   :undoc-members:





Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
