import pyximport
pyximport.install()

from collections import defaultdict
import gym
import numpy as np
import matplotlib.pyplot as plt
import time

from cqi_cpp.src.wrapper.qtree_wrapper import PyBox as Box
from cqi_cpp.src.wrapper.qtree_wrapper import PyDiscrete as Discrete
from cqi_cpp.src.wrapper.qtree_wrapper import PyQTree as QTree
from cqi_cpp.src.wrapper.qtree_wrapper import PyVector as Vector
from cqi_cpp.src.wrapper.qtree_wrapper import PyState as State
from cqi_cpp.src.wrapper.qtree_wrapper import PyAction as Action

import json
import os


def save_to_json(path, tree):
    """

    """
    with open(path, "w") as fp:
        fp.write("[\n")
        save_to_json_recursive(fp, tree)

        # remove last comma
        fp.seek(-1, os.SEEK_END)
        fp.truncate()

        fp.write("]")


def save_to_json_recursive(fp, node):
    """
    Save the DT into a json file (in 'path') visiting the tree in preorder.
    param fp:   file pointer to the json file (the file must have been opened in append mode).
    param node: the node to write into the file.
    return:     nothing.
    """
    if node is not None:
        if node.is_leaf():
            data = {
                "type": "leaf",
                "visit_freq": node.visits,
                "Q_values": node.qs
            }
        else:
            data = {
                "type": "internal",
                "visit_freq": node.visits,
                "has_left_child": False if node.left_child is None else True,
                "has_right_child": False if node.right_child is None else True,
                "feature": node.feature,
                "value": node.value
            }

        json_obj = json.dumps(data, indent=4)
        fp.write(json_obj)
        fp.write(",\n")

        save_to_json(node.left_child)
        save_to_json(node.right_child)
