 -- DEMO Instructions --

1. Open the `'Documentation'` directory and read `'Instructions.html'` (or visit the github page for this repo: https://clockelliptic.github.io/pdf_transcript_miner/). A Jupyter Notebook version of the Instructions file can also be found in this directory.

2. In two new windows, open the folder `'main/csv_out'` and the folder `'main/data'`

3. Notice the files in `'main/data'`

2. To demo the program, open a terminal/command prompt in the 'main' directory

3. Type the following three commands one at a time. When a command has finished running, the resulting CSV file will appear in the `'main/csv_out'` folder.

```
	main.exe "data/sample0.pdf" "csv_out/sample0_out.csv"
	main.exe "data/sample1.pdf" "csv_out/sample1_out.csv"
	main.exe "data/sample2.pdf" "csv_out/sample2_out.csv"
```

4. Run the following two commands to demonstrate error handling of corrupt and invalid PDF files:

	`main.exe "data/bad_file0.pdf" "csv_out/bad.csv"`
	`main.exe "data/bad_file1.pdf" "csv_out/bad.csv"`

5. - WARNING - This program is vulnerable to excessively large files. Please have your team limit the size of transcript files that users can upload to a range that is normal for transcript PDF files (approximately 0kb - 40kb).

Use the following command to extract `bad_file2.pdf` (a 39MB book) to demonstrate the vulnerability. You will have to force the process to stop.

	`main.exe "data/bad_file2.pdf" "csv_out/bad.csv"


6. A quick StackOverflow search shows that the extraction program can be executed from php with the following command:

   `shell_exec("main.exe" . $path_to_transcript_pdf . " " . $path_to_outfile_csv);`
