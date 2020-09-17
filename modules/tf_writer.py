from google.cloud import storage
import os
import tensorflow as tf

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "../data/keys/tpu-training-289520-f7727af0669b.json"

storage_client = storage.Client()

def _floatlist_feature(value):
    return tf.train.Feature(float_list=tf.train.FloatList(value=value))

def _float_feature(value):
    return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))

def _bytes_feature(value):
    """Returns a bytes_list from a string / byte."""
    if isinstance(value, type(tf.constant(0))):
        value = value.numpy() # BytesList won't unpack a string from an EagerTensor.
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

def _string_bytes_feature(value):
    """Returns a bytes_list from a string / byte."""
    if isinstance(value, type(tf.constant(0))):
        value = value.numpy() # BytesList won't unpack a string from an EagerTensor.
    if isinstance(value, type(str)):
        value = value.encode('utf-8')
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

def _int64_feature(value):
    """Returns an int64_list from a bool / enum / int / uint."""
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def serialize_example(dataset):
    """
    Takes a json encoded Dataset with the structure:
    {'feature_name' :
        {'data':[dataset], 
        'type':'name of corresponding tf message type'}
        }
        
    Creates a tf.train.Example message ready to be written to a file.
    """

    feature_type_dict = {
        'floats' : _floatlist_feature,
        'float' : _float_feature,
        'bytes' : _bytes_feature,
        'string' : _string_bytes_feature,
        'int' : _int64_feature
    }
    
    feature = {key: feature_type_dict[dataset[key]['type']](dataset[key]['data']) for key in dataset.keys()}

    example_proto = tf.train.Example(features=tf.train.Features(feature=feature))
    return example_proto.SerializeToString()

def write_tfrecord(dataset, filename, bucket_path='gs://fin-aml/data/'):
    destination = bucket_path + filename
    
    num_records = dataset[dataset.keys()[0]]['data'].shape[0]
    
    with tf.io.TFRecordWriter(destination) as writer:
        for i in range(num_records):
            example = serialize_example(dataset)
            writer.write(example)