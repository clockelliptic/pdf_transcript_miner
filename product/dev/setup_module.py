from distutils.core import setup
from Cython.Build import cythonize

setup(name='Community College Transcript Miner',
      ext_modules=cythonize("transcript_miner.py"))