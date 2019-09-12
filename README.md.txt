 -- ENVIRONMENT SETUP --

1. Install conda or miniconda, be sure to add it to your system path
2. From the command line, navigate to the /dev/ folder
3. then run :

	conda env create -f environment_droplet.yml

4. This will create a conda environment called 'cc_transcript'
5. Activate the environment by running the command:
	
	activate cc_transcript

6. From the command line, within /dev/, with cc_transcript activated,
   run python:

	python

7. From python, run the following line of code to verify that the environment
   has been configured correctly:

	import transcript_miner


   If you no exceptions are raised, the environment is set.

8. Optionally, you can install Jupyter Notebook using conda or setup VSCode with
   the Jupyter Notebook Ipython extension.