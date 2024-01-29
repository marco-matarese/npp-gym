from sklearn.cluster import KMeans
from sklearn.cluster import k_means
import numpy as np
import csv


class PartnerModel:
    """

    """

    def __init__(self, user_id, exp_type):
        self.k = 12
        self.no_features = 8
        self.observations = np.empty(shape=[0, self.no_features])
        self.observations = np.append(self.observations, [[80, 30, 120, 0, 1, 0, 1., 0]], axis=0)   # first obs
        self.actions_declared = np.empty(shape=[0, 1], dtype=int)
        self.actions_frequencies = np.zeros(shape=[self.k, self.k])   # rows represent clusters, columns the users' actions frequencies

        # boundaries of the environment's features
        self.temperature_water_core_boundaries = np.array([80, 380])
        self.pressure_core_boundaries = np.array([1, 220])
        self.level_water_steam_generator_boundaries = np.array([20, 140])
        self.reactor_power_boundaries = np.array([0.0, 1000.0])
        self.safety_rods_boundaries = np.array([0, 1])
        self.sustain_rods_boundaries = np.array([0, 2])
        self.fuel_rods_boundaries = np.array([0, 1])
        self.regulatory_rods_boundaries = np.array([0, 2])

        self.last_action_declaration = None
        self.last_obs = None
        self.last_action_confirmed = None
        self.last_prediction = None
        self.user_id = user_id

        log_filename = 'log/partner_model_' + user_id + '_' + str(exp_type) + '.csv'
        self.file_log = open(log_filename, 'w')
        self.file_log_writer = csv.writer(self.file_log)
        self.file_log_writer.writerow(['observation', 'declared_action', 'prediction', 'confirmed_action'])

    def normalize_observation_values(self, obs):
        """
        :param obs: np.array([  self.temperature_water_core, self.pressure_core, self.level_water_steam_generator,
                                self.reactor_power, self.safety_rods,
                                self.sustain_rods, self.fuel_rods, self.regulatory_rods],
                            dtype=np.float)
        :return: normalized (between [0, 1]) obs
        """
        obs[0] = (obs[0] - self.temperature_water_core_boundaries.min()) / \
                 (self.temperature_water_core_boundaries.max() - self.temperature_water_core_boundaries.min())
        obs[1] = (obs[1] - self.pressure_core_boundaries.min()) / \
                 (self.pressure_core_boundaries.max() - self.pressure_core_boundaries.min())
        obs[2] = (obs[2] - self.level_water_steam_generator_boundaries.min()) / \
                 (self.level_water_steam_generator_boundaries.max() - self.level_water_steam_generator_boundaries.min())
        obs[3] = (obs[3] - self.reactor_power_boundaries.min()) / \
                 (self.reactor_power_boundaries.max() - self.reactor_power_boundaries.min())
        obs[4] = (obs[4] - self.safety_rods_boundaries.min()) / \
                 (self.safety_rods_boundaries.max() - self.safety_rods_boundaries.min())
        obs[5] = (obs[5] - self.sustain_rods_boundaries.min()) / \
                 (self.sustain_rods_boundaries.max() - self.sustain_rods_boundaries.min())
        obs[6] = (obs[6] - self.fuel_rods_boundaries.min()) / \
                 (self.fuel_rods_boundaries.max() - self.fuel_rods_boundaries.min())
        obs[7] = (obs[7] - self.regulatory_rods_boundaries.min()) / \
                 (self.regulatory_rods_boundaries.max() - self.regulatory_rods_boundaries.min())
        return obs

    def get_prediction(self, obs):
        """
        :param obs: new observation
        :return:    action prediction (or None if it cannot perform k-means)
        """

        # self.last_obs = obs

        # perform k-means
        if len(self.observations) < self.k:
            return None
        centroids, labels, inertia = k_means(self.observations, self.k)

        # update self.action_frequencies
        i = 0
        self.actions_frequencies.fill(0)
        # for each observation but the new one (because it doesn't have an associated action already
        for x in self.observations[:-1]:
            cluster = np.argmin([np.linalg.norm(x - b) for b in centroids])
            action = self.actions_declared[i]
            # print("indexes:", cluster, action)
            self.actions_frequencies[cluster][action] += 1
            i += 1

        # find the cluster that obs belongs to
        curr_centroid = np.argmin([np.linalg.norm(obs - b) for b in centroids])

        # retrieve frequencies of that cluster
        action_prediction = np.argmax(self.actions_frequencies[curr_centroid])

        print("ACTION FREQUENCES:", self.actions_frequencies)
        print("USER'S ACTION PREDICTION:", action_prediction)

        self.last_prediction = action_prediction

        return action_prediction

    def set_action_to_last_obs(self, action):

        if self.last_action_declaration is not None:
            self.actions_declared = np.append(self.actions_declared, self.last_action_declaration)

            print("saved action declaration")
            self.last_action_confirmed = action
            self.log()
            self.last_action_declaration = None
        else:
            self.actions_declared = np.append(self.actions_declared, action)
            self.last_action_declaration = action
            self.last_action_confirmed = action
            self.log()

            print("saved action performed")

    def add_observation(self, obs):
        self.observations = np.append(self.observations, [obs], axis=0)
        self.last_obs = obs

    def set_last_action_declaration(self, action):
        self.last_action_declaration = action

        print("action declaration", action)

    def print_observation(self):
        print(self.observations)

    def print_actions_declared(self):
        print(self.actions_declared)

    def log(self):
        self.file_log_writer.writerow([self.last_obs, self.last_action_declaration, self.last_prediction, self.last_action_confirmed])
