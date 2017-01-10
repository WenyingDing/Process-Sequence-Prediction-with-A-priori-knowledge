'''
this script takes as input the output of evaluate_suffix_and_remaining_time.py
therefore, the latter needs to be executed first

Author: Niek Tax
'''

from __future__ import division
import unicodecsv

eventlog = "helpdesk.csv"
csvfile = open('output_files/results/suffix_and_remaining_time_%s' % eventlog, 'r')
r = unicodecsv.reader(csvfile ,encoding='utf-8')
r.next() # header
vals = dict()


damerau = 0
count = 0

for row in r:
    l = list()

    count += 1
    damerau += float(row[4])

    if row[0] in vals.keys():
        l = vals.get(row[0])
    if len(row[1])==0 and len(row[2])==0:
        l.append(1)
    elif len(row[1])==0 and len(row[2])>0:
        l.append(0)
    elif len(row[1])>0 and len(row[2])==0:
        l.append(0)
    else:
        l.append(int(row[1][0]==row[2][0]))
    vals[row[0]] = l
    #print(vals)
    
l2 = list()
for k in vals.keys():
    #print('{}: {}'.format(k, vals[k]))
    l2.extend(vals[k])
    res = sum(vals[k])/len(vals[k])
    print('{}: {}'.format(k, res))

print('total 1: {}'.format(sum(l2)/len(l2)))

print('damerau 1: {}'.format(damerau/count))

############################################################################################

csvfile = open('output_files/results/suffix_and_remaining_time2_%s' % eventlog, 'r')
r = unicodecsv.reader(csvfile, encoding='utf-8')
r.next()  # header
vals = dict()

damerau = 0
count = 0

for row in r:
    l = list()

    count += 1
    damerau += float(row[4])

    if row[0] in vals.keys():
        l = vals.get(row[0])
    if len(row[1]) == 0 and len(row[2]) == 0:
        l.append(1)
    elif len(row[1]) == 0 and len(row[2]) > 0:
        l.append(0)
    elif len(row[1]) > 0 and len(row[2]) == 0:
        l.append(0)
    else:
        l.append(int(row[1][0] == row[2][0]))
    vals[row[0]] = l
    # print(vals)

l2 = list()
for k in vals.keys():
    # print('{}: {}'.format(k, vals[k]))
    l2.extend(vals[k])
    res = sum(vals[k]) / len(vals[k])
    print('{}: {}'.format(k, res))

print('total 2: {}'.format(sum(l2) / len(l2)))

print('damerau 2: {}'.format(damerau / count))