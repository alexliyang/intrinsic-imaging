# Keras imports
from keras.models import Model, Sequential
from keras.layers import Dense, Dropout, Activation, Flatten
from keras.layers.convolutional import (Convolution2D, MaxPooling2D,
                                        ZeroPadding2D)

from keras.applications.vgg16 import VGG16
from models.vgg16Reg import VGG16Reg
from keras.applications.vgg19 import VGG19
from models.vgg19Reg import VGG19Reg
# Paper: https://arxiv.org/pdf/1409.1556.pdf

def build_vgg(img_shape=(3, 224, 224), n_classes=1000, n_layers=16, l2_reg=0.,
                load_pretrained=False, freeze_layers_from='base_model'):
    # Decide if load pretrained weights from imagenet
    if load_pretrained:
        weights = 'imagenet'
    else:
        weights = None

    # Get base model
    if n_layers==16:
        if l2_reg == 0.:
            base_model = VGG16(include_top=False, weights=weights,
                           input_tensor=None, input_shape=img_shape)
        else:
            print "VGG16reg_l2_model" 
            base_model = VGG16Reg(include_top=False, weights=weights,
                           input_tensor=None, input_shape=img_shape, l2_reg=l2_reg)  
        
    elif n_layers==19:
        if l2_reg == 0.:
            base_model = VGG19(include_top=False, weights=weights,
                           input_tensor=None, input_shape=img_shape)
        else:
            print "VGG19reg_l2_model"
            base_model = VGG19Reg(include_top=False, weights=weights,
                           input_tensor=None, input_shape=img_shape, l2_reg=l2_reg)  
    else:
        raise ValueError('Number of layers should be 16 or 19')

    # Add final layers
    x = base_model.output
    x = Flatten(name="flatten")(x)
    x = Dense(4096, activation='relu', name='dense_1')(x)
    x = Dropout(0.5)(x)
    x = Dense(4096, activation='relu', name='dense_2')(x)
    x = Dropout(0.5)(x)
    x = Dense(n_classes, name='dense_3_{}'.format(n_classes))(x)
    predictions = Activation("softmax", name="softmax")(x)

    # This is the model we will train
    model = Model(input=base_model.input, output=predictions)

    # Freeze some layers
    if freeze_layers_from is not None:
        if freeze_layers_from == 'base_model':
            print ('   Freezing base model layers')
            for layer in base_model.layers:
                layer.trainable = False
        else:
            for i, layer in enumerate(model.layers):
                print(i, layer.name)
            print ('   Freezing from layer 0 to ' + str(freeze_layers_from))
            for layer in model.layers[:freeze_layers_from]:
               layer.trainable = False
            for layer in model.layers[freeze_layers_from:]:
               layer.trainable = True

    return model