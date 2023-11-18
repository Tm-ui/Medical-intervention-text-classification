# -*- coding: utf-8 -*-
"""Classify abstracts new.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Sap0Bx_L6jqz8NSv-5QXB42N3DtcZ3Lh

# Classify medical abstracts

Samuel Martey Okoe-Mensah, master's thesis 2023

# Choose workflow
"""

workflows = {0: {'dropstop': False, 'synonyms': False, 'parents': False, 'ngrams': False, 'nrfeats': 1000},
             1: {'dropstop': True, 'synonyms': False, 'parents': False, 'ngrams': False, 'nrfeats': 1000},
             2: {'dropstop': True, 'synonyms': True, 'parents': False, 'ngrams': False, 'nrfeats': 1000},
             3: {'dropstop': True, 'synonyms': True, 'parents': True, 'ngrams': False, 'nrfeats': 1000},
             4: {'dropstop': True, 'synonyms': False, 'parents': False, 'ngrams': 3, 'nrfeats': 1000},
             5: {'dropstop': True, 'synonyms': True, 'parents': False, 'ngrams': 3, 'nrfeats': 1000},
             6: {'dropstop': True, 'synonyms': True, 'parents': True, 'ngrams': 3, 'nrfeats': 1000},
             7: {'dropstop': False, 'synonyms': True, 'parents': True, 'ngrams': 3, 'nrfeats': 1000},
             8: {'dropstop': False, 'synonyms': False, 'parents': False, 'ngrams': 3, 'nrfeats': 1000},
             9: {'dropstop': False, 'synonyms': False, 'parents': False, 'ngrams': 3, 'nrfeats': 2000},
             10: {'dropstop': True, 'synonyms': True, 'parents': True, 'ngrams': 3, 'nrfeats': 2000}}

"""Choose only one of the following workflows before continuing."""

Workflow = 0

Workflow = 1

Workflow = 2

Workflow = 3

Workflow = 4

Workflow = 5

Workflow = 6

Workflow = 7

Workflow = 8

Workflow = 9

Workflow = 10

"""After choosing a workflow, continue here."""

print(Workflow)
print(workflows[Workflow])
workflow = str(Workflow)

"""# 0. Preliminaries

Needs to be done only once per session.

Connect to Google Drive where data is stored.
"""

from google.colab import drive
drive.mount('/content/drive/')

"""Decide where the files with result data will be placed. Make helper functions for writing text, figures and LaTeX tables to files in that folder, with appropriate settings."""

doc_path = 'drive/MyDrive/Colab Notebooks/Samuel/Doc/' # change to your folder

def write_text (data, file):
  with open(doc_path + file + workflow + '.tex', 'w') as out:
    print(data, file=out)

def write_fig (fig, file):
  fig.savefig(doc_path + file + workflow, dpi=150, bbox_inches='tight')

def write_table (styled_df, file, caption, label,
                 column_format=None, position='hbtp'):
  styled_df.format_index(escape="latex", axis=0)
  styled_df.format_index(escape="latex", axis=1)
  styled_df.to_latex(doc_path + file + workflow + '.tex', position=position,
                     caption=caption, label=label+workflow, column_format=column_format,
                     position_float='centering', hrules=True, convert_css=True)

"""Load modules and set random seeds for replicability of results."""

import numpy as np
import pandas as pd
import re
#from collections import Counter
import matplotlib.pyplot as plt
import tensorflow as tf
print(tf.__version__)
from tensorflow import math
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords')
eng_stopwords = stopwords.words('english')
#from nltk.util import ngrams
import json
import seaborn as sns

# if desired, set seeds for replicability of results
np.random.seed(41)
tf.random.set_seed(42)

"""# 1. Importing, checking and tokenizing the data.

Needs to be done only once per session.

Change the path if necessary.
"""

data_path = '/content/drive/My Drive/Colab Notebooks/Samuel/Data/'

"""Read the data file containing the annotated corpus"""

data = pd.read_csv(data_path + 'abstracts.tsv', sep='\t')
data

write_text(data, 'samples')

"""Show some labels and part of a text."""

data_labels = data['labels']
data_labels[:10]

data['texts'][0][:100]

"""Show distribution of labels."""

class_dist = pd.concat([data_labels.value_counts(),
                        data_labels.value_counts(normalize=True) * 100],
                       axis=1,
                       keys=('count', '%'))
class_dist

class_dist.reset_index(inplace=True)
class_dist.columns = ['label', 'count', '%']
class_dist_styled = class_dist.style.format(precision=1).hide(axis=0)
class_dist_styled

"""Write to file as LaTeX table."""

write_table(class_dist_styled, 'class-distribution',
            caption='Articles per class (1 = included, 0 = excluded).',
            label='tab:dist-articles', column_format='ccc')

"""# 2. Functions for feature enhancement: n-grams, stop words and NEO

Needs to be done only once per session.

## 2.1 N-grams

Define a simple function to compute n-grams from tokens. Use underscore in n-grams.
"""

def n_grams (seq, n=3):
  return ['_'.join(tpl) for tpl in zip(*[seq[i:] for i in range(n)])]

n_grams(['a','b','c','d','e'])

"""## 2.2 Ontology

Optionally, enrich text with terms from ontology. Load the NEO ontology dict from json.
"""

with open(data_path + 'neo.json') as infile:
  neodict = json.load(infile)

"""Try getting synonyms from NEO for a word."""

def try_synonyms(word, ontodict=neodict):
  val = ontodict.get(word)
  if val:
    return val.get('Synonyms')

"""Test."""

print(try_synonyms('ataxia'))
print(try_synonyms('dystaxia'))
print(try_synonyms('nonexistent'))

"""Try getting parents from NEO for a word."""

def try_parents(word, ontodict=neodict):
  val = ontodict.get(word)
  if val:
    return val.get('Parents')

"""Test."""

print(try_parents('ataxia'))
print(try_parents('dystaxia'))
print(try_parents('sign'))

"""Function to split multi-word terms unless n-grams are added."""

def split_terms(terms):
  if not workflows[Workflow]['ngrams']:
    # split multi-words into a flat list
    return {s for sublist in [t.split('_') for t in terms] for s in sublist}
  else:
    return set(terms)

split_terms(['cerebellar_signs', 'hypertonia', 'weight_gain', 'weight'])

"""Function to add synonyms from NEO."""

def all_synonyms(toks):
  new = set()
  for w in toks:
    synonyms = try_synonyms(w)
    if synonyms:
      synonyms = split_terms(synonyms)
      print('Adding synonyms ', synonyms, 'for', w)
      new = new | synonyms
  #if new:
    #print('Adding all synonyms ', new)
  return new

"""Test."""

print(all_synonyms(['ataxia', 'weakness_arm']))

"""Function to add parents from NEO."""

def all_parents(toks):
  new = set()
  for w in toks:
    parents = try_parents(w)
    if parents:
      parents = split_terms(parents)
      print('Adding parents ', parents, 'for', w)
      new = new | parents
  #if new:
    # print('Adding all parents', new)
  return new

print(all_parents(['ataxia', 'weakness_arm']))

"""Depending on workflow, add synonyms and/or parents."""

Neo = set()

def enrich_neo(tokenlist):
  global Neo
  if workflows[Workflow]['synonyms'] or workflows[Workflow]['parents']:
    tokenset = set(tokenlist)
    new = set()
    if workflows[Workflow]['synonyms']:
      new = new | all_synonyms(tokenset)
    if workflows[Workflow]['parents']:
      new = new | all_parents(tokenset)
    if new:
      new = new - tokenset
      print('Adding:', new)
      Neo = Neo | new
      tokenlist = list(tokenset | new)
  return tokenlist

print(enrich_neo(['The', 'patient', 'has', 'ataxia', 'agitated', 'agitation']))

print(Neo)
write_text(Neo, 'neo')

"""## 2.3 Stop words

Medical stop words.
"""

with open(data_path + 'med-stopwords.txt') as infile:
  med_stopwords = infile.read().splitlines()
print(len(med_stopwords), 'medical stop words read.')
print(med_stopwords[:12])

"""General English stop words."""

print(len(eng_stopwords), 'English stop words from NLTK.')
print(eng_stopwords[:12])

"""Union of medical stop words and NLTK stop words."""

allstopwords = set(med_stopwords).union(set(stopwords.words('english')))
len(allstopwords)

"""Function to remove stopwords in all texts."""

def remove_stopwords (toklist):
  return [tok for tok in toklist if tok not in allstopwords]

"""#3. Execute preprocessing according to workflows

Must be done for each workflow.

Make a simple tokenizer and tokenize all texts.
"""

def word_tokens (text):
  return re.findall(r'[\w-]+', text.casefold())

tokenized_texts = [word_tokens(t) for t in data['texts']]
print(tokenized_texts[0][:12])

"""## 3.1 Add n-grams, depending on workflow"""

N = workflows[Workflow]['ngrams']
if N:
  print(f'Adding {N}-grams')
  for txt in tokenized_texts:
    txt.extend(n_grams(txt, N))

print(tokenized_texts[0][:12])
print(tokenized_texts[0][-12:])

"""## 3.2 NEO enrichment, depending on workflow."""

Neo = set()
enriched_texts = [enrich_neo(t) for t in tokenized_texts]

"""Check some texts."""

for i in range(min([6, len(data_labels)])):
  print(data_labels[i], enriched_texts[i][:12])
  print(data_labels[i], enriched_texts[i][-12:])

"""These are all terms added by NEO to any of the texts."""

print(Neo)
write_text(', '.join(Neo), 'neo')

"""## 3.3 Remove stop words, depending on workflow."""

if workflows[Workflow]['dropstop']:
  print('Removing stop words')
  data_texts = [remove_stopwords(t) for t in enriched_texts]
else:
  print('Keeping stop words')
  data_texts = enriched_texts

"""Check some texts again."""

for i in range(min([6, len(data_labels)])):
  print(data_labels[i], data_texts[i][:12])
  print(data_labels[i], data_texts[i][-12:])

"""# 4. Preparing the input

Do for each workflow. Splitting and vectorizing the data.

## 4.1 Splitting the data

Split the dataset into training, development and test sets. First split into train part and rest (test and dev). Then split rest (test and dev) into dev part and test part. Keep the same proportion of classes in each set.
"""

from sklearn.model_selection import train_test_split

train_texts, testdev_texts, train_labels, testdev_labels = train_test_split(
  data_texts, data_labels,
  test_size = 0.4,
  random_state = 42,
  shuffle = True,
  stratify = data_labels)

dev_texts, test_texts, dev_labels, test_labels = train_test_split(
  testdev_texts, testdev_labels,
  test_size = 0.5,
  random_state = 42,
  shuffle = True,
  stratify = testdev_labels)

train_size = len(train_labels)
dev_size = len(dev_labels)
test_size = len(test_labels)

print(f'Training size: {train_size}')
print(f'Development size: {dev_size}')
print(f'Testing size: {test_size}')

train_labels

"""Show distribution of classes in training, development and test sets. This should be the same for all workflows."""

class_sizes = pd.concat([train_labels.value_counts(),
                         train_labels.value_counts(normalize=True) * 100,
                         dev_labels.value_counts(),
                         dev_labels.value_counts(normalize=True) * 100,
                         test_labels.value_counts(),
                         test_labels.value_counts(normalize=True) * 100],
                       axis=1,
                       keys=('train', 'train%', 'val', 'val%', 'test', 'test%'))
class_sizes

class_sizes.reset_index(inplace=True)
class_sizes.columns = ['label', 'train', '%', 'val', '%', 'test', '%']
class_sizes_styled = class_sizes.style.format(precision=1).hide(axis=0)
class_sizes_styled

"""Write to file as LaTeX table."""

write_table(class_sizes_styled, 'class-sizes',
            caption='Articles per class and set (1 = included, 0 = excluded).',
            label='tab:dist-sets')

"""## 4.2 Vectorizing the data

First tokenize with max vocabulary size.
"""

from tensorflow.keras.preprocessing import text, sequence
from tensorflow.keras import utils

nr_words = workflows[Workflow]['nrfeats']
write_text(nr_words, 'nrfeats')

# Create a tokenizer that takes the most common words (or n-grams)
tokenizer = text.Tokenizer(num_words=nr_words)

# Build the word index (dictionary)
tokenizer.fit_on_texts(train_texts) # Create word index using only training part

"""Vectorize with one-hot encoding."""

# Vectorize texts into one-hot encoding representations
x_train = tokenizer.texts_to_matrix(train_texts, mode='binary')
x_dev = tokenizer.texts_to_matrix(dev_texts, mode='binary')
x_test = tokenizer.texts_to_matrix(test_texts, mode='binary')

# Labels are already binary, turn list into array
y_train = np.array(train_labels)
y_dev = np.array(dev_labels)
y_test = np.array(test_labels)

print(f'Shape of the training set (data items, vector_size): {x_train.shape}\n')

"""# 5. Checking the vectorized data

Optional.
"""

print(f'Text of the first example:\n{train_texts[0]}\n')
print(f'Binary representation of the class: {y_train[0]}\n')
print(f'Vector of the first example:\n{x_train[0]}\n')

"""It is possible to obtain the lists of integers indices instead of the one-hot binary representation. This is a less sparse representation. Notice that the set may be smaller than the number of unique words because less frequent words are not used."""

# Turns strings into sets of integer indices
print(train_texts[0])
one_hot_results = tokenizer.texts_to_sequences(train_texts)
print(set(one_hot_results[0]))

"""The tokenizer has a word index and word counts. Find out how many words there are in word_index, which is a dict."""

print(f'Found {len(tokenizer.word_index)} unique tokens.')
write_text(len(tokenizer.word_index), 'nrtokens')

"""Find the index of a word."""

tokenizer.word_index.get('alzheimer')

"""The tokenizer also has a dict of word_counts. Find the frequency of a word."""

word_counts = tokenizer.word_counts
word_counts.get('alzheimer')

"""Sort the words by their counts. Show the top ones."""

sorted_words = (sorted(word_counts, key=word_counts.get, reverse=True))
sorted_words[:10]

"""Zip the words and their counts and convert to a dataframe, using the index as row names.
NB. 0 is a reserved index that is not assigned to any word, therefore the index starts at 1.
"""

freqzip = zip(sorted_words, [word_counts[w] for w in sorted_words])
freq_df = pd.DataFrame(freqzip, columns=['word', 'frequency'],
                       index=[tokenizer.word_index[w] for w in sorted_words])
freq_df

"""Check what we obtain when we vectorize words that are out of the index (_out of vocabulary_ words)."""

oov_sample = ['fløyen', 'ulriken']
sequences = tokenizer.texts_to_matrix(oov_sample)
print(sequences[0])

"""Check what we obtain when we vectorize words that are out of the index (_out of vocabulary_ words).

# 6. Running the modeling pipeline

Do for each workflow. Building, testing and tuning the model.

## 6.1 Building and training the model

Build a __logistic regression__ model (aka single-layer perceptron) using ```Dense``` layer. ```Dense``` implements the following  operation:

> ```output = activation(dot(input, kernel) + bias)```

where activation is the element-wise activation function passed as the ```activation``` argument (_sigmoid_ function in our case), ```kernel``` is a weights matrix created by the layer, and ```bias``` is a bias vector created by the layer.

We'll set ```(binary) cross-entropy``` as a __loss function__ and ```adam```, a variant of the _Stochastic Gradient Descent_, as the __optimizer__.
"""

from tensorflow.keras import Sequential
from tensorflow.keras.layers import Dense

input_size = x_train[0].shape[0] ## vector length equals to vocabulary size.
print(input_size)
num_classes = 2

model = Sequential()
model.add(Dense(units=1, activation='sigmoid', input_shape=(input_size,)))
# now the model will take as input arrays of shape (*, input_size)
# and output arrays of shape (*, 1)

# Compile the model using a loss function and an optimizer.
model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
model.summary()

"""Next piece of code trains the model defined above.

```model.fit()``` returns the history of the training, which contains the accuracies and loss values of training and development sets obtained in each of the epochs.
"""

history = model.fit(x_train, y_train, epochs=42, batch_size=5, validation_data=(x_dev, y_dev), verbose=2)

"""```model.fit()``` has returned the history of the training as a dict. Convert to a dataframe and plot."""

history_df = pd.DataFrame(history.history)
history_df.head()

history_plot = history_df.plot(xlabel='Epoch')

"""Save the figure in a file in your Drive folder."""

pic = history_plot.get_figure()
write_fig(pic, 'history')

"""## 6.2 Evaluating the model

Once we fit the model we can use the method ```model.evaluate()``` to obtain the accuracy on test set.
"""

score = model.evaluate(x_test, y_test, verbose=1)
write_text(f'{score[1]:.2f}', 'accuracy')

"""Get the predictions on the test set. Print a few of them."""

y_predict = (model.predict(x_test) > 0.5).astype("int32")
y_predict[:10]

"""Report metrics."""

from sklearn.metrics import classification_report
print(classification_report(y_test, y_predict))

"""Produce the classification report as dict, convert to dataframe, drop accuracy and apply style."""

report_dict = classification_report(y_test, y_predict, output_dict=True)
report_df = pd.DataFrame(report_dict).transpose()
report_df.drop('accuracy', inplace=True)
#report_df.drop(columns='support', inplace=True)
report_styled = report_df.style.format(precision=2).highlight_max()
report_styled

"""Now write the classification report to a latex table."""

write_table(report_styled, 'metrics',
  caption='Metrics for model '+workflow, label='tab:metrics', column_format='rrrrr')

"""Confusion matrix. Rows are actual classes, columns are classifications by the model."""

cm = math.confusion_matrix(labels=y_test, predictions=y_predict)
print(cm)

"""Display the confusion matrix as a heatmap."""

plt.figure(figsize = (6,5))
heatmap = sns.heatmap(cm, annot=True, annot_kws={"size": 15},
                cmap = 'YlGnBu', vmin=0, fmt='d') # integers
heatmap.set_xlabel('Predicted', fontsize=14)
heatmap.set_ylabel('Actual', fontsize=14)
write_fig(plt, 'cm-heatmap')
plt.show()

"""## 6.3 Model Tuning

Add L2 regularizer. Regularization is an estimator that reduces variance signiﬁcantly while not overly increasing the bias. L1 regularization tends to make some weights zero, while L2 regularization makes all weights somewhat smaller.
"""

import matplotlib.pyplot as plt
from tensorflow.keras import optimizers, regularizers

model2 = Sequential()

# add L2 weight regularization to logistic regression
regularizer = regularizers.l2(0.000002)
model2.add(Dense(units=1, activation='sigmoid', input_shape=(input_size,), kernel_regularizer=regularizer))

# Init optimizer
opt = optimizers.Adam()
model2.compile(loss='binary_crossentropy', optimizer=opt, metrics=['accuracy'])
history_reg = model2.fit(x_train, y_train, epochs=42, batch_size=32, validation_data=(x_dev, y_dev), verbose=0)

# summarize history for accuracy
plt.plot(history.history['accuracy'])
plt.plot(history.history['val_accuracy'])

plt.plot(history_reg.history['accuracy'])
plt.plot(history_reg.history['val_accuracy'])

plt.title('model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['train orig', 'dev orig', 'train reg', 'dev reg'], loc='lower right')
write_fig(plt, 'history-reg')
plt.show()

"""## 6.4 Evaluating the tuned model

Once we fit the model we can use the method ```model.evaluate()``` to obtain the accuracy on test set.
"""

score = model2.evaluate(x_test, y_test, verbose=1)
write_text(f'{score[1]:.2f}', 'accuracy-reg')

"""Get the predictions on the test set. Print a few of them."""

y_predict = (model2.predict(x_test) > 0.5).astype("int32")
y_predict[:10]

"""Report metrics."""

from sklearn.metrics import classification_report
print(classification_report(y_test, y_predict))

"""Produce the classification report as dict, convert to dataframe, drop accuracy and apply style."""

report_dict = classification_report(y_test, y_predict, output_dict=True)
report_df = pd.DataFrame(report_dict).transpose()
report_df.drop('accuracy', inplace=True)
#report_df.drop(columns='support', inplace=True)
report_styled = report_df.style.format(precision=2).highlight_max(color='LimeGreen')
report_styled

"""Now write the classification report to a latex table."""

write_table(report_styled, 'metrics-reg',
  caption='Metrics for model '+workflow+' with regularization',
  label='tab:metrics-reg', column_format='rrrrr')

"""Confusion matrix. Rows are actual classes, columns are classifications by the model."""

cm = math.confusion_matrix(labels=y_test, predictions=y_predict)
print(cm)

"""Display the confusion matrix as a heatmap."""

plt.figure(figsize = (6,5))
heatmap = sns.heatmap(cm, annot=True, annot_kws={"size": 15},
                cmap = 'YlGnBu', vmin=0, fmt='d') # integers
heatmap.set_xlabel('Predicted', fontsize=14)
heatmap.set_ylabel('Actual', fontsize=14)
write_fig(plt, 'cm-heatmap-reg')
plt.show()