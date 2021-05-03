#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# --------------------------------------------------
# Description:
# --------------------------------------------------
# Author: Konfido <konfido.du@outlook.com>
# Created Date : April 4th 2020, 17:45:05
# Last Modified: April 4th 2020, 17:45:05
# --------------------------------------------------

from nltk.classify.maxent import MaxentClassifier
from sklearn.metrics import (accuracy_score, fbeta_score, precision_score,
                             recall_score)
import os
import pickle
import re
import nltk
from tqdm import tqdm
from nltk.tag.perceptron import PerceptronTagger
from names_dataset import NameDatasetV1


class MEMM:
    def __init__(self):
        self.train_path = "../data/train"
        self.dev_path = "../data/dev"
        self.beta = 0
        self.max_iter = 0
        self.classifier = None
        self.tagger = PerceptronTagger()
        self.m = NameDatasetV1()

    def features(self, sentence, labels, fs, ls):

        """ Baseline Features """
        length = len(sentence)
        poses = self.tagger.tag(sentence)
        for i in range(length):
            features = {}
            current_word = sentence[i]
            features['has_(%s)' % current_word] = 1
            if i == 0:
                features['prev_label'] = "O"
            else:
                features['prev_label'] = labels[i - 1]
            if bool(re.search('[A-Z]+[a-z]+$', current_word)):
                features['first_uppercase'] = 1

                pos = poses[i][1]
                if pos == 'NNP':
                    features['proper_noun'] = 1
                    if i == 0 or i == length:
                        features['first_last'] = 1
                    if sentence[i + 1] == "'s":
                        features['possession'] = 1

                if self.m.search_first_name(current_word) or self.m.search_last_name(current_word):
                    features['dataset'] = 1

            honorifics = ['Mr', 'Ms', 'Miss', 'Mrs', 'Mx', 'Master', 'Sir', 'Madam', 'Dame', 'Lord', 'Lady', 'Dr',
                          'Prof',
                          'Br', 'Sr', 'Fr', 'Rev', 'Pr', 'Elder']
            if i > 0:
                previous_word = sentence[i - 1].replace('.', '')
                if previous_word in honorifics:
                    features['honorific'] = 1

            fs.append(features)
            ls.append(labels[i])

        return True

    def load_data(self, filename):
        words = []
        labels = []
        for line in open(filename, "r", encoding="utf-8"):
            doublet = line.strip().split("\t")
            if len(doublet) < 2:  # remove emtpy lines
                continue
            words.append(doublet[0])
            labels.append(doublet[1])
        return words, labels

    def get_sentences(self, words, labels):
        sentences = []
        labels_list = []
        j = 0
        for i in range(len(words)):
            if words[i] == ".":
                sentence = []
                temp_labels = []
                for tmp in range(j, i + 1):
                    sentence.append(words[tmp])
                    temp_labels.append(labels[tmp])
                sentences.append(sentence)
                labels_list.append(temp_labels)
                j = i + 1
        return sentences, labels_list

    def train(self):
        print('Training classifier...')
        words, labels = self.load_data(self.train_path)
        sentences, labels_list = self.get_sentences(words, labels)

        features = []
        labels = []
        for i in tqdm(range(len(sentences))):
            self.features(sentences[i], labels_list[i], features, labels)

        train_samples = [(f, l) for (f, l) in zip(features, labels)]
        classifier = MaxentClassifier.train(
            train_samples, max_iter=self.max_iter)
        self.classifier = classifier

    def test(self):
        print('Testing classifier...')
        words, labels = self.load_data(self.dev_path)
        sentences, labels_list = self.get_sentences(words, labels)

        features = []
        labels = []
        for i in tqdm(range(len(sentences))):
            self.features(sentences[i], labels_list[i], features, labels)

        results = [self.classifier.classify(n) for n in features]

        f_score = fbeta_score(labels, results, average='macro', beta=self.beta)
        precision = precision_score(labels, results, average='macro')
        recall = recall_score(labels, results, average='macro')
        accuracy = accuracy_score(labels, results)

        print("%-15s %.4f\n%-15s %.4f\n%-15s %.4f\n%-15s %.4f\n" %
              ("f_score=", f_score, "accuracy=", accuracy, "recall=", recall,
               "precision=", precision))

        return True

    def show_samples(self, bound):
        """Show some sample probability distributions.
        """
        words, labels = self.load_data(self.dev_path)
        sentences, labels_list = self.get_sentences(words, labels)

        features = []
        labels = []
        for i in tqdm(range(len(sentences))):
            self.features(sentences[i], labels_list[i], features, labels)

        (m, n) = bound
        pdists = self.classifier.prob_classify_many(features[m:n])

        print('  Words          P(PERSON)  P(O)\n' + '-' * 40)
        for (word, label, pdist) in list(zip(words, labels, pdists))[m:n]:
            if label == 'PERSON':
                fmt = '  %-15s *%6.4f   %6.4f'
            else:
                fmt = '  %-15s  %6.4f  *%6.4f'
            print(fmt % (word, pdist.prob('PERSON'), pdist.prob('O')))

    def dump_model(self):
        with open('../model.pkl', 'wb') as f:
            pickle.dump(self.classifier, f)

    def load_model(self):
        with open('../model.pkl', 'rb') as f:
            self.classifier = pickle.load(f)


# mem = MEMM()
# mem.train()
# mem.load_model()
# mem.show_samples((0, 500))
