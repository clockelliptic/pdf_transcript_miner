#%%
# ANCHOR: Imports
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import gridspec
import numpy as np

# ANCHOR: Plot style
try:
    from jupyterthemes import jtplot
    jtplot.style(theme='solarizedl')
except:
    None

# ANCHOR: Visual Test

def setup_plot(npages):
    NROW = npages
    NCOL = 1
    FIG, AX = plt.subplots(NROW, NCOL,
                        figsize=(2*NCOL*15.3 +1, NROW*19.8 +1), dpi=72,
                        gridspec_kw = {'wspace':0.0, 'hspace':0.0,
                                        'top':1.-0.5/(NROW+1), 'bottom':0.5/(NROW+1),
                                        'left':0.5/(NCOL+1), 'right':1-0.5/(NCOL+1)},)
    return FIG, AX

# bbox and text COLORS for image-reconstruction of scraped pdf targets
COLORS = {'College':"red", 'Plan':"yellow",
          'Course':"green", 'Description':"blue", 'Grade':"indigo",
          'Attempted':"violet", 'Earned':"magenta", 'Points':"cyan",
          'semester':"purple"}

def drawpage(FIG, AX, i):
    AX[i].set(xlim=[0, 792], ylim=[0,612])
    AX[i].set_xticklabels([]); AX[i].set_yticklabels([])
    FIG.canvas.draw()
    rect = mpatches.Rectangle( \
                (0,0), 792, 612, edgecolor="cyan", lw = 10)
    AX[i].add_artist(rect); AX[i].draw_artist(rect)
    AX[i].text(10, 602, ("(Page %s)"% (i+1)), color="black")

def drawcollegelabels(FIG, AX, instances):
    for key in instances.keys():
        for n, row in instances[key].iterrows():
            pageid, text = int(row.pageid-1), row.text
            x, y = row.x0, row.y0
            w, h = row.width, row.height
            rect = mpatches.Rectangle((x, y), w, h, edgecolor=COLORS[key])
            AX[pageid].add_artist(rect), AX[pageid].draw_artist(rect)
            #AX[pageid].text(x, y, ("(%s)(%s, %s)"% (n, x,y))+text, fontsize=8, color=COLORS[key])
            AX[pageid].text(x, y, ("(%s, %s)"% (x,y)), fontsize=7, color=COLORS[key])
            #AX[pageid].text(x, y-1, ("%s"% (row.text)), fontsize=9, color=COLORS[key])

def drawbbox(FIG, AX, i, x0, y0, x1, y1, bboxcolor):
    w = x1 - x0
    h = y1 - y0
    rect = mpatches.Rectangle((x0, y0), w, h, edgecolor=bboxcolor)
    AX[int(i)].add_artist(rect), AX[int(i)].draw_artist(rect)

def draw_targetarea_bboxes(FIG, AX, pdf, instances):
    bottom_of_page = 72
    top_of_page = float(pdf.pq('LTTextLineHorizontal:contains("Print")')[0].get('y0'))
    rightside_of_page = 792
    middle_of_page = 792/2
    leftside_of_page = 0
    bboxcolor = "black"
    for n, row in instances['Course'].iterrows():
        # CASE: semester section starts on one page of the transcript and ends on the next
        if instances["Points"].loc[n*2+1]['pageid'] > row['pageid']:
            # draw bbox around part on first page
            drawbbox(FIG, AX,
                     i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = bottom_of_page,
                     x1 = rightside_of_page,
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

            # draw bbox around part on second page
            drawbbox(FIG, AX,
                     i = row['pageid'],
                     x0 = leftside_of_page,
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = middle_of_page,
                     y1 = top_of_page,
                     bboxcolor = bboxcolor)

        # CASE: semester section starts in first column of page and ends in second column
        elif instances["Points"].loc[n*2+1]['pageside'] != row['pageside']:
            # draw bbox around part in first columns
            drawbbox(FIG, AX,
                     i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = bottom_of_page,
                     x1 = middle_of_page,
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

            # draw bbox around part in second column
            drawbbox(FIG, AX,
                     i = row['pageid']-1,
                     x0 = middle_of_page,
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = instances["Points"].loc[n*2+1]['x1'],
                     y1 = top_of_page,
                     bboxcolor = bboxcolor)

        # CASE: semester section starts and ends in same column on same page
        else:
            drawbbox(FIG, AX,
                     i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = instances["Points"].loc[n*2+1]['x1'],
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

def draw_plan_bboxes(FIG, AX, instances):
    for n, row in instances['Plan'].iterrows():
        drawbbox(FIG, AX,
                 i = row['pageid'] - 1,
                 x0 = row['x1'],
                 y0 = row['y0'],
                 x1 = row['x1'] + 300,
                 y1 = row['y1'],
                 bboxcolor = "black")

# ANCHOR: draw_plan_targets
def draw_plan_targets(FIG, AX, instances):
    for n, row in instances['Plan'].iterrows():
        i = row['pageid'] - 1
        x = row['x1']
        y = row['y0']
        textcolor = "yellow"
        text = row['target']['text']
        AX[int(i)].text(x, y, text, fontsize=9, color=textcolor)

# ANCHOR: draw_course_targets
def draw_course_targets(FIG, AX, colleges):
    for college in colleges:
        instances = colleges[college]
        for n, row in instances['Course'].iterrows():
            for course_targets_dict in row['targets']:
                for target_instance in course_targets_dict:
                    if target_instance != None:
                        i = target_instance['pageid'] - 1
                        x = round(float(target_instance['x0']))
                        y = round(float(target_instance['y0']))
                        textcolor = "black"
                        text = target_instance['text']
                        #AX[int(i)].text(float(x), float(y), text, fontsize=7, color=textcolor)
                        AX[int(i)].text(x, y, "(%s, %s)" % (x, y), fontsize=7, color=textcolor)
                    else:
                        continue

def draw_course_bboxes(FIG, AX, pdf, instances):
    bottom_of_page = 72
    top_of_page = float(pdf.pq('LTTextLineHorizontal:contains("Print")')[0].get('y0'))
    rightside_of_page = 792
    middle_of_page = 792/2
    leftside_of_page = 0
    bboxcolor = "green"
    for n, row in instances['Course'].iterrows():
        # CASE: semester section starts on one page of the transcript and ends on the next
        if instances["Points"].loc[n*2+1]['pageid'] > row['pageid']:
            # draw bbox around part on first page
            drawbbox(FIG, AX,
                     i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = bottom_of_page,
                     x1 = instances['Description'].loc[n]['x0'],
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

            # draw bbox around part on second page
            drawbbox(FIG, AX,
                     i = row['pageid'],
                     x0 = leftside_of_page,
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = 162,
                     y1 = top_of_page,
                     bboxcolor = bboxcolor)

        # CASE: semester section starts in first column of page and ends in second column
        elif instances["Points"].loc[n*2+1]['pageside'] != row['pageside']:
            # draw bbox around part in first column
            drawbbox(FIG, AX,
                     i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = bottom_of_page,
                     x1 = instances['Description'].loc[n]['x0'],
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

            # draw bbox around part in second column
            drawbbox(FIG, AX,
                     i = row['pageid']-1,
                     x0 = middle_of_page,
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = 512,
                     y1 = top_of_page,
                     bboxcolor = bboxcolor)

        # CASE: semester section starts and ends in same column on same page
        else:
            drawbbox(FIG, AX,
                     i = row['pageid']-1,
                     x0 = row['x0'],
                     y0 = instances["Points"].loc[n*2+1]['y1'],
                     x1 = instances['Description'].loc[n]['x0'],
                     y1 = row['y0'],
                     bboxcolor = bboxcolor)

# ANCHOR: scrape_courses
def draw_course_target_bboxes(FIG, AX, pdf, colleges):
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
# !SECTION

# ANCHOR: Draw image of reconstructed PDF from scraped data
def plot_transcript(FIG, AX, pdf, npages, colleges):
    for i in range(npages):
        drawpage(FIG, AX, i)

    for college in colleges:
        df = colleges[college]["College"]
        instances = colleges[college]

        drawcollegelabels(FIG, AX, instances)
        draw_targetarea_bboxes(FIG, AX, pdf, instances)
        draw_plan_bboxes(FIG, AX, instances)
        draw_course_bboxes(FIG, AX, pdf, instances)
        draw_plan_targets(FIG, AX, instances)

    draw_course_targets(FIG, AX, colleges)
plt.show()
# !SECTION