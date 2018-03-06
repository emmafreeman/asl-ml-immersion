#!/usr/bin/env python

# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tensorflow as tf
import tensorflow.contrib.metrics as metrics
import tensorflow.contrib.rnn as rnn

tf.logging.set_verbosity(tf.logging.INFO)

SEQ_LEN = 10
DEFAULTS = [[0.0] for x in xrange(0, SEQ_LEN)]
BATCH_SIZE = 20
TIMESERIES_COL = 'rawdata'
# In each sequence, column index 0 to N_INPUTS - 1 are features, and column index N_INPUTS to SEQ_LEN are labels
N_OUTPUTS = 1
N_INPUTS = SEQ_LEN - N_OUTPUTS

# Read data and convert to needed format
def read_dataset(filename, mode, batch_size = 512):
    def _input_fn():
        # Provide the ability to decode a CSV
        def decode_csv(line):
            # all_data is a list of scalar tensors
            all_data = tf.decode_csv(line, record_defaults = DEFAULTS)
            inputs = all_data[:len(all_data) - N_OUTPUTS]  # first N_INPUTS values
            labels = all_data[len(all_data) - N_OUTPUTS:] # last N_OUTPUTS values

            # Convert each list of rank R tensors to one rank R+1 tensor
            inputs = tf.stack(inputs, axis = 0)
            labels = tf.stack(labels, axis = 0)

            # Convert input R+1 tensor into a feature dictionary of one R+1 tensor
            features = {TIMESERIES_COL: inputs}

            return features, labels

        # Create list of files that match pattern
        file_list = tf.gfile.Glob(filename)

        # Create dataset from file list
        dataset = tf.data.TextLineDataset(file_list).map(decode_csv)

        if mode == tf.estimator.ModeKeys.TRAIN:
            num_epochs = None # indefinitely
            dataset = dataset.shuffle(buffer_size = 10 * batch_size)
        else:
            num_epochs = 1 # end-of-input after this

        dataset = dataset.repeat(num_epochs).batch(batch_size)

        iterator = dataset.make_one_shot_iterator()
        batch_features, batch_labels = iterator.get_next()
        return batch_features, batch_labels
    return _input_fn

LSTM_SIZE = 3  # number of hidden layers in each of the LSTM cells

# Create the inference model
def simple_rnn(features, labels, mode):
    # 0. Reformat input shape to become a sequence
    x = tf.split(features[TIMESERIES_COL], N_INPUTS, 1)

    # 1. Configure the RNN
    lstm_cell = rnn.BasicLSTMCell(LSTM_SIZE, forget_bias = 1.0)
    outputs, _ = rnn.static_rnn(lstm_cell, x, dtype = tf.float32)

    # Slice to keep only the last cell of the RNN
    outputs = outputs[-1]
    #print 'last outputs={}'.format(outputs)

    # Output is result of linear activation of last layer of RNN
    weight = tf.Variable(tf.random_normal([LSTM_SIZE, N_OUTPUTS]))
    bias = tf.Variable(tf.random_normal([N_OUTPUTS]))
    predictions = tf.matmul(outputs, weight) + bias
    
    # 2. Loss function, training/eval ops
    if mode == tf.estimator.ModeKeys.TRAIN or mode == tf.estimator.ModeKeys.EVAL:
        loss = tf.losses.mean_squared_error(labels, predictions)
        train_op = tf.contrib.layers.optimize_loss(
            loss = loss,
            global_step = tf.train.get_global_step(),
            learning_rate = 0.01,
            optimizer = "SGD")
        eval_metric_ops = {
            "rmse": tf.metrics.root_mean_squared_error(labels, predictions)
        }
    else:
        loss = None
        train_op = None
        eval_metric_ops = None
  
    # 3. TODO: Create predictions dict
  
    # 4. TODO: Create export outputs (use regression in this case)
  
    # 5. TODO: Return EstimatorSpec
  

# Create functions to read in respective datasets
def get_train():
    return read_dataset(filename = 'train.csv', mode = tf.estimator.ModeKeys.TRAIN, batch_size = 512)

def get_valid():
    return read_dataset(filename = 'valid.csv', mode = tf.estimator.ModeKeys.EVAL, batch_size = 512)

# Create serving input function
def serving_input_fn():
    feature_placeholders = {
        TIMESERIES_COL: tf.placeholder(tf.float32, [None, N_INPUTS])
    }

    features = {
        key: tf.expand_dims(tensor, -1)
        for key, tensor in feature_placeholders.items()
    }
    features[TIMESERIES_COL] = tf.squeeze(features[TIMESERIES_COL], axis = [2])

    return tf.estimator.export.ServingInputReceiver(features, feature_placeholders)

# Create custom estimator's train and evaluate function
def train_and_evaluate(output_dir):
    # TODO: Add estimator
    
    train_spec = tf.estimator.TrainSpec(input_fn = get_train(),
                                        max_steps = 1000)
    exporter = tf.estimator.LatestExporter('exporter', serving_input_fn)
    eval_spec = tf.estimator.EvalSpec(input_fn = get_valid(),
                                      steps = None, 
                                      exporters = exporter)
    tf.estimator.train_and_evaluate(estimator, train_spec, eval_spec)