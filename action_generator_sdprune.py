#!/usr/bin/env python3
import warnings
import config
import numpy as np
from model import GumbelAE, ActionDiscriminator, default_networks

import keras.backend as K
import tensorflow as tf

float_formatter = lambda x: "%.3f" % x
np.set_printoptions(formatter={'float_kind':float_formatter})

################################################################


from plot import plot_ae

def main():
    import numpy.random as random
    from trace import trace

    import sys
    if len(sys.argv) == 1:
        sys.exit("{} [directory]".format(sys.argv[0]))

    directory = sys.argv[1]
    directory_ad = "{}_ad/".format(directory)
    print("loading the ActionDiscriminator", end='...', flush=True)
    ad = ActionDiscriminator(directory_ad).load()
    print("done.")
    name = "generated_actions.csv"

    print("loading {}".format("{}/generated_states.csv".format(directory)), end='...', flush=True)
    states  = np.loadtxt("{}/generated_states.csv".format(directory),dtype=np.uint8)
    print("done.")
    total   = states.shape[0]
    N       = states.shape[1]
    actions = np.pad(states,((0,0),(0,N)),"constant")

    acc = 0
    
    try:
        print(ad.local(name))
        with open(ad.local(name), 'wb') as f:
            for i,s in enumerate(states):
                print("Iteration {}/{} base: {}".format(i,total,i*total), end=' ')
                actions[:,N:] = s
                ys            = ad.discriminate(actions,batch_size=400000)
                valid_actions = actions[np.where(ys > 0.8)]
                acc           += len(valid_actions)
                print(len(valid_actions),acc)
                np.savetxt(f,valid_actions,"%d")
    except KeyboardInterrupt:
        print("dump stopped")

if __name__ == '__main__':
    main()
    
    
"""

* Summary:

Dump all actions classified as valid by a discriminator.

Input: states generated by EB-discriminator

2190258 states
 362880 states (true variation ---- x7 redundancy)

"""
