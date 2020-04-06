from setuptools import setup, find_packages
from platform import system as operatingsystem

# requirment.txt
if operatingsystem() == 'Windows':
    requirement_path = 'requ_windows.txt'
elif operatingsystem() == 'Linux':
    requirement_path = 'requ_linux.txt'
elif operatingsystem() == 'Darwin':
    requirement_path = 'requ_mac.txt'
with open(requirement_path) as f:
    required_packages = f.read().splitlines()

# README.md
with open("README.md", "r", encoding='utf8') as fh:
    long_description = fh.read()

# INSTALL
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
    install_requires=required_packages,
    include_package_data=True,
    python_requires='>=3.6',
    entry_points="""
    [console_scripts]
    habby=habby.main
    """,
    zip_safe=False,
)