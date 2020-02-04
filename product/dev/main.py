# Environment:
# python = 3.74
# dependencies: pandas, pdfquery

#%%
def scrape_transcript(pdf_filepath, outfile_path):
    """
    Args:
        pdf_filepath: path to transcript pdf to be scraped
        outfile_path: path and filename of CSV outfile
    """
    import transcript_miner as tm
    import pdfquery as pq

    is_good_pdf = False

    try:
        pdf = pq.PDFQuery(pdf_filepath)
        pdf.load()

        is_good_pdf = tm.valid_pdf(pdf)
    except Exception as e:
        print("Input file is invalid. Error: ", e)
        return -1

    if is_good_pdf:
        figures = pdf.pq('LTFigure')

        beginning_labels = tm.define_college_sections(pdf, figures)

        label_instances = tm.scrape_labels(pdf, beginning_labels, figures)
        label_instances = tm.clean_labels(label_instances)

        colleges = tm.group_label_instances_by_college(label_instances)
        colleges = tm.scrape_plans(pdf, colleges)
        colleges = tm.scrape_course_targets(pdf, colleges)

        tm.gen_csv(pdf, colleges, outfile_path)
    else:
        print("Invalid PDF.")
        return -1

#%%
if __name__ == "__main__":
    import os
    import argparse

    argparser = argparse.ArgumentParser(\
        description = "Scrape Los Rios CCD Unofficial Transcripts")

    argparser.add_argument(
        "infile", default = "",
        help = "Path to transcript PDF to be scraped",
        metavar = "PDF_IN"
    )

    argparser.add_argument(
        "outfile", default = "",
        help = "path to CSV output file",
        metavar = "CSV_OUT"
    )

    args = argparser.parse_args()

    scrape_transcript(pdf_filepath = args.infile,
                      outfile_path = args.outfile)

#%%