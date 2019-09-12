# Environment:
# python = 3.74
# dependencies: pandas, pdfquery, numpy, matplotlib (test suite only)

#%% ANCHOR: Imports
import pandas as pd
import pdfquery as pq

#%% SECTION: Define Mining Functions

# ANCHOR: Global Constants
PAGEWIDTH = 792
HALFPAGEWIDTH = 396
PAGEHEIGHT = 612
TOP_OF_PAGE = 523
BOTTOM_OF_PAGE = 72


# ANCHOR: valid_pdf()
def valid_pdf(pdf):
    """
    Returns bool

    Args:
        pdf: loaded pdfquery pdf object
    """
    pageheading = 'Los Rios CCD Unofficial Transcript - All'
    pageheadings = pdf.pq('LTTextLineHorizontal:contains("%s")' % pageheading)

    valid_headings = [i[0].text.strip(" ") == pageheading.strip(" ")
                      for i in pageheadings].count(True) == len(pdf.pq('LTFigure'))
    valid_pagewidth = 792 == round(float(pdf.get_layout(1).bbox[2]))
    valid_pageheight = 612 == round(float(pdf.get_layout(1).bbox[3]))

    return all([valid_headings, valid_pagewidth, valid_pageheight])

# ANCHOR: scrape_labels()
def define_college_sections(pdf, figures):
    """
    Returns dict of Pandas DataFrames

    Args:
        pdf: loaded pdfquery pdf object
        figures: list of LTFigure objects scraped from the PDF
    """

    raw_scrape = {"Beginning": []}

    for figure in figures:
        pageid = float(figure.iterancestors('LTPage').__next__().layout.pageid)
        for instance_wrapper in figure:
            for instance in instance_wrapper.getchildren():
                if "----------Beginning" in instance.text:
                    raw_scrape["Beginning"].append(dict(instance.attrib,
                                                    **{"pageid":pageid,
                                                        "-y0":-1 * float(instance.get('y0')),
                                                        "text": instance.text,
                                                        "pageside":
                                                        float(instance.attrib['x0']) > HALFPAGEWIDTH
                                                    }))

        _instances = raw_scrape
        instances = dict()

        if len(_instances["Beginning"]) > 0:
            instances["Beginning"] = \
            pd.DataFrame.from_records(_instances["Beginning"]).apply( \
                                    lambda df_col: pd.to_numeric(df_col, \
                                        errors='ignore')).round(decimals=0)

    return find_college_section_ends(instances, len(figures))

# ANCHOR: define_college_sections()
def find_college_section_ends(instances, maxpageid):
    """
    Adds a column to the instances["Beginning"] dataframe which indicates
    the last page of that college section of the given transcript.

    Returns a dict of pandas dataframes.

    Args:
        instances: dict of pandas dataframes containng label instances
        maxpageid: the page number of the final page of the transcript
    """
    instances['Beginning']['last_pageid'] = 0
    # find the pageid of the last page of each college section
    for n, row in instances['Beginning'].iterrows():
        if n < (len(instances['Beginning']) - 1):
            instances["Beginning"].at[n, 'last_pageid'] = instances['Beginning'].at[n+1, 'pageid'] - 1

        elif n == (len(instances['Beginning']) - 1):
            instances["Beginning"].at[n, 'last_pageid'] = maxpageid

    return instances

# ANCHOR: scrape_labels()
def scrape_labels(pdf, beginning_label_instances, figures):
    """
    Returns a dict() containing key-value pairs for each label (text) that we
    want to search for in the PDF. The values of the dict contain lists of
    instances of each label and their respective meta-data (i.e. position on
    page, pageid, etc.). The keys are the labels.

    Args:
        pdf: loaded pdfquery pdf object
        figures: list of LTFigure objects scraped from the PDF
    """

    semesters = ("Spring", "Summer", "Fall", "Winter",)
    labels = ("Plan", "Course", "Description", "Grade", "Attempted", "Earned", "Points")

    raw_scrape = dict()
    for label in labels:
        raw_scrape[label] = []
    raw_scrape['semester'] = []

    for figure in figures:
        pageid = float(figure.iterancestors('LTPage').__next__().layout.pageid)

        for label in labels+semesters:
            for instance_wrapper in figure:
                for instance in instance_wrapper.getchildren():
                    if label in instance.text:
                        if any([s in label for s in semesters]):
                            raw_scrape['semester'].append(dict(instance.attrib,
                                                          **{"pageid":pageid,
                                                             "-y0":-1 * float(instance.get('y0')),
                                                             "text": instance.text,
                                                             "pageside":
                                                             float(instance.attrib['x0']) > HALFPAGEWIDTH
                                                            }))
                        elif label == instance.text.strip(" ").strip(":"):
                            raw_scrape[label].append(dict(instance.attrib,
                                                          **{"pageid":pageid,
                                                             "-y0":-1 * float(instance.get('y0')),
                                                             "text": instance.text,
                                                             "pageside":
                                                             float(instance.attrib['x0']) > HALFPAGEWIDTH
                                                            }))

        _instances = raw_scrape
        instances = dict(beginning_label_instances)

        for label in _instances.keys():
            if len(_instances[label]) > 0:
                instances[label] = \
                pd.DataFrame.from_records(_instances[label]).apply( \
                                        lambda df_col: pd.to_numeric(df_col, \
                                            errors='ignore')).round(decimals=0)

    return instances


# ANCHOR: clean_labels()
def clean_labels(instances):
    """
    Cleans and sorts label instances.

    Returns a dict of pandas dataframes.

    Args:
        instances: dict of pandas dataframes containng label instances
    """
    # skip every third instance of these labels
    skip_third = ["Points"]
    # skip every second and third instance of these labels
    skip_secondthird = ["Attempted", "Earned"]

    # all labels
    labels = ["Beginning", "Plan", "Course", "Description",
              "Grade", "Points", "Attempted", "Earned", "semester"]

    for s in skip_third:
        df = instances[s]
        instances[s] = df[(df.index+1) %3 != 0].reset_index(drop=True)

    for s in skip_secondthird:
        df = instances[s]
        instances[s] = df[df.index %3 == 0].reset_index(drop=True)

    instances['semester'] = instances['semester'].sort_values(by = ["pageid", "pageside", "-y0"]).reset_index(drop=True)
    return instances

# ANCHOR: group_label_instances_by_college()
def group_label_instances_by_college(instances):
    """
    Returns a dict of dicts of pandas dataframes.

    Args:
        instances: dict of pandas dataframes containng label instances
    """
    colleges = dict()
    labels = ["Beginning", "Plan", "Course", "Description",
              "Grade", "Points", "Attempted", "Earned", "semester"]

    for n, row in instances['Beginning'].iterrows():
        collegename = row.text.split(" ")[2]
        colleges[collegename] = dict()
        for label in labels:
            df = instances[label]

            colleges[collegename][label] = df[ (
                                    (df['pageid'] >= row['pageid']) & \
                                    (df['pageid'] <= row['last_pageid'])
                                ) &
                                (
                                    (
                                        df['pageid'] > row['pageid']
                                    ) |
                                    (
                                        (df['pageid'] == row['pageid']) &
                                        (
                                            (df['y0'] < row['y1']) |
                                            (df['x0'] > HALFPAGEWIDTH)
                                        )
                                    )
                                )].reset_index(drop=True)
    return colleges

# ANCHOR: scrape_plans()
def scrape_plans(pdf, colleges):
    """
    Adds a new column called 'targets' to the 'Plan' dataframe.

    Scrapes the names of the learning plans in each semester of the transcript into
    this column.

    Returns a dict of dicts of pandas dataframes.

    Args:
        pdf: loaded pdfquery pdf object
        colleges: dict of dicts of dataframes containing label instances
    """
    for college in colleges:
        instances = colleges[college]
        instances["Plan"]['target'] = ""
        for n, row in instances['Plan'].iterrows():
            x0 = row['x1'] -1
            y0 = row['y0'] -1
            x1 = row['x1'] + 300
            y1 = row['y1'] +1
            raw_scrape = pdf.pq('LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % \
                                                                (x0, y0, x1, y1))
            for i in raw_scrape:
                if i.iterancestors('LTPage').__next__().layout.pageid == row['pageid']:
                    target_text = ''.join([j.text for j in i])
                    target = dict(i.attrib, **{"text": target_text,
                                               "pageid": row['pageid']} )

            instances["Plan"].at[n, 'target'] = target
            colleges[college]["Plan"] = instances["Plan"]
    return colleges

# ANCHOR: scrape_course_targets()
def scrape_course_targets(pdf, colleges):
    """
    Scrapes the department, sequence, description/title, attempted, earned
    grade, and points for each course in each semester.

    Args:
        pdf: loaded pdfquery pdf object
        colleges: dict of dicts of dataframes containing label instances
    """

    for college in colleges:

        instances = colleges[college] #type: pd.DataFrame
        instances['Course']['targets'] = object

        for n, row in instances['Course'].iterrows():
            targets = {
                        "dept":        [],
                        "seq":         [],
                        "description": [],
                        "attempted":   [],
                        "earned":      [],
                        "grade":       [],
                        "points":      []
            }

            # CASE: semester section starts on one page of the transcript and ends on the next
            if instances["Points"].loc[n*2+1]['pageid'] > row['pageid']:
                # scrape part on first page
                depts, seqs = \
                    scrape_course_dept_and_seq(
                        pdf = pdf,
                        pageid = row['pageid'],
                        x0 = row['x0']-1,
                        y0 = BOTTOM_OF_PAGE,
                        x1 = instances['Description'].loc[n]['x0']+1,
                        y1 = row['y0']+1,)
                for dept, seq in zip(depts, seqs):
                    targets['dept'].append(dept)
                    targets['seq'].append(seq)
                    targets_ = scrape_targets(pdf = pdf, x0 = 511, y0 = seq['y0'], y1 = seq['y1'], pageid = seq['pageid'])
                    for key in targets_.keys():
                        targets[key].append(targets_[key])

                # scrape part on second page
                depts, seqs = \
                    scrape_course_dept_and_seq(
                        pdf = pdf,
                        pageid = row['pageid'],
                        x0 = 0,
                        y0 = instances["Points"].loc[n*2+1]['y1']-1,
                        x1 = 162+1,
                        y1 = TOP_OF_PAGE,)
                for dept, seq in zip(depts, seqs):
                    targets['dept'].append(dept)
                    targets['seq'].append(seq)
                    targets_ = scrape_targets(pdf = pdf, x0 = 161, y0 = seq['y0'], y1 = seq['y1'], pageid = seq['pageid'])
                    for key in targets_.keys():
                        targets[key].append(targets_[key])

            # CASE: semester section starts in first column of page and ends in second column
            elif instances["Points"].loc[n*2+1]['pageside'] != row['pageside']:
                # scrape part in first column
                depts, seqs = \
                    scrape_course_dept_and_seq(
                        pdf = pdf,
                        pageid = row['pageid'],
                        x0 = row['x0']-1,
                        y0 = BOTTOM_OF_PAGE,
                        x1 = instances['Description'].loc[n]['x0']+1,
                        y1 = row['y0']+1,)
                for dept, seq in zip(depts, seqs):
                    targets['dept'].append(dept)
                    targets['seq'].append(seq)
                    targets_ = scrape_targets(pdf = pdf, x0 = 161, y0 = seq['y0'], y1 = seq['y1'], pageid = seq['pageid'])
                    for key in targets_.keys():
                        targets[key].append(targets_[key])

                # scrape part in second column
                depts, seqs = \
                    scrape_course_dept_and_seq(
                        pdf = pdf,
                        pageid = row['pageid'],
                        x0 = HALFPAGEWIDTH,
                        y0 = instances["Points"].loc[n*2+1]['y1']-1,
                        x1 = 512+1,
                        y1 = TOP_OF_PAGE,)
                for dept, seq in zip(depts, seqs):
                    targets['dept'].append(dept)
                    targets['seq'].append(seq)
                    targets_ = scrape_targets(pdf = pdf, x0 = 511, y0 = seq['y0'], y1 = seq['y1'], pageid = seq['pageid'])
                    for key in targets_.keys():
                        targets[key].append(targets_[key])

            # CASE: semester section starts and ends in same column on same page
            else:
                depts, seqs = \
                    scrape_course_dept_and_seq(
                        pdf = pdf,
                        pageid = row['pageid'],
                        x0 = row['x0']-1,
                        y0 = instances["Points"].loc[n*2+1]['y1']-1,
                        x1 = instances['Description'].loc[n]['x0']+1,
                        y1 = row['y0']+1,)
                for dept, seq in zip(depts, seqs):
                    targets['dept'].append(dept)
                    targets['seq'].append(seq)
                    if row['pageside'] == False:
                        x0 = 161
                    else:
                        x0 = 511
                    targets_ = scrape_targets(pdf = pdf, x0 = x0, y0 = seq['y0'], y1 = seq['y1'], pageid = seq['pageid'])
                    for key in targets_.keys():
                        targets[key].append(targets_[key])

            for label in targets.keys():
                for target_instance in targets[label]:
                    if target_instance != None:
                        target_instance['label'] = label

            instances['Course'].at[n, 'targets'] = list( zip( * [targets[key] for key in targets]))
        colleges[college] = instances
    return colleges


# ANCHOR: scrape_course_dept_and_seq()
def scrape_course_dept_and_seq(pdf, pageid, x0, y0, x1, y1):
    """
    For a particular semester / bbox area, returns two ordered lists of dicts:
    course departments and course sequence numbers. Dicts contain the metadata
    for each dept/seq.

    Args:
        pdf: loaded pdfquery pdf object
        pageid: the page of the transcript to scrape
        x0, y0, x1, y1: bbox coordinates to scrape from

    """
    targets = []
    raw_scrape = pdf.pq('LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % \
                                                        (x0, y0, x1, y1))
    for i in raw_scrape:
        if i.iterancestors('LTPage').__next__().layout.pageid == pageid:
            if len(i) > 0:
                for j in i:
                    if j.text != None and j != None:
                        targets.append(( dict(j.attrib, **{"pageid": pageid,
                                                        "text": j.text.strip(" ")}
                                            )))
            else:
                if i.text != None and i != None:
                    targets.append(( dict(i.attrib, **{"pageid": pageid,
                                                    "text": i.text.strip(" ")}
                                        )))

    depts = [i for i in targets if i['text'].isalpha()]
    seqs = [i for i in targets if i['text'].isnumeric()]

    return depts, seqs


# ANCHOR: scrape_targets()
def scrape_targets(pdf, x0, y0, y1, pageid):
    """
    Scrapes the description/title, attempted, earned, grade, and points for a given course.

    Args:
        pdf: loaded pdfquery pdf object
        x0: initial x-position to begin iteratively scraping targets
        y0: lower y-coordinate of scraped bbox
        y1: upper y-coordinate of scraped bbox
        pageid: the page of the transcript to scrape
    """
    # generate pairs of (x0, x1)---the start and stop x-coordinates for each target instance
    labels = ["description", "attempted", "earned", "grade", "points"]
    xs_ = [float(x0)+i for i in [-1, 75, 103, 140, 169, 212]]
    xs_ = list(zip(xs_, xs_[1:]))
    xs = {labels[i]:xs_[i] for i in range(5)}
    targets = {label:None for label in labels}
    for label in xs.keys():
        x0 = float(xs[label][0])-1
        y0 = float(y0)-1
        x1 = float(xs[label][1])+1
        y1 = float(y1)+1
        raw_scrape = pdf.pq('LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % \
                                                                (x0, y0, x1, y1))
        for i in raw_scrape:
            if i.iterancestors('LTPage').__next__().layout.pageid == pageid:
                if len(i) > 0:
                    for j in i:
                        if j!=None and j.text!=None:
                            targets[label] = dict(j.attrib, **{"text": j.text.strip(" "),
                                                            "pageid": pageid})
                else:
                    if i!=None and i.text!=None:
                        targets[label] = dict(i.attrib, **{"text": i.text.strip(" "),
                                                        "pageid": pageid})
    return targets


def gen_csv(pdf, colleges, filename_out):
    """
    Args:
        filename_out: name of csv file to output
        pdf: loaded pdfquery pdf object
        colleges: dict of dicts of dataframes containing label instances
    """
    studentname = pdf.pq('LTTextLineHorizontal:contains("Name:")')[0][0].text.split("Name: ")[1]
    courses = []
    for college in colleges:
        for n, row in colleges[college]['Course'].iterrows():
            course_targets = row['targets']
            for target_set in course_targets:
                courses.append(
                    dict({(target['label'] if target!=None else "missing") : (target['text'] if target!=None else None) \
                         for target in target_set},
                         **{"semester":colleges[college]['semester'].loc[n]['text'],
                            "plan": colleges[college]['Plan'].loc[n]['target']['text'],
                            "college": college,
                            "name": studentname})
                )

    try:
        pd.DataFrame(courses).drop('missing', 1).to_csv(filename_out, index=False)
    except Exception as e:
        try:
            pd.DataFrame(courses).to_csv(filename_out, index=False)
        except:
            print(e)

# !SECTION
