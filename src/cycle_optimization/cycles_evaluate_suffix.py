'''
EVALUATES the trained model with the techniques for diminishing the cycle repetitions

Author: Anton Yeshchenko
'''

from __future__ import division

import re

from keras.models import load_model
import csv
import copy
import numpy as np
import distance
from itertools import izip
from jellyfish._jellyfish import damerau_levenshtein_distance
import unicodecsv
from sklearn import metrics
from math import sqrt
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from collections import Counter

from src.formula_verificator import verify_formula_as_compliant
from src.shared_variables import eventlog, getUnicode_fromInt, path_to_model_file, prefix_size_fed
from src.support_scripts.prepare_data import repetitions, amplify, getSymbolAmpl

start_time = time.time()

csvfile = open('../../data/%s' % eventlog, 'r')
spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')

next(spamreader, None)  # skip the headers


lastcase = ''
line = ''
firstLine = True
lines = []
timeseqs = []  # relative time since previous event
timeseqs2 = [] # relative time since case start
timeseqs3 = [] # absolute time of previous event
times = []
times2 = []
times3 = []
numlines = 0
casestarttime = None
lasteventtime = None

for row in spamreader:
    t = time.strptime(row[2], "%Y-%m-%d %H:%M:%S")
    if row[0]!=lastcase:
        casestarttime = t
        lasteventtime = t
        lastcase = row[0]
        if not firstLine:
            lines.append(line)
            timeseqs.append(times)
            timeseqs2.append(times2)
            timeseqs3.append(times3)
        line = ''
        times = []
        times2 = []
        times3 = []
        numlines+=1
    line+= getUnicode_fromInt(row[1])
    timesincelastevent = datetime.fromtimestamp(time.mktime(t))-datetime.fromtimestamp(time.mktime(lasteventtime))
    timesincecasestart = datetime.fromtimestamp(time.mktime(t))-datetime.fromtimestamp(time.mktime(casestarttime))
    midnight = datetime.fromtimestamp(time.mktime(t)).replace(hour=0, minute=0, second=0, microsecond=0)
    timesincemidnight = datetime.fromtimestamp(time.mktime(t))-midnight
    timediff = 86400 * timesincelastevent.days + timesincelastevent.seconds
    timediff2 = 86400 * timesincecasestart.days + timesincecasestart.seconds
    times.append(timediff)
    times2.append(timediff2)
    times3.append(datetime.fromtimestamp(time.mktime(t)))
    lasteventtime = t
    firstLine = False

# add last case
lines.append(line)
timeseqs.append(times)
timeseqs2.append(times2)
timeseqs3.append(times3)
numlines+=1

divisor = np.mean([item for sublist in timeseqs for item in sublist])
print('divisor: {}'.format(divisor))
divisor2 = np.mean([item for sublist in timeseqs2 for item in sublist])
print('divisor2: {}'.format(divisor2))
divisor3 = np.mean(map(lambda x: np.mean(map(lambda y: x[len(x)-1]-y, x)), timeseqs2))
print('divisor3: {}'.format(divisor3))

elems_per_fold = int(round(numlines/3))

fold1and2lines = lines[:2*elems_per_fold]

step = 1
sentences = []
softness = 0
next_chars = []
fold1and2lines = map(lambda x: x+'!',fold1and2lines)
maxlen = max(map(lambda x: len(x),fold1and2lines))

chars = map(lambda x : set(x),fold1and2lines)
chars = list(set().union(*chars))
chars.sort()
target_chars = copy.copy(chars)
chars.remove('!')
print('total chars: {}, target chars: {}'.format(len(chars), len(target_chars)))
char_indices = dict((c, i) for i, c in enumerate(chars))
indices_char = dict((i, c) for i, c in enumerate(chars))
target_char_indices = dict((c, i) for i, c in enumerate(target_chars))
target_indices_char = dict((i, c) for i, c in enumerate(target_chars))
print(indices_char)

#we only need the third fold, because first two were used for training

fold3 = lines[2*elems_per_fold:]
fold3_t = timeseqs[2*elems_per_fold:]
fold3_t2 = timeseqs2[2*elems_per_fold:]
fold3_t3 = timeseqs3[2*elems_per_fold:]

lines = fold3
lines_t = fold3_t
lines_t2 = fold3_t2
lines_t3 = fold3_t3

# set parameters
predict_size = maxlen

# load model, set this to the model generated by train.py
model = load_model(path_to_model_file)

# define helper functions

#this one encodes the current sentence into the onehot encoding
def encode(sentence, times, times3, maxlen=maxlen):
    num_features = len(chars)+5
    X = np.zeros((1, maxlen, num_features), dtype=np.float32)
    leftpad = maxlen-len(sentence)
    times2 = np.cumsum(times)
    for t, char in enumerate(sentence):
        midnight = times3[t].replace(hour=0, minute=0, second=0, microsecond=0)
        timesincemidnight = times3[t]-midnight
        multiset_abstraction = Counter(sentence[:t+1])
        for c in chars:
            if c==char:
                X[0, t+leftpad, char_indices[c]] = 1
        X[0, t+leftpad, len(chars)] = t+1
        X[0, t+leftpad, len(chars)+1] = times[t]/divisor
        X[0, t+leftpad, len(chars)+2] = times2[t]/divisor2
        X[0, t+leftpad, len(chars)+3] = timesincemidnight.seconds/86400
        X[0, t+leftpad, len(chars)+4] = times3[t].weekday()/7
    return X



#find cycles and modify the probability functionality goes here
stop_symbol_probability_amplifier_current = 1


one_ahead_gt = []
one_ahead_pred = []

two_ahead_gt = []
two_ahead_pred = []

three_ahead_gt = []
three_ahead_pred = []

#select only lines with formula verified
lines_v = []
lines_t_v = []
lines_t2_v = []
lines_t3_v = []
for line, times, times2, times3 in izip(lines, lines_t, lines_t2, lines_t3):
    if verify_formula_as_compliant(line):
        lines_v.append(line)
        lines_t_v.append(times)
        lines_t2_v.append(times2)
        lines_t3_v.append(times3)

lines = lines_v
lines_t = lines_t_v
lines_t2 = lines_t2_v
lines_t3 = lines_t3_v






with open('../output_files/results/suffix_and_remaining_time3_%s' % eventlog, 'wb') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(["Prefix length", "Groud truth", "Predicted", "Levenshtein", "Damerau", "Jaccard", "Ground truth times", "Predicted times", "RMSE", "MAE", "Median AE"])
    for prefix_size in range(3,10):
        print(prefix_size)
        for line, times, times2, times3 in izip(lines, lines_t, lines_t2, lines_t3):
            times.append(0)
            cropped_line = ''.join(line[:prefix_size])
            cropped_times = times[:prefix_size]
            cropped_times3 = times3[:prefix_size]
            if len(times2)<prefix_size:
                continue # make no prediction for this case, since this case has ended already
            ground_truth = ''.join(line[prefix_size:prefix_size+predict_size])
            ground_truth_t = times2[prefix_size-1]
            case_end_time = times2[len(times2)-1]
            ground_truth_t = case_end_time-ground_truth_t
            predicted = ''
            total_predicted_time = 0
            for i in range(predict_size):
                enc = encode(cropped_line, cropped_times, cropped_times3)
                y = model.predict(enc, verbose=0) # make predictions
                # split predictions into seperate activity and time predictions
                y_char = y[0][0]
                y_t = y[1][0][0]
                prediction = getSymbolAmpl(y_char,target_indices_char, stop_symbol_probability_amplifier_current) # undo one-hot encoding
                cropped_line += prediction


                stop_symbol_probability_amplifier_current = amplify(cropped_line)



                if y_t<0:
                    y_t=0
                cropped_times.append(y_t)
                if prediction == '!': # end of case was just predicted, therefore, stop predicting further into the future
                    one_ahead_pred.append(total_predicted_time)
                    one_ahead_gt.append(ground_truth_t)
                    print('! predicted, end case')
                    break
                y_t = y_t * divisor3
                cropped_times3.append(cropped_times3[-1] + timedelta(seconds=y_t))
                total_predicted_time = total_predicted_time + y_t
                predicted += prediction
            output = []
            if len(ground_truth)>0:
                output.append(prefix_size)
                output.append(unicode(ground_truth).encode("utf-8"))
                output.append(unicode(predicted).encode("utf-8"))
                output.append(1 - distance.nlevenshtein(predicted, ground_truth))
                dls = 1 - (damerau_levenshtein_distance(unicode(predicted), unicode(ground_truth)) / max(len(predicted),len(ground_truth)))
                if dls<0:
                    dls=0 # we encountered problems with Damerau-Levenshtein Similarity on some linux machines where the default character encoding of the operating system caused it to be negative, this should never be the case
                output.append(dls)
                output.append(1 - distance.jaccard(predicted, ground_truth))
                output.append(ground_truth_t)
                output.append(total_predicted_time)
                output.append('')
                output.append(metrics.mean_absolute_error([ground_truth_t], [total_predicted_time]))
                output.append(metrics.median_absolute_error([ground_truth_t], [total_predicted_time]))
                spamwriter.writerow(output)
print("TIME TO FINISH --- %s seconds ---" % (time.time() - start_time))