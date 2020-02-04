
#%%
# SECTION: Define Mining Functions

# ANCHOR: load_pdf
def load_pdf(pdf_path):
    pdf = pq.PDFQuery(pdf_path)
    pdf.load()
    return pdf

# ANCHOR: scrape_name
def scrape_name(pdf):
    label = pdf.pq('LTTextLineHorizontal:contains("Name:")')[0][0].text.split("Name: ")[1]
    return label

# ANCHOR: removekey
def removekey(d, key):
    r = dict(d)
    del r[key]
    return r

# ANCHOR: scrape_labels
def scrape_labels(pdf, figures):
    """
    Takes a list of LTFigure objects.

    Returns a dict() containing key-value pairs for each label (text) that we
    want to search for in the PDF. The values of the dict contain lists of
    instances of each label and their respective meta-data (i.e. position on
    page, pageid, etc.)
    """
    pagewidth = float(pdf.get_layout(1).bbox[2])
    semesters = ["Spring", "Summer", "Fall", "Winter",]
    # contains tags that will return 100% relevant results
    labels0 = ["Beginning", "Plan", "Course", "Description", "Grade",]

    # contains tags that will return some superfluous instances
    # that we must handle / filter / remove from results. In particular, every
    # second and third instance will need to be removed from results.
    labels1 = ["Attempted", "Earned", "Points"]

    raw_scrape = dict()
    for label in labels0+labels1:
        raw_scrape[label] = []
    raw_scrape['semester'] = []

    for figure in figures:
        pageid = float(figure.iterancestors('LTPage').__next__().layout.pageid)

        for label in labels0+labels1+semesters:
            for instance_wrapper in figure:
                for instance in instance_wrapper.getchildren():
                    if label in instance.text:
                        if any([s in label for s in semesters]):
                            raw_scrape['semester'].append(dict(instance.attrib,
                                                          **{"pageid":pageid,
                                                             "-y0":-1 * float(instance.get('y0')),
                                                             "text": instance.text,
                                                             "pageside":
                                                             float(instance.attrib['x0']) > pagewidth/2
                                                            }))
                        elif label == instance.text.strip(" ").strip(":") or "----------"+label == instance.text.split(" ")[0]:
                            raw_scrape[label].append(dict(instance.attrib,
                                                          **{"pageid":pageid,
                                                             "-y0":-1 * float(instance.get('y0')),
                                                             "text": instance.text,
                                                             "pageside":
                                                             float(instance.attrib['x0']) > pagewidth/2
                                                            }))

        _instances = raw_scrape
        instances = dict()

        # Convert to dataframe. Multikey sort labels into the order in which
        # they appear in the transcript. Convert numeric strings to floats
        for LABEL in _instances.keys():
            if len(_instances[LABEL]) > 0:
                instances[LABEL] = \
                pd.DataFrame.from_records(_instances[LABEL]).apply( \
                                        lambda df_col: pd.to_numeric(df_col, \
                                            errors='ignore')).round(decimals=0)

    return instances

# ANCHOR: define_college_sections
def define_college_sections(instances, maxpageid):
    """
    Adds a column to the instances["Beginning"] dataframe that indicates
    the last page of that college section of a transcript.
    """
    instances['Beginning']['last_pageid'] = instances['Beginning']['pageid']
    # find the pageid of the last page of each college section
    for n, row in instances['Beginning'].iterrows():
        if n < (len(instances['Beginning']) - 1):
            instances["Beginning"].at[n, 'last_pageid'] = instances['Beginning'].at[n+1, 'pageid'] - 1

        elif n == (len(instances['Beginning']) - 1):
            instances["Beginning"].at[n, 'last_pageid'] = maxpageid

    return instances

# ANCHOR: clean_labels
def clean_labels(instances):
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

# ANCHOR: group_colleges
def group_colleges(instances):
    colleges = dict()
    labels = ["Beginning", "Plan", "Course", "Description",
              "Grade", "Points", "Attempted", "Earned", "semester"]
    halfpagewidth = 792/2
    instances['Beginning']['name'] =''

    for n, row in instances['Beginning'].iterrows():
        collegename = row.text.split(" ")[2]
        colleges[collegename] = dict()
        instances['Beginning'].at[n, "name"] = collegename
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
                                            (df['x0'] > halfpagewidth)
                                        )
                                    )
                                )].reset_index(drop=True)
    return colleges

# ANCHOR: scrape_plans
def scrape_plans(pdf, colleges):
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

# ANCHOR: scrapecoursenames
def scrapecoursetargets(colleges):
    bottom_of_page = 72
    top_of_page = float(pdf.pq('LTTextLineHorizontal:contains("Print")')[0].get('y0'))
    rightside_of_page = 792
    middle_of_page = 792/2
    leftside_of_page = 0

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
                # draw boox around part on first page
                depts, seqs = \
                    scrapecourseid(
                        pdf = pdf,
                        row = row,
                        x0 = row['x0']-1,
                        y0 = bottom_of_page,
                        x1 = instances['Description'].loc[n]['x0']+1,
                        y1 = row['y0']+1,)
                for dept, seq in zip(depts, seqs):
                    targets['dept'].append(dept)
                    targets['seq'].append(seq)
                    targets_ = scrape_targets(x0 = 511, y0 = seq['y0'], y1 = seq['y1'], pageid = seq['pageid'])
                    for key in targets_.keys():
                        targets[key].append(targets_[key])

                # draw boox around part on second page
                depts, seqs = \
                    scrapecourseid(
                        pdf = pdf,
                        row = row,
                        x0 = leftside_of_page-1,
                        y0 = instances["Points"].loc[n*2+1]['y1']-1,
                        x1 = 162+1,
                        y1 = top_of_page,)
                for dept, seq in zip(depts, seqs):
                    targets['dept'].append(dept)
                    targets['seq'].append(seq)
                    targets_ = scrape_targets(x0 = 161, y0 = seq['y0'], y1 = seq['y1'], pageid = seq['pageid'])
                    for key in targets_.keys():
                        targets[key].append(targets_[key])

            # CASE: semester section starts in first column of page and ends in second column
            elif instances["Points"].loc[n*2+1]['pageside'] != row['pageside']:
                # draw boox around part in first column
                depts, seqs = \
                    scrapecourseid(
                        pdf = pdf,
                        row = row,
                        x0 = row['x0']-1,
                        y0 = bottom_of_page,
                        x1 = instances['Description'].loc[n]['x0']+1,
                        y1 = row['y0']+1,)
                for dept, seq in zip(depts, seqs):
                    targets['dept'].append(dept)
                    targets['seq'].append(seq)
                    targets_ = scrape_targets(x0 = 161, y0 = seq['y0'], y1 = seq['y1'], pageid = seq['pageid'])
                    for key in targets_.keys():
                        targets[key].append(targets_[key])

                # draw boox around part in second column
                depts, seqs = \
                    scrapecourseid(
                        pdf = pdf,
                        row = row,
                        x0 = middle_of_page,
                        y0 = instances["Points"].loc[n*2+1]['y1']-1,
                        x1 = 512+1,
                        y1 = top_of_page,)
                for dept, seq in zip(depts, seqs):
                    targets['dept'].append(dept)
                    targets['seq'].append(seq)
                    targets_ = scrape_targets(x0 = 511, y0 = seq['y0'], y1 = seq['y1'], pageid = seq['pageid'])
                    for key in targets_.keys():
                        targets[key].append(targets_[key])

            # CASE: semester section starts and ends in same column on same page
            else:
                depts, seqs = \
                    scrapecourseid(
                        pdf = pdf,
                        row = row,
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
                    targets_ = scrape_targets(x0 = x0, y0 = seq['y0'], y1 = seq['y1'], pageid = seq['pageid'])
                    for key in targets_.keys():
                        targets[key].append(targets_[key])

            for label in targets.keys():
                for target_instance in targets[label]:
                    if target_instance != None:
                        target_instance['label'] = label

            instance_targets = list( zip( * [targets[key] for key in targets]))
            #instance_targets = [ dict(targets[key], **{"label":key}) for key in targets ]
            #
            instances['Course'].at[n, 'targets'] = instance_targets
        colleges[college] = instances
    return colleges


# ANCHOR:scrapecourseid
def scrapecourseid(pdf, row, x0, y0, x1, y1):
    """
    For a particular semester / bbox area, returns two ordered lists of dicts:
    course departments and course sequence numbers. Dicts contain the metadata
    for each dept/seq.
    """
    targets = []
    raw_scrape = pdf.pq('LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % \
                                                        (x0, y0, x1, y1))
    for i in raw_scrape:
        if i.iterancestors('LTPage').__next__().layout.pageid == row['pageid']:
            if len(i) > 0:
                for j in i:
                    if j!=None and j.text!=None:
                        targets.append(( dict(j.attrib, **{"pageid": row['pageid'],
                                                        "text": j.text.strip(" ")}
                                            )))
            else:
                if i!=None and i.text!=None:
                    targets.append(( dict(i.attrib, **{"pageid": row['pageid'],
                                                    "text": i.text.strip(" ")}
                                        )))

    depts = [i for i in targets if i['text'].isalpha()]
    seqs = [i for i in targets if any(j.isnumeric() for j in i['text'])]

    return depts, seqs


# ANCHOR: scrape_targets
def scrape_targets(x0, y0, y1, pageid):
    # generate pairs of (x0, x1)---the start and stop x-coordinates for each target label
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


def gen_csv(pdf, colleges):
    name = scrape_name(pdf)
    courses = []
    for college in colleges:
        for n, row in colleges[college]['Course'].iterrows():
            course_targets = row['targets']
            for target_set in course_targets:
                courses.append(
                    dict({(target['label'] if target!=None else "missing") : (target['text'] if target!=None else None) \
                         for target in target_set}, **{"semester":colleges[college]['semester'].loc[n]['text'],
                                                       "plan": colleges[college]['Plan'].loc[n]['target']['text'],
                                                       "college": college,
                                                       "name": name})
                )
    try:
        return pd.DataFrame(courses).drop('missing', 1)
    except Exception as e:
        if e == "['missing'] not found in axis":
            return pd.DataFrame(courses)
        else:
            print(e)
# !SECTION

# SECTION: Mine data
#%%
# ANCHOR: Load Data
import pandas as pd
import pdfquery as pq
pdf = load_pdf('C:\\Users\\allen\\Documents\\GitHub\\Upwork\\data\\sample2.pdf')


#%%
# ANCHOR: Scrape & Clean Data
figures = pdf.pq('LTFigure')
instances = scrape_labels(pdf, figures)
instances = define_college_sections(instances, maxpageid = len(figures))
instances = clean_labels(instances)
colleges = group_colleges(instances)
colleges = scrape_plans(pdf, colleges)
colleges = scrapecoursetargets(colleges)
# !SECTION


# SECTION: Tests
#%%
# ANCHOR: Import Visual Test Modules
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import gridspec
import numpy as np
from jupyterthemes import jtplot
jtplot.style(theme='solarizedl')

#%%
# ANCHOR: Visual Test
npages = len(figures)
ncol = 1
nrow = npages

fig, ax = plt.subplots(nrow, ncol,
                       figsize=(2*ncol*15.3 +1, nrow*19.8 +1), dpi=72,
                       gridspec_kw = {'wspace':0.0, 'hspace':0.0,
                                       'top':1.-0.5/(nrow+1), 'bottom':0.5/(nrow+1),
                                       'left':0.5/(ncol+1), 'right':1-0.5/(ncol+1)},)

# bbox and text colors for image-reconstruction of scraped pdf targets
colors = {'Beginning':"red", 'Plan':"yellow",
              'Course':"green", 'Description':"blue", 'Grade':"indigo",
              'Attempted':"violet", 'Earned':"magenta", 'Points':"cyan",
              'semester':"purple"}

def drawpage(i):
    ax[i].set(xlim=[0, 792], ylim=[0,612])
    ax[i].set_xticklabels([]); ax[i].set_yticklabels([])
    fig.canvas.draw()
    rect = mpatches.Rectangle( \
                (0,0), 792, 612, edgecolor="cyan", lw = 10)
    ax[i].add_artist(rect); ax[i].draw_artist(rect)
    ax[i].text(10, 602, ("(Page %s)"% (i+1)), color="black")

def drawcollegelabels(instances):
    for key in instances.keys():
        for n, row in instances[key].iterrows():
            pageid, text = int(row.pageid-1), row.text
            x, y = row.x0, row.y0
            w, h = row.width, row.height
            rect = mpatches.Rectangle((x, y), w, h, edgecolor=colors[key])
            ax[pageid].add_artist(rect), ax[pageid].draw_artist(rect)
            #ax[pageid].text(x, y, ("(%s)(%s, %s)"% (n, x,y))+text, fontsize=8, color=colors[key])
            #ax[pageid].text(x, y, ("(%s)(%s, %s)"% (n,x,y))+text[0:5], color=colors[key])
            ax[pageid].text(x, y-1, ("%s"% (row.text)), fontsize=9, color=colors[key])

def drawbbox(i, x0, y0, x1, y1, bboxcolor):
    w = x1 - x0
    h = y1 - y0
    rect = mpatches.Rectangle((x0, y0), w, h, edgecolor=bboxcolor)
    ax[int(i)].add_artist(rect), ax[int(i)].draw_artist(rect)

def draw_targetarea_bboxes(instances):
    bottom_of_page = 72
    top_of_page = float(pdf.pq('LTTextLineHorizontal:contains("Print")')[0].get('y0'))
    rightside_of_page = 792
    middle_of_page = 792/2
    leftside_of_page = 0
    bboxcolor = "black"
    for n, row in instances['Course'].iterrows():
        # CASE: semester section starts on one page of the transcript and ends on the next
        if instances["Points"].loc[n*2+1]['pageid'] > row['pageid']:
            # draw boox around part on first page
            drawbbox(i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = bottom_of_page,
                     x1 = rightside_of_page,
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

            # draw boox around part on second page
            drawbbox(i = row['pageid'],
                     x0 = leftside_of_page,
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = middle_of_page,
                     y1 = top_of_page,
                     bboxcolor = bboxcolor)

        # CASE: semester section starts in first column of page and ends in second column
        elif instances["Points"].loc[n*2+1]['pageside'] != row['pageside']:
            # draw boox around part in first columns
            drawbbox(i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = bottom_of_page,
                     x1 = middle_of_page,
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

            # draw boox around part in second column
            drawbbox(i = row['pageid']-1,
                     x0 = middle_of_page,
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = instances["Points"].loc[n*2+1]['x1'],
                     y1 = top_of_page,
                     bboxcolor = bboxcolor)

        # CASE: semester section starts and ends in same column on same page
        else:
            drawbbox(i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = instances["Points"].loc[n*2+1]['x1'],
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

def draw_plan_bboxes(instances):
    for n, row in instances['Plan'].iterrows():
        drawbbox(i = row['pageid'] - 1,
                 x0 = row['x1'],
                 y0 = row['y0'],
                 x1 = row['x1'] + 300,
                 y1 = row['y1'],
                 bboxcolor = "black")

# ANCHOR: draw_plan_targets
def draw_plan_targets(instances):
    for n, row in instances['Plan'].iterrows():
        i = row['pageid'] - 1
        x = row['x1']
        y = row['y0']
        textcolor = "yellow"
        text = row['target']['text']
        ax[int(i)].text(x, y, text, fontsize=9, color=textcolor)

# ANCHOR: draw_course_targets
def draw_course_targets(colleges):
    for college in colleges:
        instances = colleges[college]
        for n, row in instances['Course'].iterrows():
            for course_targets_dict in row['targets']:
                for target_instance in course_targets_dict:
                    if target_instance != None:
                        i = target_instance['pageid'] - 1
                        x = target_instance['x0']
                        y = target_instance['y0']
                        textcolor = "black"
                        text = target_instance['text']
                        ax[int(i)].text(float(x), float(y), text, fontsize=9, color=textcolor)
                    else:
                        continue

def draw_course_bboxes(instances):
    bottom_of_page = 72
    top_of_page = float(pdf.pq('LTTextLineHorizontal:contains("Print")')[0].get('y0'))
    rightside_of_page = 792
    middle_of_page = 792/2
    leftside_of_page = 0
    bboxcolor = "green"
    for n, row in instances['Course'].iterrows():
        # CASE: semester section starts on one page of the transcript and ends on the next
        if instances["Points"].loc[n*2+1]['pageid'] > row['pageid']:
            # draw boox around part on first page
            drawbbox(i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = bottom_of_page,
                     x1 = instances['Description'].loc[n]['x0'],
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

            # draw boox around part on second page
            drawbbox(i = row['pageid'],
                     x0 = leftside_of_page,
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = 162,
                     y1 = top_of_page,
                     bboxcolor = bboxcolor)

        # CASE: semester section starts in first column of page and ends in second column
        elif instances["Points"].loc[n*2+1]['pageside'] != row['pageside']:
            # draw boox around part in first column
            drawbbox(i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = bottom_of_page,
                     x1 = instances['Description'].loc[n]['x0'],
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

            # draw boox around part in second column
            drawbbox(i = row['pageid']-1,
                     x0 = middle_of_page,
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = 512,
                     y1 = top_of_page,
                     bboxcolor = bboxcolor)

        # CASE: semester section starts and ends in same column on same page
        else:
            drawbbox(i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = instances['Description'].loc[n]['x0'],
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

# ANCHOR: scrape_courses
def draw_course_target_bboxes(pdf, colleges):
    """
    Scrapes each course and all corresponding data targets including
    course name, course number, course description, as well as the
    student's attempted credits, earned credits, grade, and points.
    """
    keys = ["Course", "Plan", "Description", "Attempted", "Earned", "Grade", "Points"]
    for college in colleges:
        instances = colleges[college]
        instances["Course"]['target'] = {'course':'',
                                         'number':'',
                                         'description':'',
                                         'attempted':'',
                                         'earned':'',
                                         'grade':'',
                                         'points':''}

        for n, row in instances['Course'].iterrows():
            x0 = row['x1'] -1
            y0 = row['y0'] -1
            x1 = row['x1'] + 300
            y1 = row['y1'] +1
            raw_scrape = pdf.pq('LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % \
                                                                (x0, y0, x1, y1))
            for i in raw_scrape:
                if i.iterancestors('LTPage').__next__().layout.pageid == row['pageid']:
                    target_text = ''.join([j.text for j in i])

            instances["Plan"].at[n, 'target'] = target_text
            colleges[college]["Plan"] = instances["Plan"]
    return colleges



# ANCHOR: make drawing
for i in range(npages):
    drawpage(i)

for college in colleges:
    df = colleges[college]["Beginning"]
    instances = colleges[college]

    drawcollegelabels(instances)
    draw_targetarea_bboxes(instances)
    draw_plan_bboxes(instances)
    draw_course_bboxes(instances)
    draw_plan_targets(instances)

draw_course_targets(colleges)


plt.show()
# !SECTION


#%%
