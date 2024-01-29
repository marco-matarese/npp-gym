from view import NPPGui
from cqi_cpp.src.wrapper.qtree_wrapper import PyBox as Box
from cqi_cpp.src.wrapper.qtree_wrapper import PyDiscrete as Discrete
from cqi_cpp.src.wrapper.qtree_wrapper import PyQTree as QTree
from cqi_cpp.src.wrapper.qtree_wrapper import PyVector as Vector
from cqi_cpp.src.wrapper.qtree_wrapper import PyState as State
from cqi_cpp.src.wrapper.qtree_wrapper import PyAction as Action
from NuclearPowerPlant import NuclearPowerPlant
import numpy as np

import sys

def convert_to_pybox(b):
    low = Vector()
    high = Vector()
    
    low.add(40)
    low.add(1)
    low.add(20)
    low.add(0)
    low.add(0.0)
    low.add(-1)
    low.add(0)
    low.add(-1)
    high.add(380)
    high.add(220)
    high.add(140)
    high.add(1000.0)
    high.add(1)
    high.add(1)
    high.add(1)
    high.add(1)
    
    return Box(low, high)

def convert_to_pystate(s):
    if type(s) is State:
        return s
    v = Vector()
    for i in s:
        v.add(i)
    return State(v)


if __name__ == '__main__':
    
    env = NuclearPowerPlant()
    discrete = Discrete(env.action_space.n)
    box = convert_to_pybox(env.observation_space)
    alpha = 0.01
    gamma = 0.8
    split_threshold_max = 1000000
    no_splits = 7
    DT = QTree(box, discrete, None, gamma=gamma, alpha=alpha, visit_decay=0.999, split_thresh_max=1000000,
               split_thresh_decay=0.99, num_splits=3)
    fileName = "models/DT.txt"
    DT.set_root_from_file(fileName.encode())

    obs = np.array([80, 30, 120, 910, 1, 0, 1, 0])
    pystate = convert_to_pystate(obs)
    action = DT.select_a(pystate)
    print("action", action)

    expl = DT.explain_classic(action, obs, False)
    print("classical", expl)
    expl = DT.explain_useraware(0, action, obs, True)
    print("contrastive", expl)

