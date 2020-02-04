# This test suite is intended to be used in an iPython Environment
#%%
import dev.transcript_plotter.transcript_plotter as tplot
import dev.transcript_miner.transcript_miner as tm
import pdfquery as pq
from time import time

#%%
pdf_filepath = 'C:\\Users\\allen\\Documents\\GitHub\\Upwork\\cc_transcript\\dev\\data\\sample2.pdf'
outfile_path = 'C:\\Users\\allen\\Documents\\GitHub\\Upwork\\cc_transcript\\dev\\csv_out\\sample2.csv'

#%% ANCHOR:
pdf = pq.PDFQuery(pdf_filepath)
pdf.load()

if not tm.valid_pdf(pdf):
    print(" ** PDF IS INVALID ** ")

#%% ANCHOR:
figures = pdf.pq('LTFigure')

#%% ANCHOR:
colleges = tm.define_college_sections(pdf, figures)

#%% ANCHOR:
semesters = tm.scrape_semesters_and_plans(pdf, figures)

#%%
colleges = tm.group_semesters_by_college(colleges, semesters)

#%%
colleges = tm.scrape_courses(pdf, colleges)



#%%
t = time()
pdf = pq.PDFQuery('C:\\Users\\allen\\Documents\\GitHub\\Upwork\\cc_transcript\\dev\\data\\scccatalog.pdf')
pdf.load()
print(time()-t)

#%%
