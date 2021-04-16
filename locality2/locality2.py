from math import sqrt
from random import random, randrange, seed
import matplotlib
import seaborn
import pandas
from models import *
from methods import *
seaborn.set(style="darkgrid")
matplotlib.rcParams["figure.dpi"] = 300
matplotlib.rcParams["font.family"] = "serif"
matplotlib.rcParams["font.serif"] = ["Times New Roman"]
seed(0)

num_professions = 2  # This is a constant; changing it requires
                     # further code modifications
num_agents = 100
prof1 = 50
prof2 = num_agents - prof1
professions = [0] * prof1 + [1] * prof2
random_samples = 1000

def _distribute_caps_and_jobs(num_localities):
    assert num_localities <= num_agents
    # Distribute caps adding up to `num_agents` over all localities,
    # ensuring that each locality has at least one space
    locality_caps = [1 for _ in range(num_localities)]
    for _ in range(num_agents - num_localities):
        locality_caps[randrange(len(locality_caps))] += 1
    # Job numbers add up to the cap per locality, but `prof1` jobs for
    # profession 1 and `prof2` jobs for profession 2 are randomly
    # distributed inside these bounds.
    prof1_jobs = prof1  # Remaining jobs to distribute
    prof2_jobs = prof2
    job_numbers = []
    for cap in locality_caps:
        p1, p2 = 0, 0
        for _ in range(cap):
            if random() < prof1_jobs / (prof1_jobs + prof2_jobs):
                p1 += 1
                prof1_jobs -= 1
                assert prof1_jobs >= 0
            else:
                p2 += 1
                prof2_jobs -= 1
                assert prof2_jobs >= 0
        job_numbers.append((p1, p2))
    return locality_caps, job_numbers

def test_correction(num_localities):
    locality_caps, job_numbers = \
        _distribute_caps_and_jobs(num_localities)
    qualification_probabilities = \
        [[random()] * num_localities for _ in range(num_agents)]
    correction_functions = []
    for p1, p2 in job_numbers:
        # The default parameters in the lambdas are never used, but are
        # a way of getting Python's peculiar binding behavior to work.
        # See https://docs.python.org/3/faq/programming.html#why-do-
        # lambdas-defined-in-a-loop-with-different-values-all-return-
        # the-same-result for more information.
        correction_functions.append((lambda x, P1=p1: min(x, P1),
                                     lambda x, P2=p2: min(x, P2)))
    model = RetroactiveCorrectionModel(num_agents, locality_caps,
                                       num_professions, professions,
                                       qualification_probabilities,
                                       correction_functions,
                                       random_samples)
    return model

def test_interview(num_localities):
    locality_caps, job_numbers = \
        _distribute_caps_and_jobs(num_localities)
    compatibility_probabilities = [random() for _ in range(num_agents)]
    model = InterviewModel(num_agents, locality_caps, num_professions,
                           professions, job_numbers,
                           compatibility_probabilities, random_samples)
    return model

def test_coordination(num_localities):
    locality_caps, job_numbers = \
        _distribute_caps_and_jobs(num_localities)
    locality_num_jobs = locality_caps
    compatibility_probabilities = []
    for _ in range(prof1):
        competency = random()
        compatibility_probabilities.append(
            [[competency] * p1 + [0.] * p2 for p1, p2 in job_numbers])
    for _ in range(prof2):
        competency = random()
        compatibility_probabilities.append(
            [[0.] * p1 + [competency] * p2 for p1, p2 in job_numbers])
    model = CoordinationModel(num_agents, locality_caps,
                              locality_num_jobs,
                              compatibility_probabilities,
                              random_samples)
    return model

settings = {"correction": test_correction, "interview": test_interview,
            "coordination": test_coordination}

data = []

def sample(logger, setting, num_localities):
    m = settings[setting](num_localities)
    greedy = greedy_algorithm(m)[1]
    gsemo = gsemo_algorithm(m)[1]
    datum = {}
    datum["number of localities"] = num_localities
    datum["greedy"] = greedy
    datum["gsemo"] = gsemo
    if greedy > 0.0005:
        datum["gsemo / greedy"] = gsemo / greedy
    else:
        datum["gsemo / greedy"] = None
    datum["model"] = setting
    print(f'gsemo = {gsemo}',f' greedy = {greedy}', f' gsemo / greedy = {gsemo} / {greedy}')
    logger.info(f'gsemo = {gsemo}, greedy = {greedy}, gsemo / greedy = {gsemo} / {greedy}')
    data.append(datum)
    return datum

from datetime import datetime
import logging
import os.path
import time
logger = logging.getLogger()
logger.setLevel(logging.INFO)
rq = time.strftime('%Y%m%d%H%M', time.localtime(time.time()))
log_path = os.path.dirname(os.getcwd()) + '/Logs5/'
log_name = log_path + rq + '.log'
logfile = log_name
fh = logging.FileHandler(logfile, mode='w')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

for _ in range(2):
    for num_localities in range(1,21):
        for setting in settings:
            sample(logger, setting, num_localities)
            print(datetime.now(), setting, num_localities, len(data))

def _format_y(ratio):
    return "{:,.1%}".format(ratio-1)

def plot():
    d = pandas.DataFrame(data)
    y_min = 0.9
    y_max = 1.2
    g = seaborn.relplot(x="number of localities",
                        y="gsemo / greedy", col="model", data=d,
                        facet_kws={"ylim": (y_min, y_max)})
    for i, setting in enumerate(settings):
        up_outliers = {}
        down_outliers = {}
        for datum in data:
            if datum["model"] != setting:
                continue
            ga = datum['gsemo / greedy']
            nl = datum["number of localities"]
            if ga > y_max:
                if nl not in up_outliers:
                    up_outliers[nl] = []
                up_outliers[nl].append(ga)
            if ga < y_min:
                if nl not in down_outliers:
                    down_outliers[nl] = []
                down_outliers[nl].append(ga)
        ax = g.axes[0][i]
        ax.xaxis.set_major_locator(
            matplotlib.ticker.MultipleLocator(5))
        ax.yaxis.set_major_locator(
            matplotlib.ticker.MultipleLocator(0.05))
        vals = ax.get_yticks()
        ax.set_yticklabels([_format_y(x) for x in vals])
        ax.set_ylabel("improvement of gsemo over greedy")
        for nl in up_outliers:
            label = "\n".join(_format_y(ga) for ga in up_outliers[nl])
            ax.annotate(label, xy=(nl, y_max),
                        xytext=(nl, y_max-0.025),
                        horizontalalignment="center",
                        verticalalignment="top",
                        arrowprops={"color": "b", "arrowstyle": "->"})
        for nl in down_outliers:
            label = "\n".join(_format_y(ga) for ga in down_outliers[nl])
            ax.annotate(label, xy=(nl, y_min),
                        xytext=(nl, y_min+0.025),
                        horizontalalignment="center",
                        verticalalignment="bottom",
                        arrowprops={"color": "b", "arrowstyle": "->"})
    g.savefig("num_localities.pdf")

plot()