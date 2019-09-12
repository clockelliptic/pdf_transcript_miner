# This test suite is intended to be used in an iPython Environment
#%%
import dev.transcript_plotter.transcript_plotter as tplot
import dev.transcript_miner.transcript_miner as tm
import pdfquery as pq
from time import time

#%%
pdf_filepath = 'C:\\Users\\allen\\Documents\\GitHub\\Upwork\\cc_transcript\\dev\\data\\sample2.pdf'
outfile_path = 'C:\\Users\\allen\\Documents\\GitHub\\Upwork\\cc_transcript\\dev\\csv_out\\sample2.csv'

#%% ANCHOR: Load and validate PDF
pdf = pq.PDFQuery(pdf_filepath)
pdf.load()

if not tm.valid_pdf(pdf):
    print(" ** PDF IS INVALID ** ")

#%% ANCHOR: Scrape figures (pages)
figures = pdf.pq('LTFigure')

#%% ANCHOR: Scrape 'Beginning' labels to locate college sections
beginning_labels = tm.define_college_sections(pdf, figures)

#%% ANCHOR: Scrape the rest of the labels (Course, Attempted, Grade....)
label_instances = tm.scrape_labels(pdf, beginning_labels, figures)

#%% ANCHOR: Clean the labels, remove unneeeded instances, etc.
label_instances = tm.clean_labels(label_instances)

#%% ANCHOR: Group label instances according to their respective college-section
colleges = tm.group_label_instances_by_college(label_instances)

#%% ANCHOR: Scrape the names of the semesterly learning Plans
colleges = tm.scrape_plans(pdf, colleges)

#%% ANCHOR: Scrape target data (course departments, course numbers, descriptions, credits, points, etc.)
colleges = tm.scrape_course_targets(pdf, colleges)

#%% ANCHOR: Dump data to CSV file
tm.gen_csv(pdf, colleges, outfile_path)

#%% ANCHOR: Visualize scraped data with image-reconstruction of transcript
npages=len(figures)

fig, ax = tplot.setup_plot(npages)
tplot.plot_transcript(fig, ax, pdf, npages, colleges)


#%%
