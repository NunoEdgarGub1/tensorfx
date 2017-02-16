# Copyright 2016 TensorLab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.

# _model.py
# Implements the Model base class.

import os
import tensorflow as tf


class Model(object):
  """A model provides performs inferences using TensorFlow to produce predictions.

  A model is loaded from a checkpoint that was produced during training.
  """
  def __init__(self, session, signature):
    """Initializes a Model using a TensorFlow session containing an initialized prediction graph.

    Arguments:
      session: The TensorFlow session to use for evaluating inferences.
      signature: The signature defining the input and outputs for prediction.
    """
    self._session = session
    self._signature = signature

  @classmethod
  def load(cls, path):
    """Imports a previously exported saved model.

    Arguments:
      - path: The location on disk where the saved model exists.
    Returns:
      An initialized Model object that can be used for performing prediction.
    """
    with tf.Graph().as_default() as g:
      with tf.Session() as session:
        model = tf.saved_model.loader.load(session, ['SERVING'], path)
        signature = _parse_signature(model)

        local_init_op = tf.get_collection(tf.GraphKeys.LOCAL_INIT_OP)[0]
        session.run(local_init_op)

        return cls(session, signature)


  @staticmethod
  def save(session, path, inputs, outputs):
    """Exports the current session, the loaded graph, and variables into a saved model.

    Arguments:
      - session: the TensorFlow session with variables to save.
      - path: the location where the output model directory should be created.
      - inputs: the list of tensors constituting the input to the prediction graph.
      - outputs: the list of tensors constituting the outputs of the prediction graph.
    """
    signature_map = {'serving_default': _build_signature(inputs, outputs)}
    model_builder = tf.saved_model.builder.SavedModelBuilder(path)
    model_builder.add_meta_graph_and_variables(session,
                                              tags=['SERVING'],
                                              signature_def_map=signature_map,
                                              clear_devices=True)
    model_builder.save()

  def predict(self, instances):
    """Performs inference to return predictions for the specified instances of data.

    Arguments:
      - instances: either an object, or list of objects each containing feature values.
    """
    raise NotImplementedError()


def _build_signature(inputs, outputs):
  def tensor_alias(tensor):
    local_name = tensor.name.split('/')[-1]
    return local_name.split(':')[0]

  input_map = {}
  output_map = {}
  for tensor in inputs:
    input_map[tensor_alias(tensor)] = tf.saved_model.utils.build_tensor_info(tensor)
  for tensor in outputs:
    output_map[tensor_alias(tensor)] = tf.saved_model.utils.build_tensor_info(tensor)

  return tf.saved_model.signature_def_utils.build_signature_def(
    inputs=input_map,
    outputs=output_map,
    method_name=tf.saved_model.signature_constants.PREDICT_METHOD_NAME)


def _parse_signature(model):
  if not model.signature_def:
    raise ValueError('Invalid model. The saved model does not define a signature.')
  if len(model.signature_def) > 1:
    raise ValueError('Invalid model. Only models with a single signature are supported.')

  signature = model.signature_def.get('serving_default', None)
  if not signature:
    raise ValueError('Invalid model. Unexpected signature type.')

  if len(signature.inputs) != 1:
    raise ValueError('Invalid model. Only models with a single input are supported.')
  for alias in signature.inputs:
    if signature.inputs[alias].dtype != tf.string.as_datatype_enum:
      raise ValueError('Invalid model. Only models with a string input are supported.')
  if len(signature.outputs) == 0:
    raise ValueError('Invalid model. Only models with at least one output are supported.')

  return signature
