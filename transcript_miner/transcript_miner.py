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

COL1_X_VALS = {
   # 'key':        (x0 , x1),
    'dept':        (71 ,121),
    'seq':         (122,160),
    'description': (161,236),
    'attempted':   (237,279),
    'earned':      (280,312),
    'grade':       (313,349),
    'points':      (350,395),
}

COL2_X_VALS = {
    # 'key':       (x0 , x1),
    'dept':        (421,470),
    'seq':         (471,510),
    'description': (511,585),
    'attempted':   (586,629),
    'earned':      (630,660),
    'grade':       (661,699),
    'points':      (700,791),
}

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
    valid_pagewidth = PAGEWIDTH == round(float(pdf.get_layout(1).bbox[2]))
    valid_pageheight = PAGEHEIGHT == round(float(pdf.get_layout(1).bbox[3]))

    return all([valid_headings, valid_pagewidth, valid_pageheight])

# ANCHOR: scrape_labels()
def define_college_sections(pdf, figures):
    """
    Returns Pandas DataFrame.

    Args:
        pdf: loaded pdfquery pdf object
        figures: list of LTFigure objects scraped from the PDF
    """
    colleges = []
    idx=0
    for figure in figures:
        pageid = float(figure.iterancestors('LTPage').__next__().layout.pageid)
        for instance_wrapper in figure:
            for instance in instance_wrapper.getchildren():
                if "----------Beginning" in instance.text:
                    new_attribs = {"name": instance.text.split(" ")[2],
                                   "n":idx,
                                   "pageid": pageid,
                                   "last_pageid": None,
                                # '-y0' and 'pageside' are for easy top-to-bottom sorting
                                   "-y0": -1*float(instance.get('y0')),
                                   "pageside": float(instance.attrib['x0']) > HALFPAGEWIDTH,
                                   "semesters": object,}
                    colleges.append(dict(instance.attrib, **new_attribs))
                    idx+=1

    colleges = pd.DataFrame.from_records(colleges, index=("n", "name"))
    colleges = colleges.apply(lambda df_col: \
                                pd.to_numeric(df_col, errors='ignore')).round(decimals=0)

    return __find_college_section_ends(colleges, len(figures))

# ANCHOR: __find_college_section_ends()
def __find_college_section_ends(colleges, maxpageid):
    """
    Returns a Pandas DataFrame

    Args:
        colleges: pandas dataframe
        maxpageid: the page number of the final page of the transcript
    """
    # find the pageid of the last page of each college section
    for n, row in colleges.iterrows():
        if n[0] < (len(colleges) - 1):
            colleges.xs(n[0]).at[n[1], 'last_pageid'] = colleges.iloc[n[0]+1].pageid - 1
        else:
            colleges.xs(n[0]).at[n[1], 'last_pageid'] = maxpageid
    return colleges

# ANCHOR: scrape_semesters_and_plans()
def scrape_semesters_and_plans(pdf, figures):
    """
    Args:
        pdf: loaded pdfquery pdf object
        figures: list of LTFigure objects scraped from the PDF
    """

    seasons = ["Spring", "Summer", "Fall", "Winter",]
    labels = ["Plan",]

    plans = []
    semesters = []

    for figure in figures:
        pageid = float(figure.iterancestors('LTPage').__next__().layout.pageid)

        for label in seasons+labels:
            for instance_wrapper in figure:
                for instance in instance_wrapper.getchildren():
                    if label in instance.text:
                        if any([s in label for s in seasons]):
                            attribs = instance.attrib
                            plan_name = attribs
                            new_attribs ={"name": instance.text,
                                          "plan": "",
                                          "courses": object,
                                          "pageid":pageid,
                                          "end_pageid": None,
                                          "end_x": None,
                                          "end_y": None,
                                          "-y0":-1 * float(instance.get('y0')),
                                          "pageside": float(instance.attrib['x0']) > HALFPAGEWIDTH,
                                          "end_pageside": False #placeholder value
                                         }
                            semesters.append(dict(attribs, **new_attribs))

                        elif label == instance.text.strip(" ").strip(":"):
                            plans.append(instance.text) # TODO: FIX: needs to append target, not label

    for n, plan in enumerate(plans):
        semesters[n]['plan'] = plan

    semesters = pd.DataFrame.from_records(semesters).apply( \
                                lambda df_col: pd.to_numeric(df_col, \
                                    errors='ignore')).round(decimals=0)

    semesters = semesters.sort_values(by=["pageid", "pageside", "-y0"])
    semesters = semesters.reset_index(drop=True)
    semesters.index = semesters.index.rename('n')
    semesters = semesters.set_index([semesters.index, 'name'])

    return __find_semester_section_ends(pdf, figures, semesters)

# ANCHOR: __find_semester_section_ends()
def __find_semester_section_ends(pdf, figures, semesters):
    label = "Points"
    points = []
    idx=0

    for figure in figures:
        pageid = float(figure.iterancestors('LTPage').__next__().layout.pageid)
        for instance_wrapper in figure:
            for instance in instance_wrapper.getchildren():
                if label in instance.text:
                    attribs = instance.attrib
                    plan_name = attribs
                    new_attribs ={"pageid":pageid,
                                  "-y0":-1 * float(instance.get('y0')),
                                  "pageside": float(instance.attrib['x0']) > HALFPAGEWIDTH
                                  }
                    points.append(dict(attribs, **new_attribs))

    points = pd.DataFrame.from_records(points).apply( \
                                lambda df_col: pd.to_numeric(df_col, \
                                    errors='ignore')).round(decimals=0)
    points = points.sort_values(by=["pageid", "pageside", "-y0"]).reset_index(drop=True)
    points = points[(points.index - 1)%3==0].reset_index(drop=True)

    for i, row in semesters.iterrows():
        semesters.xs(i[0]).at[i[1], 'end_pageid'] = points.iloc[i[0]].pageid
        semesters.xs(i[0]).at[i[1], 'end_x'] = points.iloc[i[0]].x1
        semesters.xs(i[0]).at[i[1], 'end_y'] = points.iloc[i[0]].y0
        semesters.xs(i[0]).at[i[1], 'end_pageside'] = float(points.iloc[i[0]].x0) > HALFPAGEWIDTH

    return semesters

# ANCHOR: group_semesters_by_college()
def group_semesters_by_college(colleges, semesters):
    for n, row in colleges.iterrows():
        pageid = colleges.iloc[n[0]].pageid
        end_pageid = colleges.iloc[n[0]].last_pageid
        colleges.xs(n[0]).at[n[1], 'semesters'] = semesters[(semesters['pageid'] >= pageid) & \
                                                        (semesters['end_pageid'] <= end_pageid)]
    return colleges

# ANCHOR: scrape_courses()
def scrape_courses(pdf, colleges):
    #TODO: Fix, apparent not scraping course targets.
    for n, college in colleges.iterrows():
        for i, semester in college['semesters'].iterrows():
            multipage = semester.pageid == semester.end_pageid
            samecolumn = semester.pageside == semester.end_pageside
            pageid = semester.pageid
            if (samecolumn) and (not multipage):
                y1 = semester.y0 - 18
                y0 = semester.end_y
                if not semester.pageside:
                    x0 = COL1_X_VALS['dept'][0]
                    x1 = COL1_X_VALS['dept'][1]
                else:
                    x0 = COL2_X_VALS['dept'][0]
                    x1 = COL2_X_VALS['dept'][1]
                # SCRAPE
                courses = scrape_course_bbox(pdf, x0, y0, x1, y1, pageid)

            elif (not samecolumn) and (not multipage):
                y1 = semester.y0 - 18
                y0 = BOTTOM_OF_PAGE
                x0 = COL1_X_VALS['dept'][0]
                x1 = COL1_X_VALS['dept'][1]
                courses = scrape_course_bbox(pdf, x0, y0, x1, y1, pageid)
                y1 = TOP_OF_PAGE
                y0 = semester.end_y
                x0 = COL2_X_VALS['dept'][0]
                x1 = COL2_X_VALS['dept'][1]
                courses.append(scrape_course_bbox(pdf, x0, y0, x1, y1, pageid))

            elif (multipage):
                y1 = semester.y0 - 18
                y0 = BOTTOM_OF_PAGE
                x0 = COL2_X_VALS['dept'][0]
                x1 = COL2_X_VALS['dept'][1]
                courses = scrape_course_bbox(pdf, x0, y0, x1, y1, pageid)

                y1 = TOP_OF_PAGE
                y0 = semester.end_y
                x0 = COL2_X_VALS['dept'][0]
                x1 = COL2_X_VALS['dept'][1]
                courses.append(scrape_course_bbox(pdf, x0, y0, x1, y1, pageid+1))

            #colleges.loc[n[1]].semesters.iloc[i[0]].courses = courses
            colleges.xs(n[0]).at[n[1], 'semesters'].xs(i[0]).at[i[1], 'courses'] = courses
    return colleges

# ANCHOR: __prepare_courses()
def __prepare_courses(pdf, courses):
    """
    Combines course departments and course numbers into single objects, then
    scrapes target data (description, attempted credits, earned credits, etc...)
    for each course object.

    Returns pd.DataFrame

    Args:
        courses: list of tuples, each containing pairs of dicts
    """
    prepared_courses = []
    for dept, seq in courses:
        if not dept.pageside:
            COLX = COL1_X_VALS
        else:
            COLX = COL2_X_VALS
        course = {
            "dept":        dept.text,
            "seq":         seq.text,
            "x0":          dept.x0,
            "y0":          dept.y0,
            "x1":          seq.x1,
            "y1":          dept.y1,
            "pageid":      dept.pageid,
            "description": scrape_bbox(pdf, courses, COLX.description[0], dept.y0, COLX.description[1], dept.y1, dept.pageid),
            "attempted":   scrape_bbox(pdf, courses, COLX.attempted[0], dept.y0, COLX.attempted[1], dept.y1, dept.pageid),
            "earned":      scrape_bbox(pdf, courses, COLX.earned[0], dept.y0, COLX.earned[1], dept.y1, dept.pageid),
            "grade":       scrape_bbox(pdf, courses, COLX.grade[0], dept.y0, COLX.grade[1], dept.y1, dept.pageid),
            "points":      scrape_bbox(pdf, courses, COLX.points[0], dept.y0, COLX.points[1], dept.y1, dept.pageid),}
        prepared_courses.append(course)

    return pd.DataFrame.from_records(prepared_courses)

# ANCHOR: scrape_targets()
def scrape_bbox(pdf, courses, x0, y0, x1, y1, pageid):
    """
    Returns dict

    Args:
        pdf: loaded pdfquery object contianing transcript
        courses: pd.DataFrame
    """
    raw_scrape = pdf.pq('LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % \
                                                      (x0, y0, x1, y1))
    for i in raw_scrape:
        if i.iterancestors('LTPage').__next__().layout.pageid == pageid:
            if len(i) > 0:
                for j in i:
                    if j!=None and j.text!=None:
                        target = dict(j.attrib, **{"text": j.text.strip(" "),
                                                   "pageid": pageid})
            else:
                if i!=None and i.text!=None:
                    target = dict(i.attrib, **{"text": i.text.strip(" "),
                                               "pageid": pageid})
    return target

# ANCHOR: scrape_course_bbox()
def scrape_course_bbox(pdf, x0, y0, x1, y1, pageid):
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
    courses = zip(depts, seqs)

    return __prepare_courses(pdf, courses)


def prepare_records(pdf, colleges):
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
        records = pd.DataFrame(courses).drop('missing', 1)
    except:
        try:
            records = pd.DataFrame(courses)
        except Exception as e:
            print(e)
            return -1

    return records

def gen_csv(records, filename_out):
    """
    Args:
        filename_out: name of csv file to output
        pdf: loaded pdfquery pdf object
        colleges: dict of dicts of dataframes containing label instances
    """
    records.to_csv(filename_out, index=False)

# !SECTION
