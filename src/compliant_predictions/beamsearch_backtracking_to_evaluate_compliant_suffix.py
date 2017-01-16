'''
this file is build based on the code found in evaluate_suffix_and_remaining_time.py

here the beam search (with backtracking) is implemented, to find compliant prediction

Author: Anton Yeshchenko
'''

from __future__ import division

import csv
from datetime import timedelta
from itertools import izip

import distance
from jellyfish._jellyfish import damerau_levenshtein_distance
from keras.models import load_model
from sklearn import metrics

from src.compliant_predictions.tree_structure_beamsearch import MultileafTree
from src.formula_verificator import  verify_formula_as_compliant
from src.shared_variables import path_to_model_file, eventlog
from src.support_scripts.prepare_data import encode
from src.support_scripts.prepare_data import getSymbol
from src.support_scripts.prepare_data import prepare_testing_data



only_compliant = True
lines, lines_t, lines_t2, lines_t3, maxlen, chars, char_indices,divisor, divisor2, divisor3, predict_size,target_indices_char = prepare_testing_data(eventlog, only_compliant)

#this is the beam stack size, means how many "best" alternatives will be stored
beam_size = 3
one_ahead_gt = []
one_ahead_pred = []

# load model, set this to the model generated by train.py
model = load_model(path_to_model_file)

# make predictions
with open('../output_files/results/suffix_and_remaining_time1_%s' % eventlog, 'wb') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(["Prefix length", "Groud truth", "Predicted", "Levenshtein", "Damerau", "Jaccard", "Ground truth times", "Predicted times", "RMSE", "MAE", "Median AE"])
    for prefix_size in range(2,maxlen):
        print(prefix_size)
        for line, times, times2, times3 in izip(lines, lines_t, lines_t2, lines_t3):
            prediction_end_reached = False
            times.append(0)
            cropped_line = ''.join(line[:prefix_size])
            cropped_times = times[:prefix_size]
            cropped_times3 = times3[:prefix_size]
            if len(times2)<prefix_size:
                continue # make no prediction for this case, since this case has ended already

            # initialize root of the tree for beam search
            total_predicted_time_initialization = 0
            search_tree_root = MultileafTree(beam_size, encode(cropped_line, cropped_times, cropped_times3,maxlen,chars, char_indices, divisor, divisor2),
                                             cropped_line, total_predicted_time_initialization)

            prediction_end_reached = False


            ground_truth = ''.join(line[prefix_size:prefix_size+predict_size])
            ground_truth_t = times2[prefix_size-1]
            case_end_time = times2[len(times2)-1]
            ground_truth_t = case_end_time-ground_truth_t
            predicted = ''



            for i in range(predict_size):
                #here we will take data from the node in the tree used to prun
                enc = search_tree_root.data#encode(cropped_line, cropped_times, cropped_times3)
                y = model.predict(enc, verbose=0) # make predictions
                # split predictions into seperate activity and time predictions
                y_char = y[0][0]
                y_t = y[1][0][0]
                prediction = getSymbol(y_char,target_indices_char) # undo one-hot encoding
                #cropped_line += prediction
                if y_t<0:
                    y_t=0
                #TODO not normalizing here seems like a bug
                cropped_times.append(y_t)




                if prediction == '!': # end of case was just predicted, therefore, stop predicting further into the future
                    if verify_formula_as_compliant(search_tree_root.cropped_line) == True:
                        one_ahead_pred.append(search_tree_root.total_predicted_time)
                        one_ahead_gt.append(ground_truth_t)
                        print('! predicted, end case')
                        break
                    else:
                        prediction_end_reached = True;

                #if the end of prediction was not reached we continue as always, and then function :choose_next_top_descendant: will
                #search for future prediction

                #in not reached, function :choose_next_top_descendant: will backtrack
                y_t = y_t * divisor3
                if prediction_end_reached == False:
                    cropped_times3.append(cropped_times3[-1] + timedelta(seconds=y_t))

                    for i in range(beam_size):
                        temp_prediction = getSymbol(y_char, target_indices_char, i)
                        temp_cropped_line = search_tree_root.cropped_line + temp_prediction

                        temp_total_predicted_time = search_tree_root.total_predicted_time + y_t

                        temp_state_data = encode(temp_cropped_line, cropped_times, cropped_times3, maxlen, chars, char_indices, divisor, divisor2)
                        search_tree_root.descendants[i] = MultileafTree(beam_size, temp_state_data,
                                                                      temp_cropped_line, temp_total_predicted_time, search_tree_root)

                search_tree_root = search_tree_root.choose_next_top_descendant()
                if prediction_end_reached:
                    prediction_end_reached = False;
                if search_tree_root == None:
                    print "Cannot find any trace that is compliant with formula given current beam size";
                    break

            output = []

            if search_tree_root == None:
                predicted = u""
                total_predicted_time = 0
            else:
                predicted = (search_tree_root.cropped_line[prefix_size:])
                total_predicted_time = search_tree_root.total_predicted_time


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