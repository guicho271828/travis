import keras.initializers
import keras.backend as K
from keras.layers import *
import numpy as np
import tensorflow as tf
debug = False
# debug = True

def Print(msg=None):
    def printer(x):
        if msg:
            print(x,":",msg)
        else:
            print(x)
        return x
    return Lambda(printer)

def list_layer_io(net):
    from keras.models import Model
    print(net)
    if isinstance(net, list):
        for subnet in net:
            list_layer_io(subnet)
    elif isinstance(net, Model):
        net.summary()
    elif isinstance(net, Layer):
        print("  <-")
        for i in range(len(net._inbound_nodes)):
            print(net._get_node_attribute_at_index(i, 'input_tensors', 'input'))
        print("  ->")
        for i in range(len(net._inbound_nodes)):
            print(net._get_node_attribute_at_index(i, 'output_tensors', 'output'))
        # print(net.input)
    else:
        print("nothing can be displayed")

def Sequential (array):
    from functools import reduce
    def apply1(arg,f):
        if debug:
            print("applying {}({})".format(f,arg))
        result = f(arg)
        if debug:
            print(K.int_shape(result), K.shape(result))
        return result
    return lambda x: reduce(apply1, array, x)

def ConditionalSequential (array, condition, **kwargs):
    from functools import reduce
    def apply1(arg,f):
        if debug:
            print("applying {}({})".format(f,arg))
        concat = Concatenate(**kwargs)([condition, arg])
        return f(concat)
    return lambda x: reduce(apply1, array, x)

def Residual (layer):
    def res(x):
        return x+layer(x)
    return Lambda(res)

def ResUnit (*layers):
    return Residual(
        Sequential(layers))

def wrap(x,y,**kwargs):
    "wrap arbitrary operation"
    return Lambda(lambda x:y,**kwargs)(x)


def Densify(layers):
    "Apply layers in a densenet-like manner."
    def densify_fn(x):
        def rec(x,layers):
            layer, *rest = layers

            result = layer(x)
            if len(rest) == 0:
                return result
            else:
                return rec(concatenate([x,result]), rest)
        return rec(x,layers)
    return densify_fn

def flatten(x):
    if K.ndim(x) >= 3:
        try:
            # it sometimes fails to infer shapes
            return Reshape((int(np.prod(K.int_shape(x)[1:])),))(x)
        except:
            return Flatten()(x)
    else:
        return x
def flatten1D(x):
    def fn(x):
        if K.ndim(x) == 3:
            return x
        elif K.ndim(x) > 3:
            s = K.shape(x)
            return K.reshape(x, [K.shape(x)[0],int(np.prod(K.int_shape(x)[1:-1])),K.int_shape(x)[-1]])
        else:
            raise Exception(f"unsupported shape {K.shape(x)}")
    return Lambda(fn)(x)
def flatten2D(x):
    def fn(x):
        if K.ndim(x) == 4:
            return x
        elif K.ndim(x) > 4:
            return K.reshape(x, [K.shape(x)[0],int(np.prod(K.int_shape(x)[1:-2])),K.int_shape(x)[-2],K.int_shape(x)[-1]])
        else:
            raise Exception(f"unsupported shape {K.shape(x)}")
    return Lambda(fn)(x)


def set_trainable (model, flag):
    from collections.abc import Iterable
    if isinstance(model, Iterable):
        for l in model:
            set_trainable(l, flag)
    elif hasattr(model, "layers"):
        set_trainable(model.layers,flag)
    else:
        model.trainable = flag

def sort_binary(x):
    x = x.round().astype(np.uint64)
    steps = np.arange(start=x.shape[-1]-1, stop=-1, step=-1, dtype=np.uint64)
    two_exp = (2 << steps)//2
    x_int = np.sort(np.dot(x, two_exp))
    # print(x_int)
    xs=[]
    for i in range(((x.shape[-1]-1)//8)+1):
        xs.append(x_int % (2**8))
        x_int = x_int // (2**8)
    xs.reverse()
    # print(xs)
    tmp = np.stack(xs,axis=-1)
    # print(tmp)
    tmp = np.unpackbits(tmp.astype(np.uint8),-1)
    # print(tmp)
    return tmp[...,-x.shape[-1]:]

# tests
# sort_binary(np.array([[[1,0,0,0],[0,1,0,0],],[[0,1,0,0],[1,0,0,0]]]))
# sort_binary(np.array([[[1,0,0,0,0,0,0,0,0],[0,1,0,0,0,0,0,0,0],],
#                       [[0,1,0,0,0,0,0,0,0],[1,0,0,0,0,0,0,0,0]]]))

def count_params(model):
    from keras.utils.layer_utils import count_params
    model._check_trainable_weights_consistency()
    if hasattr(model, '_collected_trainable_weights'):
        trainable_count = count_params(model._collected_trainable_weights)
    else:
        trainable_count = count_params(model.trainable_weights)
    return trainable_count

from keras.callbacks import Callback

class HistoryBasedEarlyStopping(Callback):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_train_begin(self, logs=None):
        # Allow instances to be re-used
        self.wait = 0
        self.stopped_epoch = 0

    def on_train_end(self, logs=None):
        if self.stopped_epoch > 0 and self.verbose > 0:
            print(f'\nEpoch {self.stopped_epoch}: early stopping {type(self)}')
            print('history:',self.history)

class GradientEarlyStopping(HistoryBasedEarlyStopping):
    def __init__(self, monitor='val_loss',
                 min_grad=-0.0001, sample_epochs=20, verbose=0, smooth=3):
        super().__init__()
        self.monitor = monitor
        self.verbose = verbose
        self.min_grad = min_grad
        self.history = []
        self.sample_epochs = sample_epochs
        self.stopped_epoch = 0
        assert sample_epochs >= 2
        if sample_epochs > smooth*2:
            self.smooth = smooth
        else:
            print("sample_epochs is too small for smoothing!")
            self.smooth = sample_epochs//2

    def gradient(self):
        h = np.array(self.history)
        
        # e.g. when smooth = 3, take the first/last 3 elements, average them over 3,
        # take the difference, then divide them by the epoch(== length of the history)
        return (h[-self.smooth:] - h[:self.smooth]).mean()/self.sample_epochs
        
    def on_epoch_end(self, epoch, logs=None):
        import warnings
        current = logs.get(self.monitor)
        if current is None:
            warnings.warn('Early stopping requires %s available!' %
                          (self.monitor), RuntimeWarning)

        self.history.append(current) # to the last
        if len(self.history) > self.sample_epochs:
            self.history.pop(0) # from the front
            if self.gradient() >= self.min_grad:
                self.model.stop_training = True
                self.stopped_epoch = epoch

class ChangeEarlyStopping(HistoryBasedEarlyStopping):
    "Stops when the training gets stabilized: when the change of the past epochs are below a certain threshold"
    def __init__(self, monitor='val_loss',
                 threshold=0.00001, epoch_start=0, sample_epochs=20, verbose=0):
        super().__init__()
        self.monitor = monitor
        self.verbose = verbose
        self.threshold = threshold
        self.history = []
        self.epoch_start = epoch_start
        self.sample_epochs = sample_epochs
        self.stopped_epoch = 0

    def change(self):
        return (np.amax(self.history)-np.amin(self.history))

    def on_epoch_end(self, epoch, logs=None):
        import warnings
        current = logs.get(self.monitor)
        if current is None:
            warnings.warn('Early stopping requires %s available!' %
                          (self.monitor), RuntimeWarning)

        self.history.append(current) # to the last
        if len(self.history) > self.sample_epochs:
            self.history.pop(0) # from the front
            if (self.change() <= self.threshold) and (self.epoch_start <= epoch) :
                self.model.stop_training = True
                self.stopped_epoch = epoch

class LinearEarlyStopping(HistoryBasedEarlyStopping):
    "Stops when the value goes above the linearly decreasing upper bound"
    def __init__(self,
                 epoch_end,
                 epoch_start=0,
                 monitor='val_loss',
                 ub_ratio_start=1.0, ub_ratio_end=0.0, # note: relative to the loss at epoch 0
                 target_value=None,
                 sample_epochs=20, verbose=0):
        super().__init__()
        self.monitor = monitor
        self.verbose = verbose
        self.history = []
        self.epoch_end     = epoch_end
        self.epoch_start   = epoch_start
        self.ub_ratio_end     = ub_ratio_end
        self.ub_ratio_start   = ub_ratio_start
        self.sample_epochs = sample_epochs
        self.stopped_epoch = 0
        self.value_start = float("inf")
        if target_value is not None:
            self.value_end = target_value
        else:
            self.value_end = 0.0

    def on_epoch_end(self, epoch, logs=None):
        import warnings
        current = logs.get(self.monitor)
        if current is None:
            warnings.warn('Early stopping requires %s available!' %
                          (self.monitor), RuntimeWarning)

        if epoch == self.epoch_start:
            self.value_start = current

        progress_ratio = (epoch - self.epoch_start) / (self.epoch_end - self.epoch_start)
        ub_ratio = self.ub_ratio_start + (self.ub_ratio_end - self.ub_ratio_start) * progress_ratio
        ub = (self.value_start - self.value_end) * ub_ratio + self.value_end

        self.history.append(current) # to the last
        if len(self.history) > self.sample_epochs:
            self.history.pop(0) # from the front
            if (np.median(self.history) >= ub) and (self.epoch_start <= epoch) :
                self.model.stop_training = True
                self.stopped_epoch = epoch

class ExplosionEarlyStopping(HistoryBasedEarlyStopping):
    "Stops when the value goes above the upper bound, which is set to a very large value (1e8 by default)"
    def __init__(self,
                 epoch_end,
                 epoch_start=0,
                 monitor='val_loss',
                 sample_epochs=20, verbose=0):
        super().__init__()
        self.monitor       = monitor
        self.verbose       = verbose
        self.history       = []
        self.epoch_end     = epoch_end
        self.epoch_start   = epoch_start
        self.sample_epochs = sample_epochs
        self.stopped_epoch = 0

    def on_epoch_end(self, epoch, logs=None):
        import warnings
        current = logs.get(self.monitor)
        if current is None:
            warnings.warn('Early stopping requires %s available!' %
                          (self.monitor), RuntimeWarning)
        if epoch == 0:
            self.ub = current * 10
        if np.isnan(current) :
            self.model.stop_training = True
            self.stopped_epoch = epoch
            return
        self.history.append(current) # to the last
        if len(self.history) > self.sample_epochs:
            self.history.pop(0) # from the front
            if (np.median(self.history) >= self.ub) and (self.epoch_start <= epoch) :
                self.model.stop_training = True
                self.stopped_epoch = epoch

def anneal_rate(epoch,min=0.1,max=5.0):
    import math
    return math.log(max/min) / epoch

take_true_counter = 0
def take_true(name="take_true"):
    global take_true_counter
    take_true_counter += 1
    return Lambda(lambda x: x[:,:,0], name="{}_{}".format(name,take_true_counter))

# sign function with straight-through estimator
sign_counter = 0
def sign(name="sign"):
    global sign_counter
    sign_counter += 1
    import tensorflow as tf
    def fn(x):
        g = tf.get_default_graph()
        with g.gradient_override_map({"Sign": "Identity"}):
            return tf.sign(x)
    return Lambda(fn,name="{}_{}".format(name,sign_counter))

# heavyside step function with straight-through estimator
heavyside_counter = 0
def heavyside(name="heavyside"):
    global heavyside_counter
    heavyside_counter += 1
    import tensorflow as tf
    def fn(x):
        g = tf.get_default_graph()
        with g.gradient_override_map({"Sign": "Identity"}):
            return (tf.sign(x)+1)/2
    return Lambda(fn,name="{}_{}".format(name,heavyside_counter))

# argmax function with straight-through estimator
argmax_counter = 0
def argmax(name="argmax"):
    global argmax_counter
    argmax_counter += 1
    import tensorflow as tf
    def fn(x):
        g = tf.get_default_graph()
        with g.gradient_override_map({"Sign": "Identity"}):
            return (tf.sign(x-K.max(x,axis=-1,keepdims=True)+1e-20)+1)/2
    return Lambda(fn,name="{}_{}".format(name,argmax_counter))

# sigmoid that becomes a step function in the test time
rounded_sigmoid_counter = 0
def rounded_sigmoid(name="rounded_sigmoid"):
    global rounded_sigmoid_counter
    rounded_sigmoid_counter += 1
    return Lambda(lambda x: K.in_train_phase(K.sigmoid(x), K.round(K.sigmoid(x))),
                  name="{}_{}".format(name,rounded_sigmoid_counter))

# softmax that becomes an argmax function in the test time
rounded_softmax_counter = 0
def rounded_softmax(name="rounded_softmax"):
    global rounded_softmax_counter
    rounded_softmax_counter += 1
    return Lambda(lambda x: K.in_train_phase(K.softmax(x), K.one_hot(K.argmax( x ), K.int_shape(x)[-1])),
                  name="{}_{}".format(name,rounded_softmax_counter))

# is a maximum during the test time
def smooth_max(*args):
    return K.in_train_phase(K.logsumexp(K.stack(args,axis=0), axis=0)-K.log(2.0), K.maximum(*args))

# is a minimum during the test time
def smooth_min(*args):
    return K.in_train_phase(-K.logsumexp(-K.stack(args,axis=0), axis=0)+K.log(2.0), K.minimum(*args))

stclip_counter = 0
def stclip(min_value,high_value,name="stclip"):
    "clip with straight-through gradient"
    global stclip_counter
    stclip_counter += 1
    import tensorflow as tf
    def fn(x):
        x_clip = K.clip(x, min_value, high_value)
        return K.stop_gradient(x_clip - x) + x
    return Lambda(fn,name="{}_{}".format(name,stclip_counter))


def delay(self, x, amount):
    switch = K.variable(0)
    def fn(epoch,log):
        if epoch > amount:
            K.set_value(switch, 1)
        else:
            K.set_value(switch, 0)
    self.callbacks.append(LambdaCallback(on_epoch_end=fn))
    return switch * x

def dmerge(x1, x2):
    return concatenate([wrap(x1, x1[:,None,...]),wrap(x2, x2[:,None,...])],axis=1)

def dapply(x,fn):
    x1 = wrap(x,x[:,0,...])
    x2 = wrap(x,x[:,1,...])
    y1 = fn(x1)
    y2 = fn(x2)
    y = dmerge(y1, y2)
    return y, y1, y2

class Gaussian:
    count = 0

    def __init__(self, beta=0.):
        self.beta = beta
        
    def call(self, mean_log_var):
        sym_shape = K.shape(mean_log_var)
        shape = K.int_shape(mean_log_var)
        dims = [sym_shape[i] for i in range(len(shape)-1)]
        dim = shape[-1]//2
        mean    = mean_log_var[...,:dim]
        log_var = mean_log_var[...,dim:]
        noise = K.exp(0.5 * log_var) * K.random_normal(shape=(*dims, dim))
        return K.in_train_phase(mean + noise, mean)
    
    def __call__(self, mean_log_var):
        Gaussian.count += 1
        c = Gaussian.count-1

        layer = Lambda(self.call,name="gaussian_{}".format(c))

        sym_shape = K.shape(mean_log_var)
        shape = K.int_shape(mean_log_var)
        dims = [sym_shape[i] for i in range(len(shape)-1)]
        dim = shape[-1]//2
        mean    = mean_log_var[...,:dim]
        log_var = mean_log_var[...,dim:]

        loss = -0.5 * K.mean(K.sum(1 + log_var - K.square(mean) - K.exp(log_var), axis=-1)) * self.beta

        layer.add_loss(K.in_train_phase(loss, 0.0), mean_log_var)
        
        return layer(mean_log_var)

class Uniform:
    count = 0

    def __init__(self, beta=0.):
        self.beta = beta

    def call(self, mean_width):
        sym_shape = K.shape(mean_width)
        shape = K.int_shape(mean_width)
        dims = [sym_shape[i] for i in range(len(shape)-1)]
        dim = shape[-1]//2
        mean = mean_width[...,:dim]
        width = mean_width[...,dim:]
        noise = width * K.random_uniform(shape=(*dims, dim),minval=-0.5, maxval=0.5)
        return K.in_train_phase(mean + noise, mean)

    def __call__(self, mean_width):
        Uniform.count += 1
        c = Uniform.count-1

        layer = Lambda(self.call,name="uniform_{}".format(c))

        sym_shape = K.shape(mean_width)
        shape = K.int_shape(mean_width)
        dims = [sym_shape[i] for i in range(len(shape)-1)]
        dim = shape[-1]//2
        mean = mean_width[...,:dim]
        width = mean_width[...,dim:]

        # KL
        high = mean + width/2
        low  = mean - width/2
        high = K.clip(high, 0.0, 1.0)
        low  = K.clip(low,  0.0, 1.0)
        intersection = high-low
        loss = K.mean(intersection) * self.beta
        # but this does not seem informative --- if it has no overlap with [0,1], it is always 0
        # Total Variation / Earth Mover would seem much better choice
        layer.add_loss(K.in_train_phase(loss, 0.0))
        return layer(mean_width)

class ScheduledVariable:
    """General variable which is changed during the course of training according to some schedule"""
    def __init__(self,name="variable",):
        self.name = name
        self.variable = K.variable(self.value(0), name=name)
        
    def value(self,epoch):
        """Should return a scalar value based on the current epoch.
Each subclasses should implement a method for it."""
        pass
    
    def update(self, epoch, logs):
        K.set_value(
            self.variable,
            self.value(epoch))

class GumbelSoftmax(ScheduledVariable):
    count = 0
    
    def __init__(self,N,M,min,max,full_epoch,
                 annealer    = anneal_rate,
                 beta        = 1.,
                 offset      = 0,
                 train_noise = True,
                 train_hard  = False,
                 test_noise  = False,
                 test_hard   = True, ):
        self.N           = N
        self.M           = M
        self.min         = min
        self.max         = max
        self.train_noise = train_noise
        self.train_hard  = train_hard
        self.test_noise  = test_noise
        self.test_hard   = test_hard
        self.anneal_rate = annealer(full_epoch-offset,min,max)
        self.offset      = offset
        self.beta        = beta
        super(GumbelSoftmax, self).__init__("temperature")
        
    def call(self,logits):
        u = K.random_uniform(K.shape(logits), 0, 1)
        gumbel = - K.log(-K.log(u + 1e-20) + 1e-20)

        if self.train_noise:
            train_logit = logits + gumbel
        else:
            train_logit = logits
            
        if self.test_noise:
            test_logit = logits + gumbel
        else:
            test_logit = logits

        def soft_train(x):
            return K.softmax( x / self.variable )
        def hard_train(x):
            # use straight-through estimator
            argmax  = K.one_hot(K.argmax( x ), self.M)
            softmax = K.softmax( x / self.variable )
            return K.stop_gradient(argmax-softmax) + softmax
        def soft_test(x):
            return K.softmax( x / self.min )
        def hard_test(x):
            return K.one_hot(K.argmax( x ), self.M)

        if self.train_hard:
            train_activation = hard_train
        else:
            train_activation = soft_train

        if self.test_hard:
            test_activation = hard_test
        else:
            test_activation = soft_test

        return K.in_train_phase(
            train_activation( train_logit ),
            test_activation ( test_logit  ))
    
    def __call__(self,prev):
        GumbelSoftmax.count += 1
        c = GumbelSoftmax.count-1

        layer = Lambda(self.call,name="gumbel_{}".format(c))

        logits = Reshape((self.N,self.M))(prev)
        q = K.softmax(logits)
        log_q = K.log(q + 1e-20)
        loss = K.mean(q * log_q) * self.beta

        layer.add_loss(K.in_train_phase(loss, 0.0), logits)

        return layer(logits)

    def value(self,epoch):
        return np.max([self.min,
                       self.max * np.exp(- self.anneal_rate * max(epoch - self.offset, 0))])

class BinaryConcrete(ScheduledVariable):
    count = 0

    def __init__(self,min,max,full_epoch,
                 annealer    = anneal_rate,
                 beta        = 1.,
                 offset      = 0,
                 train_noise = True,
                 train_hard  = False,
                 test_noise  = False,
                 test_hard   = True, ):
        self.min         = min
        self.max         = max
        self.train_noise = train_noise
        self.train_hard  = train_hard
        self.test_noise  = test_noise
        self.test_hard   = test_hard
        self.anneal_rate = annealer(full_epoch-offset,min,max)
        self.offset      = offset
        self.beta        = beta
        super(BinaryConcrete, self).__init__("temperature")

    def call(self,logits):
        u = K.random_uniform(K.shape(logits), 0, 1)
        logistic = K.log(u + 1e-20) - K.log(1 - u + 1e-20)

        if self.train_noise:
            train_logit = logits + logistic
        else:
            train_logit = logits

        if self.test_noise:
            test_logit = logits + logistic
        else:
            test_logit = logits

        def soft_train(x):
            return K.sigmoid( x / self.variable )
        def hard_train(x):
            # use straight-through estimator
            sigmoid = K.sigmoid(x / self.variable )
            step    = K.round(sigmoid)
            return K.stop_gradient(step-sigmoid) + sigmoid
        def soft_test(x):
            return K.sigmoid( x / self.min )
        def hard_test(x):
            sigmoid = K.sigmoid(x / self.min )
            return K.round(sigmoid)

        if self.train_hard:
            train_activation = hard_train
        else:
            train_activation = soft_train

        if self.test_hard:
            test_activation = hard_test
        else:
            test_activation = soft_test

        return K.in_train_phase(
            train_activation( train_logit ),
            test_activation ( test_logit  ))

    def __call__(self,logits):
        BinaryConcrete.count += 1
        c = BinaryConcrete.count-1

        layer = Lambda(self.call,name="concrete_{}".format(c))

        q0 = K.sigmoid(logits)
        q1 = 1-q0
        log_q0 = K.log(q0 + 1e-20)
        log_q1 = K.log(q1 + 1e-20)
        loss = K.mean(q0 * log_q0 + q1 * log_q1) * self.beta

        layer.add_loss(K.in_train_phase(loss, 0.0), logits)

        return layer(logits)

    def value(self,epoch):
        return np.max([self.min,
                       self.max * np.exp(- self.anneal_rate * max(epoch - self.offset, 0))])


# modified from https://github.com/HenningBuhl/VQ-VAE_Keras_Implementation
# note: this is useful only for convolutional embedding whre the same embedding
# can be reused across cells
class VQVAELayer(Layer):
    def __init__(self, embedding_dim, num_classes=2, beta=1.0,
                 initializer='uniform', epsilon=1e-10, **kwargs):
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        self.beta = beta
        self.initializer = keras.initializers.VarianceScaling(distribution=initializer)
        super(VQVAELayer, self).__init__(**kwargs)

    def build(self, input_shape):
        # Add embedding weights.
        self.w = self.add_weight(name='embedding',
                                  shape=(self.embedding_dim, self.num_classes),
                                  initializer=self.initializer,
                                  trainable=True)
        # Finalize building.
        super(VQVAELayer, self).build(input_shape)

    def call(self, x):
        # Flatten input except for last dimension.
        flat_inputs = K.reshape(x, (-1, self.embedding_dim))

        # Calculate distances of input to embedding vectors.
        distances = (K.sum(flat_inputs**2, axis=1, keepdims=True)
                     - 2 * K.dot(flat_inputs, self.w)
                     + K.sum(self.w ** 2, axis=0, keepdims=True))

        # Retrieve encoding indices.
        encoding_indices = K.argmax(-distances, axis=1)
        encodings = K.one_hot(encoding_indices, self.num_classes)
        encoding_indices = K.reshape(encoding_indices, K.shape(x)[:-1])
        quantized = self.quantize(encoding_indices)

        e_latent_loss = K.mean((K.stop_gradient(quantized) - x) ** 2)
        q_latent_loss = K.mean((quantized - K.stop_gradient(x)) ** 2)
        self.add_loss(e_latent_loss + q_latent_loss * self.beta)

        return K.stop_gradient(quantized - x) + x

    @property
    def embeddings(self):
        return self.w

    def quantize(self, encoding_indices):
        w = K.transpose(self.embeddings.read_value())
        return tf.nn.embedding_lookup(w, encoding_indices, validate_indices=False)


class BaseSchedule(ScheduledVariable):
    def __init__(self,schedule={0:0},*args,**kwargs):
        self.schedule = schedule
        super().__init__(*args,**kwargs)

class StepSchedule(BaseSchedule):
    """
       ______
       |
       |
   ____|

"""
    def __init__(self,*args,**kwargs):
        self.current_value = None
        super().__init__(*args,**kwargs)

    def value(self,epoch):
        assert epoch >= 0

        def report(value):
            if self.current_value != value:
                print(f"Epoch {epoch} StepSchedule(name={self.name}): {self.current_value} -> {value}")
                self.current_value = value
            return value

        pkey = None
        pvalue = None
        for key, value in sorted(self.schedule.items(),reverse=True):
            # from large to small
            key = int(key) # for when restoring from the json file
            if key <= epoch:
                return report(value)
            else:               # epoch < key 
                pkey, pvalue = key, value

        return report(pvalue)

class LinearSchedule(BaseSchedule):
    """
          ______
         /
        /
   ____/

"""
    def value(self,epoch):
        assert epoch >= 0
        pkey = None
        pvalue = None
        for key, value in sorted(self.schedule.items(),reverse=True):
            # from large to small
            key = int(key) # for when restoring from the json file
            if key <= epoch:
                if pkey is None:
                    return value
                else:
                    return \
                        pvalue + \
                        ( epoch - pkey ) * ( value - pvalue ) / ( key - pkey )
            else:               # epoch < key 
                pkey, pvalue = key, value

        return pvalue

# modified version
import progressbar
class DynamicMessage(progressbar.DynamicMessage):
    def __call__(self, progress, data):
        val = data['dynamic_messages'][self.name]
        if val:
            return self.name + ': ' + '{}'.format(val)
        else:
            return self.name + ': ' + 6 * '-'



from keras.constraints import Constraint, maxnorm,nonneg,unitnorm
class UnitNormL1(Constraint):
    def __init__(self, axis=0):
        self.axis = axis

    def __call__(self, p):
        return p / (K.epsilon() + K.sum(p,
                                        axis=self.axis,
                                        keepdims=True))

    def get_config(self):
        return {'name': self.__class__.__name__,
                'axis': self.axis}
    
