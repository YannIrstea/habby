from setuptools import setup, find_packages

with open("README.md", "r", encoding='utf8') as fh:
    long_description = fh.read()

setup(
    name="HABBY",
    version="0.25",
    description="Program to estimate aquatic habitats using hydraulic data and biological models",
    long_description=long_description,
    url="https://github.com/YannIrstea/habby",
    author="Diane von Gunten, Yann Le Coarer, Quentin Royer and Fabrice Zaoui",
    author_email="yann.lecoarer@irstea.fr, quentin.royer@irstea.fr, fabrice.zaoui@edf.fr",
    license='CeCILL v2.1',
    packages=find_packages(),
    # do not set packages which versions are different between operatin systems
    install_requires=[
        "appdirs==1.4.3",
        "cycler==0.10.0",
        "Cython==0.29.13",
        "h5py==2.8.0rc1",
        "kiwisolver==1.1.0",
        "matplotlib==3.0.0",
        "mplcursors==0.2.1",
        "numpy==1.15.3",
        "numpy-stl==2.10.0",
        "pyparsing==2.4.2",
        "PyQt5==5.11.3",
        "PyQt5-sip==4.19.18",
        "python-dateutil==2.8.0",
        "python-utils==2.3.0",
        "QDarkStyle==2.6.5",
        "scipy==1.1.0",
        "six==1.12.0",
        "triangle==20170429",
        "Pillow==6.2.1"
    ],
    include_package_data=True,
    python_requires='>=3.6',
    entry_points="""
    [console_scripts]
    habby=habby.main
    """,
    zip_safe=False,
)