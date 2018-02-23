from tensorflow.python.platform import gfile
import tensorflow as tf
import os
import sys
import numpy as np
import rospkg

sys.path.append(os.path.join(rospkg.RosPack().get_path('deep_motion_planner'), "../deep_learning_model/src/model"))
import simple_model as model

class TensorflowWrapper():
    """
    The class is used to load a pretrained tensorflow model and
    use it on live sensor data
    """
    def __init__(self, storage_path, protobuf_file='graph.pb', use_checkpoints=False, filename_weights=None):
        """Initialize a new TensorflowWrapper object

        @param storage_path: The path to the protobuf_file and the snapshots
        @type  :  string

        @param protobuf_file: The protobuf file to load
        @type  :  string

        @param use_checkpoints: If the given protobuf_file does not contain the trained weights, you
                                    can use checkpoint files to initialize the weights
        @type  :  bool

        """

        if filename_weights == None:
          self.init_from_graph = True
          # Load the graph definition from a binary protobuf file
          with gfile.FastGFile(os.path.join(storage_path, protobuf_file),'rb') as f:
              graph_def = tf.GraphDef()
              graph_def.ParseFromString(f.read())
              tf.import_graph_def(graph_def, name='')

          print('Loaded protobuf file: {}'.format(os.path.join(storage_path, protobuf_file)))

          self.sess = tf.Session()

          # If the protobuf file does not contain the trained weights, you can load them from
          # a checkpoint file in the storage_path folder
          if use_checkpoints:
              # Get all checkpoints
              ckpt = tf.train.get_checkpoint_state(storage_path)
              if ckpt and ckpt.model_checkpoint_path:
                  # Open the model with the highest step count (the last snapshot)
                  print('Found checkpoints: \n{}'.format(ckpt))
                  print('Load: {}'.format(ckpt.model_checkpoint_path))
                  self.sess.run(['save/restore_all'], {'save/Const:0': os.path.join(storage_path,
                      ckpt.model_checkpoint_path)})
              else:
                  print('No checkpoint files in folder: {}'.format(storage_path))

        else:
          self.init_from_graph = False
          self.sess = tf.Session()
          self.input_data_placeholder = tf.placeholder(tf.float32, shape=[1, 38], name="input_data_placeholder")
          self.keep_prob_placeholder = tf.placeholder(tf.float32, name="keep_prob_placeholder")
          self.model_inference, _, _ = model.inference(self.input_data_placeholder, self.keep_prob_placeholder, 1,
                                                       training=False, reuse=True, output_name='model_inference',
                                                       filename_init=filename_weights)

          self.sess.run(tf.global_variables_initializer())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Make sure to close the session and clean up all the used resources
        self.sess.close()

    def inference(self, data):
        """
        Take the given data and perform the model inference on it
        """
        if self.init_from_graph:
          feed_dict = {'data_input:0': [data]}

          prediction = self.sess.run(['model_inference:0'], feed_dict=feed_dict)[0]

          return (prediction[0,0], prediction[0,1])
        else:
          feed_dict = {self.input_data_placeholder: [data],
                       self.keep_prob_placeholder: 1.0}
          prediction = self.sess.run(self.model_inference, feed_dict=feed_dict)[0]
          std = 0.1
          return (prediction[0] + np.random.normal(0, std), prediction[1] + + np.random.normal(0, std))




