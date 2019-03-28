import copy

import numpy as np
from benchmarks.pendigit.loadUniPenData import loadUnipenData
from benchmarks.pendigit.normalize import normalize_example
from benchmarks.pendigit.plotting import plotUniPenData

from hmmlearn.hmm import MultinomialHMM
#from algorithms.hmm.hmm_scaled import HMM_Scaled as HiddenMarkovModel
from algorithms.hmm._hmm_base import  HiddenMarkovModel
from algorithms.hmm.distributions import ProbabilityMassFunction
import math
import joblib

MODEL_NAME="mnHmm_%s.joblib"

class DatasetPendigits():
    def __init__(self, train_path, test_path):
        # the number of classes that should the directions should be
        # divided into
        self._resolution = 8
        # todo doesn't work for 30 training steps why!!!
        self._training_steps_per_digit = 20

        self._train_label_path = train_path
        self._train_labels = None
        self._train_data = None

        self._test_label_path = test_path
        self._test_labels = None
        self._test_data = None

        self._model_dict = {}

    def load_files(self):
        train_data, train_labels = loadUnipenData(self._train_label_path)
        self._train_labels = train_labels

        #tdata is data without penUp and penDown
        train_data, tdata = normalize_example(train_data)
        self._train_data = train_data

        # load testdata
        test_data, test_labels = loadUnipenData(self._test_label_path)
        self._test_labels = test_labels

        #tdata is data without penUp and penDown
        test_data, ptest_data = normalize_example(test_data)
        self._test_data = test_data

    def get_models(self):
        return self._model_dict

    def init_models(self):
        for i in range(0, 10):
            #print('--'*10)
            # params=ste means transitions emissions and start probabiilitys are updated during training
            # initially emissions are generated at random

            # get emission labels

            # todo try out other count of states
            state_count = self._resolution + 2
            em_count = self._resolution + 2
            init_dist = HiddenMarkovModel.gen_eq_pi(state_count)
            # generate equal sized start probabilitys
            em_mat = HiddenMarkovModel.gen_rand_emissions(state_count, em_count)
            # generate equal sized transition probabilitys
            trans_mat = HiddenMarkovModel.gen_rand_transitions(state_count)
            em_dist = ProbabilityMassFunction
            #print(state_list)
            observation_alphabet = []
            for j in range(0, em_count):
                observation_alphabet.append(j)

            state_list = []
            for j in range(0, state_count):
                state_list.append(j)

            model = HiddenMarkovModel(
                latent_variables=state_list,
                observations=observation_alphabet,
                em_dist=em_dist,
                initial_dist=init_dist)

            model.set_transition_matrix(trans_mat)
            model.set_emission_matrix(em_mat)

            self._model_dict[i] = model

    def init_models_hmmlearn(self):
        # generate
        for i in range(10):
            #print('--'*10)
            # params=ste means transitions emissions and start probabiilitys are updated during training
            # initially emissions are generated at random
            # components is for the 10 classes of directions
            n_classes = self._resolution + 2
            model = MultinomialHMM(n_components=n_classes,
                                   n_iter=20,
                                   tol=100,
                                   verbose=True,
                                   params='ste',
                                   init_params='e')
            init = 1. / (n_classes + 0.0)

            # generate equal sized start probabilitys
            model.startprob_ = np.full(n_classes, init)
            # generate equal sized transition probabilitys
            model.transmat_ = np.full((n_classes, n_classes), init)
            self._model_dict[i] = model

    def train_models_hmmlearn(self):
        for i in range(10):
            enc_data, lengths = self._create_train_seq(i)
            self._model_dict[i].fit(enc_data, lengths)
            break

    def save_models(self):
        # save models
        for key, model in self._model_dict.items():
            joblib.dump(model, MODEL_NAME%(key))

    def train_models(self):
        # train 10 models for each digit one
        for i in range(0, 10):
            print('-'*100)
            print('training model nr %s for digit %s '%(i,i))
            enc_data, lengths = self._create_train_seq(i)
            print("\ntraining %s digits for number %s"%(len(lengths), i) )
            print("total length of sequence %s observations"%(sum(lengths)))
            #print(enc_data)
            #print(lengths)
            idx = 0
            curr_hmm = self._model_dict[i]
            digits_skipped = 0
            for j in range(0, len(lengths)):

                new_idx = idx + lengths[j]
                seq = enc_data[idx:new_idx]
                #print('--'*10)
                #print(j)
                #print(idx)
                #print(new_idx)
                #print(seq)
                tmp_hmm = copy.deepcopy(curr_hmm)
                try:
                    curr_hmm.train(seq, steps=self._training_steps_per_digit)
                except:
                    digits_skipped += 1
                    print('sequence to long => model crashes')
                    # rollback changes
                    curr_hmm = tmp_hmm
                idx = new_idx
                #print('~'*100)
                #print('hmm info:')
                #print(type(curr_hmm))
                #print(curr_hmm)
                # todo debug only learn one digit
                if j == 0:
                    break
            print('~'*100)
            print(len(lengths))
            print(digits_skipped)
            print(curr_hmm)

    def _create_train_seq(self, number):
        """
        extracts a number and appends
        :param number:
        :return:
        """
        # create array of positions of number in self._train_labels
        # [14 ,... ] means that the first "number" is at indici 14
        ind = np.where(np.array(self._train_labels) == number)
        digit_data = np.array(self._train_data)[ind]
        enc_data, lengths = self._encode_direction(digit_data)
        return enc_data, lengths

    def _create_test_seq(self, index):
        """
        computes one direction sequence for a given number
        :param index:
            index of the number in train_sequence to return
        :return:
            one sequence of the number
        """
        digit_data = np.array([self._test_data[index],])
        enc_data, lengths = self._encode_direction(digit_data)
        return enc_data, lengths


    def load_models(self):
        for key in range(0,10):
            self._model_dict[key] = joblib.load(MODEL_NAME%(key))

    def plot_example(self, number):
        data, tdata = normalize_example(self._train_data)
        plotUniPenData(data[number])

    def _points_to_direction(self, c, x1, y1, x2, y2):
        """
        :param c:
            number of classes
            integer
        :param x1: x-coordinate of previous point
        :param y1: y-coordinate of previous point
        :param x2: x-coordinate of current point
        :param y2: y-coordinate of current point
        :return: the class direction d \in [0, ..., c]
        """
        dx = x2 - x1
        dy = y2 - y1
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        # maps the angle to the intervall [0,...,c]
        scaled_angle = angle*(c/360)
        # modulo c because if the scaled angel nearer to c
        # than to c-1 the class should be 0
        direction = round(scaled_angle)%c
        return direction


    def _encode_direction(self, raw_data):
        """
        :param raw_data:
        :return:
            enc_data:
                contains all sequences in a single sequence
            lenghts:
                list [..., i, ...] i is length of the sequences
        """
        C = 8
        enc_data = []
        lengths = []
        for example in raw_data:
            sq = []
            for point in example:
                x = point[0]
                y = point[1]
                # the observation that the pen is set on the tablet
                if x == -1 and y == 1:
                    #sq.append([C])
                    sq.append(C)
                    xp = float('inf')
                # the observation that the pen is removed from tablet
                elif x == -1 and y == -1:
                    #sq.append([C+1])
                    sq.append(C+1)
                    xp = float('inf')
                else:
                    if xp != float('inf'):
                        #dx = xp - x
                        #dy = yp - y
                        #direction = (int(math.ceil(math.atan2(dy, dx) / (2 * math.pi / 8))) + 8) % 8
                        direction = self._points_to_direction(C, xp, yp, x, y)
                        #sq.append([direction])
                        sq.append(direction)
                    xp = x
                    yp = y
                #print(sq)
            enc_data.extend(sq)
            lengths.append(len(sq))
        return enc_data, lengths

    def _encode_direction_ex(self, example):
        sq = []
        for point in example:
            x = point[0]
            y = point[1]
            if x == -1 and y == 1:
                sq.append([8])
                xp = float('inf')
            elif x == -1 and y == -1:
                sq.append([9])
                xp = float('inf')
            else:
                if xp != float('inf'):
                    dx = xp - x
                    dy = yp - y
                    direction = (int(math.ceil(math.atan2(dy, dx) / (2 * math.pi / 8))) + 8) % 8
                    sq.append([direction])
                xp = x
                yp = y
        return sq


    def benchmark(self, length=None):
        # for the test sequence stores the predicted number
        # by determening which hmm scored most on number
        predicted_labels = []
        numbers = 10
        test_seq_length = len(self._test_labels)
        if length is not None:
            test_seq_length = length
        else:
            test_seq_length = 10

        # for every number
        for i in range(test_seq_length):
            # stores prob_x of each hmm number on the number
            llks = np.zeros(numbers)

            # get test data for one number
            # lengths should be 0
            seq, lengths = self._create_test_seq(i)


            # let each model score on the number
            for j in range(numbers):
                try:
                    llks[j] = self._model_dict[j].forward_backward(seq)
                except ValueError:
                    break

            # get highest average probX of all different hmms for the
            # type of number i
            # save number/index of hmm that scored the most
            predicted_labels.append(np.argmax(llks))

        y_true = self._test_labels[test_seq_length:]
        y_pred = predicted_labels
        # calculate accuracy
        return y_true, y_pred

    def benchmark_hmmlearn(self):
        plabels = []
        for j in range(len(self._test_data)):
            llks = np.zeros(10)
            enc_data = np.atleast_2d(self._encode_direction_ex(self._test_data[j]))
            for i in range(10):
                llks[i] = self._model_dict[i].score(enc_data)
            plabels.append(np.argmax(llks))
        print(float(np.sum(np.array(plabels) == np.array(self._test_labels))) / len(plabels))