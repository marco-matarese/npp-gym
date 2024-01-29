import pyximport
pyximport.install()

from collections import defaultdict
import numpy as np
import time

from cqi_cpp.src.wrapper.qtree_wrapper import PyBox as Box
from cqi_cpp.src.wrapper.qtree_wrapper import PyDiscrete as Discrete
from cqi_cpp.src.wrapper.qtree_wrapper import PyQTree as QTree
from cqi_cpp.src.wrapper.qtree_wrapper import PyVector as Vector
from cqi_cpp.src.wrapper.qtree_wrapper import PyState as State
from cqi_cpp.src.wrapper.qtree_wrapper import PyAction as Action

from NuclearPowerPlant import NuclearPowerPlant
from partner_model import PartnerModel

from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal


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


def verbalise_explanation(feature, direction, value):

    features_names = {
        0: "temperature of the water in the core",
        1: "pressure of the core",
        2: "level of water in the steam generator",
        3: "power of the reactor",
        4: "security rods",
        5: "sustain rods",
        6: "fuel rods",
        7: "regulatory rods"
    }

    unit_measure = ""

    if feature < 4:
        direction_string = " is minor or equal " if direction == -1.0 else " is greater "
        value = int(value)

        if feature == 0:
            direction_string += "than "
            unit_measure = " degrees"
        elif feature == 1:
            direction_string += "than "
            unit_measure = " atmospheres"
        elif feature == 2:
            direction_string += "than "
            unit_measure = " cubic meters"
        elif feature == 3:
            direction_string += "than "
            unit_measure = " megawat"

    else:
        direction_string = " are "
        if feature == 5 or feature == 7:
            if value <= 0.5:
                value = "up"
            elif value <= 1.5:
                direction_string += "a "
                value = "middle"
            else:
                value = "down"
        elif feature == 4 or feature == 6:
            if value <= 0.5:
                value = "up"
            else:
                value = "down"

    starting = "Because the "
    if feature == 2:
        starting = "Because the "
    elif feature in [4, 5, 6, 7]:
        starting = "Because the "

    return starting + features_names[feature] + direction_string + str(value) + unit_measure


def verbalise_suggestion(action):
    action_subject_names = {
        0: 'skip',
        1: 'security rods',
        2: 'security rods',
        3: 'sustain rods',
        4: 'sustain rods',
        5: 'sustain rods',
        6: 'fuel rods',
        7: 'fuel rods',
        8: 'regulatory rods',
        9: 'regulatory rods',
        10: 'regulatory rods',
        11: 'water in the steam generator'
    }

    ending = ""
    if action == 0:
        phrase = "I would "
    elif 0 < action < 11:
        phrase = "I would set "
        if action == 1 or action == 3 or action == 6 or action == 8:
            ending = " up the "
        elif action == 2 or action == 5 or action == 7 or action == 10:
            ending = " down the "
        elif action == 4 or action == 9:
            ending = " middle the "
    elif action == 11:
        phrase = "I would add "
    phrase += action_subject_names[action] + ending

    return phrase


class Train(object):
    def __init__(self, qfunc, gym_env):
        self.qfunc = qfunc
        self.env = gym_env

    def train(self, num_steps, eps_func, eval_only=False, track_data_per=0):
        if eval_only:
            pass
            # self.qfunc.print_structure()
        hist = defaultdict(list)   # number of nodes, reward per ep
        ep_r = 0
        done = True
        r_per_ep = []
        ts_per_ep = []
        num_eps = 0
        last_step_ep = -1
        for step in range(num_steps):
            if done:
                if eval_only and step > 0:
                    r_per_ep.append(ep_r)
                    ts = step - last_step_ep
                    ts_per_ep.append(ts)
                    last_step_ep = step
                if track_data_per > 0 and num_eps % track_data_per == 0:
                    hist[self.qfunc.num_nodes()].append(ep_r)
                    num_nodes = self.qfunc.num_nodes()
                s = self.env.reset()
                ep_r = 0
                num_eps = num_eps + 1
                done = False
            if np.random.random() < eps_func(step):
                a = self.env.action_space.sample()
            else:
                s = convert_to_pystate(s)
                a = self.qfunc.select_a(s)
            s2, r, done, _ = self.env.step(a)
            if not eval_only:
                s, s2 = convert_to_pystate(s), convert_to_pystate(s2)
                a = Action(a)

                self.qfunc.take_tuple(s, a, r, s2, done)
            s = s2
            ep_r += r
        if eval_only:
            # avg_r_per_ep = np.mean(r_per_ep)
            avg_r_per_ep = r_per_ep
            return hist, avg_r_per_ep
        else:
            return hist


class NPPModel(QObject):

    finished = pyqtSignal()
    env_obs_signal = pyqtSignal()
    DT_action_signal = pyqtSignal()
    explanation_signal = pyqtSignal()
    anomaly_signal = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, user_id, exp_type):
        super(NPPModel, self).__init__()
        
        # creating the DT
        self.env = NuclearPowerPlant()
        self.discrete = Discrete(self.env.action_space.n)
        self.box = convert_to_pybox(self.env.observation_space)
        self.alpha = 0.01
        self.gamma = 0.8
        self.split_threshold_max = 1000000
        self.no_splits = 7
        self.DT = QTree(self.box, self.discrete, None, gamma=self.gamma, alpha=self.alpha, visit_decay=0.999,
                        split_thresh_max=1000000, split_thresh_decay=0.99, num_splits=3)
        self.fileName = "models/winner_DT.txt"

        self.DT.set_root_from_file(self.fileName.encode())

        self.partner_model = PartnerModel(user_id, exp_type)

    def restart(self):
        self.env.reset()

    def get_DT_action(self):
        """
        :return: the action the DT'd perform in self.env.get_observation() scenario.
        """
        obs = self.env.get_observation()
        pystate = convert_to_pystate(obs)
        action = self.DT.select_a(pystate)

        action = self.skip_action_patch(obs, action)

        if action is None:
            return "Farei skip"

        if self.check_action_with_effects(obs, int(action)):
            phrase = verbalise_suggestion(int(action))
        else:
            phrase = verbalise_suggestion(0)    # "I'd skip"
        return phrase

    def skip_action_patch(self, obs, action):

        if obs[0] < 110.0 and obs[3] == 0.0:
            if obs[4] == 1:
                return 1
            elif obs[6] == 0:
                return 7
        return action

    def check_action_with_effects(self, obs, action):
        has_effects = True

        if (action == 1 and obs[4] == 0) or (action == 2 and obs[4] == 1) or (action == 3 and obs[5] == 0) or \
           (action == 4 and obs[5] == 1) or (action == 5 and obs[5] == 2) or (action == 6 and obs[6] == 0) or \
           (action == 7 and obs[6] == 1) or (action == 8 and obs[7] == 0) or (action == 9 and obs[7] == 1) or \
           (action == 10 and obs[7] == 2):
            has_effects = False

        return has_effects

    def get_classical_explanation(self, action=None):
        obs = self.env.get_observation()
        if action is None:
            pystate = convert_to_pystate(obs)
            action = self.DT.select_a(pystate)
            action = int(action)

        explanation = self.DT.explain_classic(action, obs, True)
        expl_phrase = verbalise_explanation(explanation[0], explanation[1], explanation[2])

        return expl_phrase

    def get_useraware_explanation(self, action=None, user_indicated_action=None):
        obs = self.get_observation()
        if action is None:
            pystate = convert_to_pystate(obs)
            action = self.DT.select_a(pystate)
            action = int(action)

        if user_indicated_action is None:
            user_action = self.partner_model.get_prediction(obs)
        else:
            user_action = user_indicated_action

        if user_action is None:         # or user_action == action:
            print("GET_USERAWARE_EXPLANATION CALLS EXPLAIN_CLASSIC")
            explanation = self.DT.explain_classic(action, obs, True)
        else:
            print("GET_USERAWARE_EXPLANATION CALLS EXPLAIN_USERAWARE")
            explanation = self.DT.explain_useraware(user_action, action, obs, False)

        expl_phrase = verbalise_explanation(explanation[0], explanation[1], explanation[2])

        return expl_phrase

    def perform_user_action(self, action):
        obs, r, anomaly, info = self.env.step(int(action))
        if anomaly:
            self.anomaly_signal.emit()
        return obs, anomaly, info

    def get_observation(self):
        return self.env.get_observation()

    def run(self):
        anomaly = False
        self.env.reset()

        while not anomaly:
            obs = self.env.get_observation()

            print("temperature_water_core (40-380 °C):", obs[0])
            print("pressure_core (1-220 ATM):", obs[1])
            print("level_water_steam_generator (20-140 m3):", obs[2])
            print("reactor_power (0-1000 MWh):", obs[3])
            print("safety_rods (0-1):", obs[4])
            print("sustain_rods (0-1-2):", obs[5])
            print("fuel_rods (0-1):", obs[6])
            print("regulatory_rods (0-1-2):", obs[7])

            pystate = convert_to_pystate(obs)
            action = self.DT.select_a(pystate)

            print("ACTION iCUB'D TAKE:", action)

            explanation = self.DT.explain(action, obs, True)

            print("EXPLAINATION:", verbaliseExplanation(explanation[0], explanation[1], explanation[2]))
            user_action = input('YOUR ACTION: ')
            obs, r, anomaly, info = self.env.step(user_action)
            print("ENERGY:", info['energy'])
            print("-------------------------------------------")
            time.sleep(2.0)
            if anomaly:
                print("BOOM!")
                print(info)

    def comm_partner_model_confirmed_action(self, action):
        self.partner_model.set_action_to_last_obs(action)

    def comm_partner_model_action_declaration(self, action):
        self.partner_model.set_last_action_declaration(action)

    def comm_partner_model_obs(self, obs):
        self.partner_model.add_observation(obs)
