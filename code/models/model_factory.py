import os

# Keras imports
from metrics.metrics import cce_flatt, IoU, YOLOLoss, YOLOMetrics, SSDLoss, SSDMetrics
from keras import backend as K
from keras.utils.visualize_util import plot

# Classification models
#from models.lenet import build_lenet
#from models.alexNet import build_alexNet
from models.vgg import build_vgg
from models.resnet50 import build_resnet50
from models.resnet import ResnetBuilder
from models.inceptionV3 import build_inceptionV3
from models.densenet import build_densenet
from models.SSD import Build_SSD

# Detection models
from models.yolo import build_yolo

# Segmentation models
from models.fcn8 import build_fcn8
from models.unet import build_unet
from models.segnet import build_segnet
from models.resnetFCN import build_resnetFCN
from models.densenet_fc import DenseNetFCN

# Adversarial models
#from models.adversarial_semseg import Adversarial_Semseg

from models.model import One_Net_Model


# Build the model
class Model_Factory():
    def __init__(self):
        pass

    # Define the input size, loss and metrics
    def basic_model_properties(self, cf, variable_input_size):
        # Define the input size, loss and metrics
        if cf.dataset.class_mode == 'categorical':
            if K.image_dim_ordering() == 'th':
                in_shape = (cf.dataset.n_channels,
                            cf.target_size_train[0],
                            cf.target_size_train[1])
            else:
                in_shape = (cf.target_size_train[0],
                            cf.target_size_train[1],
                            cf.dataset.n_channels)
            loss = 'categorical_crossentropy'
            metrics = ['accuracy']
        elif cf.dataset.class_mode == 'detection':
            if cf.model_name == 'tiny-yolo' or cf.model_name == 'yolo' or cf.model_name == 'yolt':
                in_shape = (cf.dataset.n_channels,
                            cf.target_size_train[0],
                            cf.target_size_train[1])
                loss = YOLOLoss(in_shape, cf.dataset.n_classes, cf.dataset.priors)
                metrics = [YOLOMetrics(in_shape, cf.dataset.n_classes, cf.dataset.priors)]
            elif cf.model_name == 'ssd':
                in_shape = (cf.target_size_train[0],
                            cf.target_size_train[1],
                            cf.dataset.n_channels,)
                loss = SSDLoss(in_shape, cf.dataset.n_classes, cf.dataset.priors)
                #metrics = [YOLOMetrics(in_shape, cf.dataset.n_classes, cf.dataset.priors)]
                metrics = [SSDMetrics()]
        elif cf.dataset.class_mode == 'segmentation':
            if K.image_dim_ordering() == 'th':
                if variable_input_size:
                    in_shape = (cf.dataset.n_channels, None, None)
                else:
                    in_shape = (cf.dataset.n_channels,
                                cf.target_size_train[0],
                                cf.target_size_train[1])
            else:
                if variable_input_size:
                    in_shape = (None, None, cf.dataset.n_channels)
                else:
                    in_shape = (cf.target_size_train[0],
                                cf.target_size_train[1],
                                cf.dataset.n_channels)
            loss = cce_flatt(cf.dataset.void_class, cf.dataset.cb_weights)
            metrics = [IoU(cf.dataset.n_classes, cf.dataset.void_class)]
        else:
            raise ValueError('Unknown problem type')
        return in_shape, loss, metrics

    # Creates a Model object (not a Keras model)
    def make(self, cf, optimizer=None):
        if cf.model_name in ['lenet', 'alexNet', 'vgg16', 'vgg19', 'resnet50', 'densenet_fc',
                             'InceptionV3', 'fcn8', 'unet', 'segnet', 'segnet_vgg',
                             'segnet_basic', 'resnetFCN', 'yolo', 'resnet50Keras', 'ssd',
                             'resnet18','resnet34','resnet50','resnet101','resnet152', 'densenet','tiny-yolo', 'yolt']:
            if optimizer is None:
                raise ValueError('optimizer can not be None')

            in_shape, loss, metrics = self.basic_model_properties(cf, True)
            model = self.make_one_net_model(cf, in_shape, loss, metrics, optimizer)

        elif cf.model_name == 'adversarial_semseg':
            if optimizer is None:
                raise ValueError('optimizer is not None')

            # loss, metrics and optimizer are made in class Adversarial_Semseg
            in_shape, _, _ = self.basic_model_properties(cf, False)
            model = Adversarial_Semseg(cf, in_shape)

        else:
            raise ValueError('Unknown model name')

        # Output the model
        return model

    # Creates, compiles, plots and prints a Keras model. Optionally also loads its
    # weights.
    def make_one_net_model(self, cf, in_shape, loss, metrics, optimizer):
        # Create the *Keras* model
        model_name = cf.model_name 
        if cf.model_name == 'fcn8':
            model = build_fcn8(in_shape, cf.dataset.n_classes, cf.weight_decay,
                               freeze_layers_from=cf.freeze_layers_from,
                               path_weights=cf.load_imageNet)
        elif cf.model_name == 'unet':
            model = build_unet(in_shape, cf.dataset.n_classes, cf.weight_decay,
                               freeze_layers_from=cf.freeze_layers_from,
                               path_weights=None)
        elif cf.model_name == 'segnet_basic':
            model = build_segnet(in_shape, cf.dataset.n_classes, cf.weight_decay,
                                 freeze_layers_from=cf.freeze_layers_from,
                                 path_weights=None, basic=True)
        elif cf.model_name == 'segnet_vgg':
            model = build_segnet(in_shape, cf.dataset.n_classes, cf.weight_decay,
                                 freeze_layers_from=cf.freeze_layers_from,
                                 path_weights=None, basic=False)
        elif cf.model_name == 'resnetFCN':
            model = build_resnetFCN(in_shape, cf.dataset.n_classes, cf.weight_decay,
                                    freeze_layers_from=cf.freeze_layers_from,
                                    path_weights=None)
        elif cf.model_name == 'densenetFCN':
            model = build_densenetFCN(in_shape, cf.dataset.n_classes, cf.weight_decay,
                                      freeze_layers_from=cf.freeze_layers_from,
                                      path_weights=None)
        elif cf.model_name == 'densenet_fc':
            model = DenseNetFCN((224, 224, 3), nb_dense_block=5, growth_rate=16,
                                nb_layers_per_block=4, upsampling_type='upsampling', 
                                classes=cf.dataset.n_classes)
        elif cf.model_name == 'lenet':
            model = build_lenet(in_shape, cf.dataset.n_classes, cf.weight_decay)
        elif cf.model_name == 'alexNet':
            model = build_alexNet(in_shape, cf.dataset.n_classes, cf.weight_decay)
        elif cf.model_name == 'vgg16':
            model = build_vgg(in_shape, cf.dataset.n_classes, 16, cf.weight_decay,
                              load_pretrained=cf.load_imageNet,
                              freeze_layers_from=cf.freeze_layers_from)
        elif cf.model_name == 'vgg19':
            model = build_vgg(in_shape, cf.dataset.n_classes, 19, cf.weight_decay,
                              load_pretrained=cf.load_imageNet,
                              freeze_layers_from=cf.freeze_layers_from)
        elif cf.model_name == 'resnet50Keras':
            model = build_resnet50(in_shape, cf.dataset.n_classes, cf.weight_decay,
                                   load_pretrained=cf.load_imageNet,
                                   freeze_layers_from=cf.freeze_layers_from)
        elif cf.model_name == 'resnet18':
            model = ResnetBuilder.build_resnet_18(in_shape, cf.dataset.n_classes)
        elif cf.model_name == 'resnet34':
            model = ResnetBuilder.build_resnet_34(in_shape, cf.dataset.n_classes)
        elif cf.model_name == 'resnet50':
            model = ResnetBuilder.build_resnet_50(in_shape, cf.dataset.n_classes)
        elif cf.model_name == 'resnet101':
            model = ResnetBuilder.build_resnet_101(in_shape, cf.dataset.n_classes)
        elif cf.model_name == 'resnet152':
            model = ResnetBuilder.build_resnet_152(in_shape, cf.dataset.n_classes)                                                                                   
        elif cf.model_name == 'InceptionV3':
            model = build_inceptionV3(in_shape, cf.dataset.n_classes,
                                      cf.weight_decay,
                                      load_pretrained=cf.load_imageNet,
                                      freeze_layers_from=cf.freeze_layers_from)
        elif cf.model_name == 'densenet':
            model = build_densenet(in_shape, cf.dataset.n_classes, cf.weight_decay)

            
        elif cf.model_name == 'yolo':
            model = build_yolo(in_shape, cf.dataset.n_classes,
                               cf.dataset.n_priors,
                               load_pretrained=cf.load_imageNet,
                               freeze_layers_from=cf.freeze_layers_from, typeNet='Regular')
        elif cf.model_name == 'tiny-yolo':
            if hasattr(cf, 'lookTwice'):
              yolt = cf.lookTwice
              if yolt:
                model_name = 'Tiny-YOLT'
            else:
              yolt = False
            model = build_yolo(in_shape, cf.dataset.n_classes,
                               cf.dataset.n_priors,
                               load_pretrained=cf.load_imageNet,
                               freeze_layers_from=cf.freeze_layers_from, typeNet='Tiny', lookTwice = yolt)
        elif cf.model_name == 'yolt':
            model = build_yolo(in_shape, cf.dataset.n_classes,
                               cf.dataset.n_priors,
                               load_pretrained=cf.load_imageNet,
                               freeze_layers_from=cf.freeze_layers_from, typeNet='YOLT')
        elif cf.model_name == 'ssd':
            model = Build_SSD(in_shape, cf.dataset.n_classes+1,
                              load_pretrained=cf.load_imageNet,
                              freeze_layers_from=cf.freeze_layers_from)

        else:
            raise ValueError('Unknown model')

        # Load pretrained weights
        if cf.load_pretrained:
            print('   loading model weights from: ' + cf.weights_file )
            model.load_weights(cf.weights_file, by_name=True)
        else:
      			try:
      				  if cf.load_transferlearning:
          				  print('   loading model weights from: ' + cf.weights_file )
          				  old_name=model.layers[-2].name
          				  model.layers[-2].name=model.layers[-2].name+'_replaced'
          				  model.load_weights(cf.weights_file, by_name=True)
          				  model.layers[-2].name=old_name
      			except:
      				  pass	
        # Compile model
        model.compile(loss=loss, metrics=metrics, optimizer=optimizer)

        # Show model structure
        if cf.show_model:
            model.summary()
            plot(model, to_file=os.path.join(cf.savepath, 'model.png'))

        # Output the model
        print ('   Model: ' + model_name)
        # model is a keras model, Model is a class wrapper so that we can have
        # other models (like GANs) made of a pair of keras models, with their
        # own ways to train, test and predict
        return One_Net_Model(model, cf, optimizer)