from distutils.core import setup
from Cython.Build import cythonize
	  
setup(name='Community College Transcript Miner - Visualization Module',
      ext_modules=cythonize("transcript_plotter.py"))