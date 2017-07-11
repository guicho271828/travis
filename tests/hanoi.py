#!/usr/bin/env python3

import numpy as np
import sys
sys.path.append('../../')

from latplan.puzzles.hanoi import generate_configs, successors, generate, states, transitions

from plot import plot_image, plot_grid

disks = 6
configs = generate_configs(disks)
puzzles = generate(configs)
print(puzzles.shape)
print(puzzles[10])
plot_image(puzzles[0],"hanoi.png")
plot_grid(puzzles[:36],"hanois.png")
_transitions = transitions(disks)
print(_transitions.shape)
import numpy.random as random
indices = random.randint(0,_transitions[0].shape[0],18)
_transitions = _transitions[:,indices]
print(_transitions.shape)
transitions_for_show = \
    np.einsum('ba...->ab...',_transitions) \
      .reshape((-1,)+_transitions.shape[2:])
print(transitions_for_show.shape)
plot_grid(transitions_for_show,"hanoi_transitions.png")
