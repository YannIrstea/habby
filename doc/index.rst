.. HABBY documentation master file, created by
   sphinx-quickstart on Tue Jan  3 14:37:35 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to HABBY's documentation!
==================================

.. toctree::
   :maxdepth: 3
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

It is also possible to call habby from the command line without the GUI. For this, the script called habby_cmd.py is used.


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
 
This python module lets the user select various options to create the figures, notably the colormap or the size of the text.
It is also wehre the user select the needed outputs.

 
.. automodule:: src_GUI.output_fig_GUI
   :members:
   :undoc-members:
   
The Stathab model - GUI
------------------------------
in src_GUI/stathab_GUI.py

.. automodule:: src_GUI.stathab_GUI
   :members:
   :undoc-members:
   
FStress model - GUI
------------------------------------
in src_GUI/fstress_GUI.py

.. automodule:: src_GUI.fstress_GUI
   :members:
   :undoc-members:
   
Estimhab - GUI
----------------------------------
in src_GUI/estimhab_GUI.py

.. automodule:: src_GUI.estimhab_GUI
   :members:
   :undoc-members:

Information Biological and Run habitat
---------------------------------------
in src_GUI/bio_info_GUI.py

This python module is where the biological info is managed and shown to the user.
It is also where the user can run the habitat calculation.

.. automodule:: src_GUI.bio_info_GUI
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

The constant C is of the form C = a + \sum ai * ln(Si) where a and ai are coefficients which depend on 
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
in src/mascaret.py

This module contains the functions used to load the outputs from the mascaret model.

.. automodule:: src.mascaret
   :members:
   :undoc-members:

River 2D
-------------------------
in src/river2D.py

This module contains the functions used to load the outputs from the River2D model.

.. automodule:: src.river2d
   :members:
   :undoc-members:

Rubar
---------------------------
in src/rubar.py

This module contains the functions used to load the Rubar data in 2D and 1D.

.. automodule:: src.rubar
   :members:
   :undoc-members:

Telemac
--------------------------
in src/selafin_habby1.py

This module contains the functions used to load the Telemac data.

.. automodule:: src.selafin_habby1
   :members:
   :undoc-members:

LAMMI
------------------------
in src/lammi.py

This module contains functions used to load data from LAMMI. For more information on LAMMI, please see the pdf document :download:`LAMMI.pdf <LAMMIGuideMetho.pdf>`

.. automodule:: src.lammi
   :members:
   :undoc-members:


Load HABBY hdf5 file
--------------------------------------
in src/load_hdf5.py

This module contains some functions to load and manage hdf5 input/outputs. 

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
in src/dist_vitesse2.py

The goal of this list of function is to distribute the velocity along the cross-section 
for 1D model such as mascaret or Rubar BE. Hec-Ras outputs do not need to uses this type 
of function as they are already distributed along the profiles.

The method of velocity distribution in HABBY is similar to the one used by Hec-Ras to distribute 
velocity.  


.. automodule:: src.dist_vistess2
   :members:
   :undoc-members:

Create a grid
--------------------
in src/manage_grid_8

This module is composed of the functions used to manage the grid, 
notably to create 2D grid from the output from 1D model.

There are two main way to go from data in 1.5D in a profile form to a 2D grid:

*	through the usage of the triangle module in create_grid().
*	through the definition of a middle profile used as a guide to create the grid in create_grid_only_one_profile(). 

For an in-depth explanation on how to create the grids, please see the pdf document :download:`More info on the grid <Grid_info.pdf>`


.. automodule:: src.manage_grid_8
   :members:
   :undoc-members:

Estimhab -source
---------------------
in src/estimhab.py

The module contains the Estimhab model. For an explanation on the estimhab model, please see 
the pdf document :download:`estimhab2008 <estimhab2008.pdf>`


.. automodule:: src.estimhab
   :members:
   :undoc-members:

Stathab - source
-------------------------
in src/stathab_c

This module contains the function used to run the model stathab.For an explanation on 
the form of the stathab input, please see the pdf document :download:`stathabinfo <stathabinfo.pdf>`


.. automodule:: src.stathab_c
   :members:
   :undoc-members:
   
FStress - source
-------------------------
in src/fstress.py

This module contains the function used to run the model FStress.For an explanation on 
the form of the FStress text input, please see the last page of the pdf document :download:`stathabinfo <stathabinfo.pdf>`
 
 
.. automodule:: src.fstress
   :members:
   :undoc-members:
   

Substrate
-------------------
in src/substrate.py

This module contains the function to load and manage the substrate data.

.. automodule:: src.substrate
   :members:
   :undoc-members:

Merge the grid
------------------
in src/mesh_grid2.py

This module contains the function to merge the substrate grid and the hydrological grid.
It cut the hydrological grid to the form of each of the substrate. An important hypothesis
is that each polygon forming the subtrate should convex.

.. automodule:: src.mesh_grid2
   :members:
   :undoc-members:

Biological Info
-------------------------
in src/bio_info.py

This module contains the script to show and manage the biological models (preference curves) which are in the biology folder.

.. automodule:: src.bio_info
   :members:
   :undoc-members:

Calculation habitat
-----------------------
in src/calcul_hab.py

This module calculates the habitat value for the fish and creates the outputs (text files, shapefile, and figures).

.. automodule:: src.calcul_hab
   :members:
   :undoc-members:


Create Paraview Files
------------------------
in src/new_create_vtk.py
in src/evtk.py
in src/hl.py
in src/vtk.py
in src/xml_vk.py

Theses modules contain the scripts to create Paraview input which are binary xml-based vtu files. This part is heavily based on the module
Pyevtk created by Paulo Herrera (https://bitbucket.org/pauloh/pyevtk). Hence, the only script written for HABBY is in new_create_vtk.py. This
script then called one function in hl.py which then called the three other scripts as in Pyevtk (not documented here).

.. automodule:: src.new_create_vtk
   :members:
   :undoc-members:

Function for the command lines
-------------------------------
in src/func_for_cmd.py

This module contains functions which are used by habby.py when called on the command line (witjout using the GUI).

.. automodule:: src.func_for_cmd
   :members:
   :undoc-members:

   
Various notes
===============



Figures and matplotlib
----------------------------------------

**The legend of the plots are not shown.**

Generally HABBY is able to save the figure while showing the legend (which is often outside of the figure) appropriately. However, 
the figure shown to the user by matplotlib often have the legend outside of the visible area. To see the figure fully, one can modify
the axes in the option of the figure (the menu in the axes on the top of the figure).


**How to make figures editable in Adobe Illustrator**

It is useful to have figures which we can edit in Adobe Illustrator. To achieve this, the following matplotlib option should be added:
mpl.rcParams['pdf.fonttype'] = 42. Moreover, matplolib should be imported (import matplotlib as mpl). It is also useful to add the tranparent option to the function to save the figure (transparent=True). This renders modification easier in many cases. However, it is not good to use mpl.rcParams['ps.fonttype'] = 42 as the figure created in the eps format would be corrupted because of a bug in matplotlib.


Translation of HABBY
------------------------

In HABBY, it is possible to translate all strings which are in a python file (.py) 
which is in the src_GUI folder.

To add a new string to translate:

*	Code as usual and write the string in English. 
*	Add self.tr() around the string  a = Qlabel(self.tr(“My message”))
*	If the code is in a new python file (like the .py was just created), open the habby_trans.pro file which is src_GUI. Then add the line SOURCES+= new_file.py where new_file.py is the new python file. 
*	If you want to add a new language, add the line TRANSLATIONS += Zen_ES.ts in the case you want to add Spanish or any other language.
*	Copy the files ZEN_EN.ts and ZEN_FR.ts from HABBY/translation to /src_GUI
*	In the src_GUI folder, run the following command on the cmd: pylupdate5 habby_trans.pro. it will work if pylupdate is installed.
*	It should update the .ts file (which is an xml file)
*	Copy both .ts file back to HABBY/translation
*	Open Qt  linguist. This is a program that you need to install before. Open the French .ts file. The English should not need translation.
*	Translate as needed and save in Qt Linguist.
*	A .qm file is the binary representing the .ts file with all the translation. To create .qm file, type (in the cmd) lrelease  file.ts. It will create a file.qm file
*	Run HABBY. The string should be updated.

**In the code**

If the user asked for a new language, we need to reload the translator with the following lines:

	*app = QApplication.instance()*

	*self.languageTranslator.load(file.qm, self.path_trans)*

 	*app.installTranslator(self.languageTranslator)*

with the appropriate name for “file.qm”. 

In HABBY, the list of the name of all qm file are in the variable self.file_langue 
in class MainWindows. Hence, we can follow the selected language using an integer self.lang 
(0 for English and 1 for French). We can now call self.file_langue[self.lang] to get the qm 
file in the right language. If a new language is added, it is necessary to add one string to this 
list and to modify the menu. If the new language is also present in the xml preference file
(which contains the biological info), it is also necessary to update the variable "bioinfo_tab.lang"
from central_widget in the function setlangue from Main_Windows(). If this is done, the description of
the xml preference file in the "Biology" tab will be shown in the selected language. Otherwise, it will be
the first language found.

When the translator has been created, it is necessary to re-do all Widgets and Windows. This is not a problem when we open HABBY, but it can be a bit of work if the user asks for a change in language when HABBY is running. This is the function of the setlangue function. This function would work for all language (it takes an integer as input to know which language to use), but it needs to be modified if one modifies the Main_Windows Class strongly (notably if one add signals).
The language should be saved in the user setting using Qsettings as it is done at the end of the 
setlangue function.

In addition, every xml project file from HABBY has a part called "FigureOPtion". In the list of available options, there is the language currently used under the attibute "LangFig". The language is given using an int (0 for english, 1 for french). This is useful to translate the axis and the titles of the figures done by HABBY. To this end, one would first called the function "load_fig_option" in output_fig_GUI.py. This returns a dictionnary with a key called "language" (0 for english, 1 for french). Then, one can use an if statement to write the xlabel in french or english.

Create a .exe
--------------------

Here are step to create a .exe using PyInstaller:

*	install Pyinstaller (pip install pyinstaller)
*	cd "folder with source code"
*	pyinstaller.exe [option] habby.py, with the option --onefile to get only one .exe and --windowed to not have the cmd which opens with the application.

Here are some common problems:

*	ImportError: (No module named 'PyQt5.QtGui'): Copy the folder platform with qwindows.dll and add to the set_up.py  "includes": ["PyQt5.QtCore", "PyQt5.QtGui"]
*	This application fails to start because ... the Qt platform pugin windows: Copy the folder platform with qwindows.dll in it
*	ImportError: h5Py "includes": ["h5py","h5py.defs", "h5py.utils", "h5py.h5ac", 'h5py._proxy' ] etc if necessary
*	Intel MKL fatal error copy the .dll missing (or just find an old dist and copy all mkl stuff) AND the libiomp5md.dll
*	The translation does not work: Add the translation folder into the dist folder
*	Do not find log0.txt (or crash when saving project): create a folder called src_GUI, copy the files log0.txt and restart_log0.txt from the src_GUI folder in the python module

Practically:

* go to the folder called executable and copy the current HABBY source there.
* copy createexe.bat in the habby folder.
* run createexe.bat (only on Windows)
* ignore the executable created in the "built" folder Use the one is in the "dist" folder.
* copy all files in the mklall folder to the folder dist/habby.
* copy all the files in the original src_GUI folder which are NOT python file to the src_GUI folder just created (or you know, improve the bat file...).
* copy the doc folder in the dist/habby folder
* run habby by writing habby on the cmd
* test and correct problems. It can be long!

Logging
--------------

**General information**

There are two different logs for HABBY. By default, the first one is called “name_projet”.log and 
the second is called restart/_'name_project'.log. Their name and path can be changed in the xml 
project file. Both file are text file.

The first log is in the form of a python file with comments. If python and the necessary modules 
are installed on the machine, this log can be renamed “name.py” and started as a python file. 
In the command line, the following command should be used: python name.py. This file can be 
modified to create a new script to use HABBY in a different ways. For this, python syntax should be used.

The second log, called restart/_’name_project’.log, has limited functionalities but allows to 
re-start the HABBY simulation from the command line, without the need for python. 
Format of this file is described below. It is aimed to be readable and easily modifiable. 
To use the restart file, type in the command line: python habby.py restart/_’name_project’.log.

This part genreally needs more revisions and tests.

**Type of log and format**

Currently, there are five types of outputs, which can be sent to the log:

*	Comment, which should start with #. They will be sent to the python-type log file and to the GUI of Habby.
*	Errors, which should start with word “Error”. They will be sent to the python-type log file and to the GUI of Habby. In the GUI, they will appear in red. 
*	Warnings, which should start with the word “Warning”. They will be sent to the python-type log file and to the GUI of Habby. In the GUI, they will appear in orange.
*	Restart info, which should start with the word “restart’. They will be sent to the restart\_’name_project’.log. The format will be developed afterwards.
*	All types of text which do not start with these code words are only shown to the GUI of Habby.
*	Python code, which should start with the line py followed by four spaces.  It will be sent to the python-type log file. It is usually a function which is part of Habby code. The different arguments of the function should be given in the preceding lines.

**Example** 

Let’s write to the log a function which takes an integer and a string as input. The function 
is in the module called habby1, which is imported by default in the .log file. The strings to send
as log would be:

*	"#  this my fancy function"
*	"py    my_int = " + str(my_int_in_code)
*	"py    my_string = ’” + my_string_in_the _code+ "'“
*	"py    habby1.myfunc(my_int, my_string)"

A comment should be added before each chunk of python code to improve the readability. 

**Update the log**

Let’s consider a scenario where a new function has been written in a non-GUI module (class or 
function) and has to be called in the GUI in a method of a class. Let’s call the new function 
new_func and the class in the GUI my_class.

To create a new line of log for new_func, one should follow these steps:

*	A PyQtsignal with a string as argument should be added to my_class: send_log = pyqtSignal(str, name='send_log')
*	If a log should be sent directly from my_class (for example, to say that new_func  has been called), the signal should be emitted: self.send_log.emit('# new_func has been called'))
*	In the new function,  error and warning are written as follows: print(“Error: here is an error.\n”) or print(“Warning:  This is just a warning.\n”)
*	In my_class, error and warning are collected by redirecting stdout to a string. The following lines of code should be added around the calling of my_func():

	*	sys.stdout = mystdout = StringIO()  # redirect stdout
	*	my_func(my_int,my_string)
	*	sys.stdout = sys.__stdout__   # re-sent stdout to the cmd
	*	str_found = mystdout.getvalue()   # get all warning, error, text,…
	*	str_found = str_found.split('\n')  # separate each message
	*	for i in range(0, len(str_found)):

		*	if len(str_found[i]) > 1:

			*	self.send_log.emit(str_found[i])  #send the text

*	To import StringIO, the following statement is needed at the start of the code: from io import StringIO
*	If new_func is called from the command line, stdout will not be redirected and the errors or warnings will be printed on the cmd as usual.  Stderr should be re-directed in a similar manner if needed. 
*	The signal should be collected in the function connect_signal_log in the Main_Windows_1.py.  For this, a line should be added in the function:
	*	self.my_class.send_log.connect(self.write_log)

**restart file**

The format of the restart file is based on the format asked by the functions in func_for_cmd.py. More information on this format in func_for_cmd.py 
(notably in the part list_command).


Git - code management
------------------------------

**Pour commencer:**

*	Choisir un dossier sur l’ordinateur local ou va se trouver les fichiers sources. 
*	cd  « dossier avec les codes source»
*	git config - - global user.name « username »
*	git config - - global user.email  « mail »
*	git init 
*	lier le repertoire local avec le repertoire distant sur forge.irstea.fr

** Pour cloner HABBY**
*	cd « dossier souhaité»
*	git clone https://git.irstea.fr/git/habby

**Pour mettre une nouvelle version sur le site web**

*	cd « dossier avec les codes source»
*	git pull (prend la dernière version à jour sur le site et mets tous les fichiers ensemble) ou git fetch (prend juste les derniers fichiers sans mettre tous les fichiers ensemble).
*	git add ‘my_file.py ou .pyc’ (choisit les fichiers qui doivent être envoyé), le signe * fonctionne.
*	git log (donne l’historique)
*	git status (donne les nouveaux fichiers locals)
*	git commit –m « description » (commit localement)
*	git push

**Pour ajouter une nouvelle branche**

*	Donc pour avoir une partie du travail sépare du reste
*	git checkout –b [branchname] pour créer la branche et y travailler
*	git checkout [branchname] pour y travailler

Test HABBY
-------------------------------

For the moment, there are two automatic tests for HABBY which are in the HABBY folder. This is test_habby_quick which takes about 2 minutes to run and which only test one simple habitat calculation, and test_habby2 which tests the loading of the different hydraulic models, the creation of computational grid for 1D hydraulic models, the habitat calculation on diverse cases and the statistical models. It takes about two hours to run.

The test are bash codes so they run under Windows only, but it is relatively easy to modify the script to run it under another exploitation system. To run it under a new Windows computer, it is also necessary to change the first lines of the bash codes to give the paths of the folders with the original data. These folders are not in the HABBY folder as they need about 7 Giga of space. 

There is no test for the GUI at the moment as we did not find a practical tool to test it.


Write the documentation
-------------------------------
Habby uses Sphinx to document the code. Sphinx uses the docstring given in each function. Hence, it is necessary to write a docstring for each function which has to be documented.

To update the html documentation, go to the doc folder and execute the command: “make html”. 

To update the Latex documentation, use the commande "make latex" and use Miketex to create the pdf. rts2pdf does not work with Python 3.

To add text in the documentation, modify the index.rst file in the doc folder. To add a new module to the 
documentation, add the module as written in the index.rts file in the doc folder. To add text comment, the index.rts file can also be direclty modified.

It is important to keep the formatting and the alignment. 

If the module is in a new folder, the address of the folder must be added to the config.py file. 
It is better to not use absolute path for this, so it is possible to move the documentation on another 
computer. If the documentation does not run on a new computer, check the path given in the config.py file. 

In the docstring, add as many blank lines as possible (in reasonable limit). This is easier for the 
formatting. To make a bullet list, one should use a tab and the symbol "*".  Using only the symbol "*" will 
fail.

To add a new title, do not start the title or the line of symbol under the title with a blank space.

License of used python modules
------------------------------------

*	h5py: BSD License
*	Element tree (XML): MIT License
*	numpy: BSD License
*	matplotlib: BSD License
*	PyQt5: GNU License
*	Scipy: BSD license
*	shutil: 



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
