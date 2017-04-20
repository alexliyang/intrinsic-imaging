import numpy as np
from keras import backend as K
from keras.models import Model
from keras.layers import Input
from keras.layers import Convolution2D
from keras.layers import UpSampling2D
from keras.layers import MaxPooling2D
from keras.layers import LeakyReLU
from keras.layers import merge
from keras.layers import Reshape
from layers.yolo_layers import YOLOConvolution2D,Reorg, concat
from layers.deconv import Deconvolution2D

import tensorflow as tf

def build_yolo(img_shape=(3, 416, 416), n_classes=80, n_priors=5,
               load_pretrained=False,freeze_layers_from='base_model',
               typeNet='Regular', lookTwice = False):

    # YOLO model is only implemented for TF backend
    assert(K.backend() == 'tensorflow')

    model = []

    # Get base model
    if typeNet == 'Regular':
      model = YOLO(input_shape=img_shape, num_classes=n_classes, num_priors=n_priors)
      base_model_layers = [layer.name for layer in model.layers[0:42]]
      tiny = False
    elif typeNet == 'Tiny':
      if lookTwice:
        model = TinyYOLT(input_shape=img_shape, num_classes=n_classes, num_priors=n_priors)
        load_pretrained = False
      else:
        model = TinyYOLO(input_shape=img_shape, num_classes=n_classes, num_priors=n_priors)
      base_model_layers = [layer.name for layer in model.layers[0:21]]
      tiny = True
    elif typeNet == 'YOLT':
      model = TinyYOLT(input_shape=img_shape, num_classes=n_classes, num_priors=n_priors)
      base_model_layers = [layer.name for layer in model.layers[0:21]]
      load_pretrained = False
      
    if load_pretrained:
      # Rename last layer to not load pretrained weights
      model.layers[-1].name += '_new'
      if not tiny:
        model.load_weights('weights/yolo.hdf5',by_name=True)
      else:
        model.load_weights('weights/tiny-yolo.hdf5',by_name=True)

    # Freeze some layers
    if freeze_layers_from is not None:
        if freeze_layers_from == 'base_model':
            for layer in model.layers:
                if layer.name in base_model_layers:
                    layer.trainable = False
        else:
            print ('   Freezing from layer 0 to ' + str(freeze_layers_from))
            for layer in model.layers[:freeze_layers_from]:
               layer.trainable = False
            for layer in model.layers[freeze_layers_from:]:
               layer.trainable = True

    return model

def YOLO(input_shape=(3,416,416),num_classes=80,num_priors=5):
    """YOLO (v2) architecture

    # Arguments
        input_shape: Shape of the input image
        num_classes: Number of classes (excluding background)

    # References
        https://arxiv.org/abs/1612.08242
        https://arxiv.org/abs/1506.02640
    """
    K.set_image_dim_ordering('th')

    net={}
    input_tensor = Input(shape=input_shape)
    net['input'] = input_tensor
    net['conv1'] = (YOLOConvolution2D(32, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['input'])
    net['relu1'] = (LeakyReLU(alpha=0.1))(net['conv1'])
    net['pool1'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu1'])
    net['conv2'] = (YOLOConvolution2D(64, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool1'])
    net['relu2'] = (LeakyReLU(alpha=0.1))(net['conv2'])
    net['pool2'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu2'])
    net['conv3_1'] = (YOLOConvolution2D(128, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool2'])
    net['relu3_1'] = (LeakyReLU(alpha=0.1))(net['conv3_1'])
    net['conv3_2'] = (YOLOConvolution2D(64, 1, 1, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu3_1'])
    net['relu3_2'] = (LeakyReLU(alpha=0.1))(net['conv3_2'])
    net['conv3_3'] = (YOLOConvolution2D(128, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu3_2'])
    net['relu3_3'] = (LeakyReLU(alpha=0.1))(net['conv3_3'])
    net['pool3'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu3_3'])
    net['conv4_1'] = (YOLOConvolution2D(256, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool3'])
    net['relu4_1'] = (LeakyReLU(alpha=0.1))(net['conv4_1'])
    net['conv4_2'] = (YOLOConvolution2D(128, 1, 1, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu4_1'])
    net['relu4_2'] = (LeakyReLU(alpha=0.1))(net['conv4_2'])
    net['conv4_3'] = (YOLOConvolution2D(256, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu4_2'])
    net['relu4_3'] = (LeakyReLU(alpha=0.1))(net['conv4_3'])
    net['pool4'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu4_3'])
    net['conv5_1'] = (YOLOConvolution2D(512, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool4'])
    net['relu5_1'] = (LeakyReLU(alpha=0.1))(net['conv5_1'])
    net['conv5_2'] = (YOLOConvolution2D(256, 1, 1, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu5_1'])
    net['relu5_2'] = (LeakyReLU(alpha=0.1))(net['conv5_2'])
    net['conv5_3'] = (YOLOConvolution2D(512, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu5_2'])
    net['relu5_3'] = (LeakyReLU(alpha=0.1))(net['conv5_3'])
    net['conv5_4'] = (YOLOConvolution2D(256, 1, 1, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu5_3'])
    net['relu5_4'] = (LeakyReLU(alpha=0.1))(net['conv5_4'])
    net['conv5_5'] = (YOLOConvolution2D(512, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu5_4'])
    net['relu5_5'] = (LeakyReLU(alpha=0.1))(net['conv5_5'])
    net['pool5'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu5_5'])
    net['conv6_1'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool5'])
    net['relu6_1'] = (LeakyReLU(alpha=0.1))(net['conv6_1'])
    net['conv6_2'] = (YOLOConvolution2D(512, 1, 1, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu6_1'])
    net['relu6_2'] = (LeakyReLU(alpha=0.1))(net['conv6_2'])
    net['conv6_3'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu6_2'])
    net['relu6_3'] = (LeakyReLU(alpha=0.1))(net['conv6_3'])
    net['conv6_4'] = (YOLOConvolution2D(512, 1, 1, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu6_3'])
    net['relu6_4'] = (LeakyReLU(alpha=0.1))(net['conv6_4'])
    net['conv6_5'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu6_4'])
    net['relu6_5'] = (LeakyReLU(alpha=0.1))(net['conv6_5'])
    net['conv6_6'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu6_5'])
    net['relu6_6'] = (LeakyReLU(alpha=0.1))(net['conv6_6'])
    net['conv6_7'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu6_6'])
    net['relu6_7'] = (LeakyReLU(alpha=0.1))(net['conv6_7'])
    net['reorg7'] = (Reorg())(net['relu5_5'])
    net['merge7'] = (merge([net['reorg7'], net['relu6_7']], mode='concat', concat_axis=1))
    net['conv8'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['merge7'])
    net['relu8'] = (LeakyReLU(alpha=0.1))(net['conv8'])
    net['conv9'] = (Convolution2D(num_priors*(4+num_classes+1), 1, 1, border_mode='same',
                                              subsample=(1,1)))(net['relu8'])

    model = Model(net['input'], net['conv9'])
    return model

def TinyYOLO(input_shape=(3,416,416),num_classes=80,num_priors=5):
    """Tiny YOLO (v2) architecture

    # Arguments
        input_shape: Shape of the input image
        num_classes: Number of classes (excluding background)

    # References
        https://arxiv.org/abs/1612.08242
        https://arxiv.org/abs/1506.02640
    """
    K.set_image_dim_ordering('th')

    net={}
    input_tensor = Input(shape=input_shape)
    net['input'] = input_tensor
    net['conv1'] = (YOLOConvolution2D(16, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['input'])
    net['relu1'] = (LeakyReLU(alpha=0.1))(net['conv1'])
    net['pool1'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu1'])
    net['conv2'] = (YOLOConvolution2D(32, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool1'])
    net['relu2'] = (LeakyReLU(alpha=0.1))(net['conv2'])
    net['pool2'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu2'])
    net['conv3'] = (YOLOConvolution2D(64, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool2'])
    net['relu3'] = (LeakyReLU(alpha=0.1))(net['conv3'])
    net['pool3'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu3'])
    net['conv4'] = (YOLOConvolution2D(128, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool3'])
    net['relu4'] = (LeakyReLU(alpha=0.1))(net['conv4'])
    net['pool4'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu4'])
    net['conv5'] = (YOLOConvolution2D(256, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool4'])
    net['relu5'] = (LeakyReLU(alpha=0.1))(net['conv5'])
    net['pool5'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu5'])
    net['conv6'] = (YOLOConvolution2D(512, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool5'])
    net['relu6'] = (LeakyReLU(alpha=0.1))(net['conv6'])
    net['pool6'] = (MaxPooling2D(pool_size=(2, 2),strides=(1,1),border_mode='same'))(net['relu6'])
    net['conv7'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool6'])
    net['relu7'] = (LeakyReLU(alpha=0.1))(net['conv7'])
    net['conv8'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu7'])
    net['relu8'] = (LeakyReLU(alpha=0.1))(net['conv8'])
    net['conv9'] = (Convolution2D(num_priors*(4+num_classes+1), 1, 1, border_mode='same',
                                              subsample=(1,1)))(net['relu8'])

    model = Model(net['input'], net['conv9'])
    return model



def TinyYOLO_Siamese(input_shape=(3,416,416),num_classes=80,num_priors=5):
    """Tiny YOLO (v2) architecture

    # Arguments
        input_shape: Shape of the input image
        num_classes: Number of classes (excluding background)

    # References
        https://arxiv.org/abs/1612.08242
        https://arxiv.org/abs/1506.02640
    """
    K.set_image_dim_ordering('th')

    input_tensor_1 = Input(shape=input_shape)
    input_tensor_2 = Input(shape=input_shape)
    net_1 = {}
    net_2 = {}
    net_1 = create_base_network(input_tensor_1, net_1)
    net_2 = create_base_network(input_tensor_2, net_2, True)

    merge_nets = (concat())([net_1['relu7'], net_2['relu7']])
    conv = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(merge_nets)                            
    ReLU = (LeakyReLU(alpha=0.1))(conv)
    outNet = (Convolution2D(num_priors*(4+num_classes+1), 1, 1, border_mode='same',
                                              subsample=(1,1)))(ReLU)
    model = Model([net_1['input'], net_2['input']], outNet)
    return model


def create_base_network(input_dim, net, doubleScaling = False):
    
    net['input'] = input_dim
    
    if doubleScaling:

      output_shape_tensor = getShapeLayer(net['input'])
      
      net['deconv'] = (YOLODeconvolution2D(3, 3, 3, batch_size = 16, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['input'])
                              
      net['conv1'] = (YOLOConvolution2D(16, 3, 3, border_mode='same',subsample=(1,1),
                                        epsilon=0.000001))(net['deconv'])
      net['input1'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['conv1'])                                      
                                      
    else:
      net['input1'] = (YOLOConvolution2D(16, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['input'])                                            
                                  
    net['relu1'] = (LeakyReLU(alpha=0.1))(net['input1'])
    net['pool1'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu1'])
    net['conv2'] = (YOLOConvolution2D(32, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool1'])
                                      
    net['relu2'] = (LeakyReLU(alpha=0.1))(net['conv2'])
    net['pool2'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu2'])
    net['conv3'] = (YOLOConvolution2D(64, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool2'])
    net['relu3'] = (LeakyReLU(alpha=0.1))(net['conv3'])
    net['pool3'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu3'])
    net['conv4'] = (YOLOConvolution2D(128, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool3'])
    net['relu4'] = (LeakyReLU(alpha=0.1))(net['conv4'])
    net['pool4'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu4'])
    net['conv5'] = (YOLOConvolution2D(256, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool4'])
    net['relu5'] = (LeakyReLU(alpha=0.1))(net['conv5'])
    net['pool5'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu5'])
    net['conv6'] = (YOLOConvolution2D(512, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool5'])
    net['relu6'] = (LeakyReLU(alpha=0.1))(net['conv6'])
    net['pool6'] = (MaxPooling2D(pool_size=(2, 2),strides=(1,1),border_mode='same'))(net['relu6'])
    net['conv7'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool6'])
    net['relu7'] = (LeakyReLU(alpha=0.1))(net['conv7'])
    
    return net
    
    
        
def TinyYOLT(input_shape=(3,416,416),num_classes=80,num_priors=5):
    """Tiny TinyYOLT architecture

    # Arguments
        input_shape: Shape of the input image
        num_classes: Number of classes (excluding background)

    # References
        https://arxiv.org/abs/1612.08242
        https://arxiv.org/abs/1506.02640
    """
    K.set_image_dim_ordering('th')

    
    input_tensor = Input(shape=input_shape)
    net = {}
    net['input'] = input_tensor
    
    # Scale 1                              
    net['input_scale1'] = (YOLOConvolution2D(16, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['input'])    
                                      
    # Scale 2 
    net['deconv'] = Deconvolution2D(3, 4, 4, net['input']._keras_shape, 'glorot_uniform',
                                    'linear', border_mode='valid', subsample=(2, 2),
                                    name='deconv')(net['input'])  
    net['deconv'] = UpSampling2D(size=(2, 2))((net['input']))
       
    net['conv1'] = (YOLOConvolution2D(16, 3, 3, border_mode='same',subsample=(1,1),
                                        epsilon=0.000001))(net['deconv'])
                                        
    net['input_scale2'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['conv1'])                                      
    
    # Merge scales    
    # net['merge'] = (concat())([net['input_scale1'], net['input_scale2']])
    net['merge'] = merge([net['input_scale1'], net['input_scale2']], mode = 'concat', name='merge', concat_axis=1)
    
    net['relu1'] = (LeakyReLU(alpha=0.1))(net['merge'])
    net['pool1'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu1'])
    net['conv2'] = (YOLOConvolution2D(32, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool1'])
                                      
    net['relu2'] = (LeakyReLU(alpha=0.1))(net['conv2'])
    net['pool2'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu2'])
    net['conv3'] = (YOLOConvolution2D(64, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool2'])
    net['relu3'] = (LeakyReLU(alpha=0.1))(net['conv3'])
    net['pool3'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu3'])
    net['conv4'] = (YOLOConvolution2D(128, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool3'])
    net['relu4'] = (LeakyReLU(alpha=0.1))(net['conv4'])
    net['pool4'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu4'])
    net['conv5'] = (YOLOConvolution2D(256, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool4'])
    net['relu5'] = (LeakyReLU(alpha=0.1))(net['conv5'])
    net['pool5'] = (MaxPooling2D(pool_size=(2, 2),border_mode='valid'))(net['relu5'])
    net['conv6'] = (YOLOConvolution2D(512, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool5'])
    net['relu6'] = (LeakyReLU(alpha=0.1))(net['conv6'])
    net['pool6'] = (MaxPooling2D(pool_size=(2, 2),strides=(1,1),border_mode='same'))(net['relu6'])
    net['conv7'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['pool6'])
    net['relu7'] = (LeakyReLU(alpha=0.1))(net['conv7'])    
    net['conv8'] = (YOLOConvolution2D(1024, 3, 3, border_mode='same',subsample=(1,1),
                                      epsilon=0.000001))(net['relu7'])                            
    net['relu8'] = (LeakyReLU(alpha=0.1))(net['conv8'])
    net['output'] = (Convolution2D(num_priors*(4+num_classes+1), 1, 1, border_mode='same',
                                              subsample=(1,1)))(net['relu8'])
    model = Model(net['input'], net['output'])
    return model
    
def getShapeLayer(layer):
  input_shape = layer.get_shape().as_list()

  rows = input_shape[2]
  cols = input_shape[3]

  rows = 2*rows
  cols = 2*cols

  outputShape = (input_shape[0], 3, rows, cols)
  return outputShape