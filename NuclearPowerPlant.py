import gym
from gym.spaces import Box, Discrete, Tuple, MultiDiscrete
import numpy as np
from enum import Enum

# ACTIONS' CODES
SKIP = 0
SET_SAFETY_RODS_UP = 1
SET_SAFETY_RODS_DOWN = 2
SET_SUSTAIN_RODS_UP = 3
SET_SUSTAIN_RODS_MEDIUM = 4
SET_SUSTAIN_RODS_DOWN = 5
SET_FUEL_RODS_UP = 6
SET_FUEL_RODS_DOWN = 7
SET_REGULATORY_RODS_UP = 8
SET_REGULATORY_RODS_MEDIUM = 9
SET_REGULATORY_RODS_DOWN = 10
ADD_WATER_STEAM_GENERATOR = 11


class NuclearPowerPlant(gym.Env):
    """
    Gym environment to manage the nuclear power plant.
    """

    def __init__(self):
        self.action_space = Discrete(12)
        self.observation_space = Tuple((
            Box(low=40, high=380, shape=(1,), dtype=int),
            Box(low=1, high=220, shape=(1,), dtype=int),
            Box(low=20, high=140, shape=(1,), dtype=int),
            Box(low=0.0, high=1000.0, shape=(1,), dtype=float),
            Discrete(2),
            Discrete(3),
            Discrete(2),
            Discrete(3)
            )
        )

        # env features
        self.temperature_water_core = 80.0      # °C
        self.pressure_core = 1.0                # ATM
        self.level_water_steam_generator = 120  # m2
        self.reactor_power = 0.0                # MW
        self.safety_rods = 1
        self.sustain_rods = 0
        self.fuel_rods = 1
        self.regulatory_rods = 0

        # variation values
        self.delta_temperature_water_core = 0.0
        self.delta_pressure_core = 0.0
        self.delta_level_water_steam_generator = 0.0

        # functional boundaries
        self.temperature_water_core_boundaries = np.array([160.0, 380.0])
        self.pressure_core_boundaries = np.array([1.0, 220.0])
        self.level_water_steam_generator_boundaries = np.array([20.0, 140.0])
        self.reactor_power_boundaries = np.array([0.0, 1000.0])

        self.no_steps = 0
        self.no_critic_steps = 0
        self.critic_gamma = 0.1
        self.action_discount_factor = 0.33
        self.critic_multiply_factor = 1.1

        self.prev_action = -1


    def __del__(self):
        del self.action_space
        del self.observation_space


    def reset(self):
        # env features
        self.temperature_water_core = 80.0  # °C
        self.pressure_core = 1.0  # ATM
        self.level_water_steam_generator = 120  # m2
        self.reactor_power = 0.0  # MW
        self.safety_rods = 1
        self.sustain_rods = 0
        self.fuel_rods = 1
        self.regulatory_rods = 0

        # variation values
        self.delta_temperature_water_core = 0.0
        self.delta_pressure_core = 0.0
        self.delta_level_water_steam_generator = 0.0

        self.no_steps = 0
        self.prev_action = -1

        obs = self.get_observation()
        return obs


    def step(self, action):
        """
        Performs the action on the environment.
        :param action: the action to execute.
        :return: reward (float), whether an anomaly happened (bool), info (string)
        """

        action_with_effects = self.last_action_had_effects(action)
        self.update_features(action)
        self.set_deltas(action)
        self.update_features_with_deltas()
        anomaly_detected, info_anomalies = self.detect_anomalies()
        self.set_reactor_power()
        energy = self.compute_energy()

        if energy > 0.0:
            self.no_critic_steps += 1
        else:
            self.no_critic_steps = 0
        if anomaly_detected:
            self.no_critic_steps = 0
        self.no_steps += 1

        reward = self.compute_reward(anomaly_detected, info_anomalies, action, energy, action_with_effects)
        obs = self.get_observation()

        self.prev_action = action
        # print("ENERGY PRODUCED:", energy)
        info = {
            "action_with_effects": action_with_effects,
            "energy": energy,
            "info_anomalies": info_anomalies
        }

        return obs, reward, anomaly_detected, info


    def update_features(self, action):
        """
        Changes the values of  features depending on the action received.
        :param action: the executed action.
        :return: False if takes an unexpected action, True otherwise.
        """
        if action == SKIP:
            pass

        elif action == SET_SAFETY_RODS_UP:
            self.safety_rods = 0

        elif action == SET_SAFETY_RODS_DOWN:
            self.safety_rods = 1

        elif action == SET_FUEL_RODS_UP:
            self.fuel_rods = 0

        elif action == SET_FUEL_RODS_DOWN:
            self.fuel_rods = 1

        elif action == SET_REGULATORY_RODS_UP:
            self.regulatory_rods = 0

        elif action == SET_REGULATORY_RODS_MEDIUM:
            self.regulatory_rods = 1

        elif action == SET_REGULATORY_RODS_DOWN:
            self.regulatory_rods = 2

        elif action == SET_SUSTAIN_RODS_UP:
            self.sustain_rods = 0

        elif action == SET_SUSTAIN_RODS_MEDIUM:
            self.sustain_rods = 1

        elif action == SET_SUSTAIN_RODS_DOWN:
            self.sustain_rods = 2

        elif action == ADD_WATER_STEAM_GENERATOR:
            self.level_water_steam_generator += 60.0

        else:
            # unexpected action!
            return False

        return True


    def set_deltas(self, action):
        """

        :param action:
        :return:
        """

        tmp_delta_pressure_core = np.nan
        tmp_delta_temperature_water_core = np.nan
        tmp_delta_level_water_steam_generator = np.nan

        if (self.safety_rods == 1) or (self.fuel_rods == 0):
            # if the safety rods are down or fuel rods are up, the fission doesn't take place, no matter what
            tmp_delta_temperature_water_core = -20.0
            tmp_delta_pressure_core = -20.0
            tmp_delta_level_water_steam_generator = 0.0

        else:
            # so SAFETY RODS are UP and FUEL RODS are DOWN -> the fission is taking place
            # because: not(S_dw or F_up) = not(S_dw) and not(F_up) = S_up and F_dw.

            tmp_delta_temperature_water_core = 30.0
            tmp_delta_pressure_core = 20.0
            tmp_delta_level_water_steam_generator = -8.0

            if self.sustain_rods == 0:
                pass
            elif self.sustain_rods == 1:
                tmp_delta_temperature_water_core += 10.0
                tmp_delta_pressure_core += 5.0
                tmp_delta_level_water_steam_generator -= 4.0
            else:
                # sustain rods == 2
                tmp_delta_temperature_water_core += 20.0
                tmp_delta_pressure_core += 10.0
                tmp_delta_level_water_steam_generator -= 8.0

            if self.regulatory_rods == 0:
                pass
            elif self.regulatory_rods == 1:
                tmp_delta_temperature_water_core -= 10.0
                tmp_delta_pressure_core -= 5.0
                tmp_delta_level_water_steam_generator += 2.0
            else:
                # regulatory rods == 2
                tmp_delta_temperature_water_core -= 20.0
                tmp_delta_pressure_core -= 10.0
                tmp_delta_level_water_steam_generator += 4.0

        self.delta_pressure_core = tmp_delta_pressure_core
        self.delta_temperature_water_core = tmp_delta_temperature_water_core
        self.delta_level_water_steam_generator = tmp_delta_level_water_steam_generator


    def update_features_with_deltas(self):
        """

        :return:
        """
        self.temperature_water_core += self.delta_temperature_water_core
        self.pressure_core += self.delta_pressure_core
        self.level_water_steam_generator += self.delta_level_water_steam_generator

        self.adjust_lower_bound_if_needed()


    def adjust_lower_bound_if_needed(self):
        """
        Adjust the value of temperature and pressure of the (water) core if, after a delta update,
        they decrease their minimum level.
        If so, it brings these parameters to their initial values.
        """
        if self.temperature_water_core < 80.0:
            self.temperature_water_core = 80.0
        if self.pressure_core < 1.0:
            self.pressure_core = 1.0


    def detect_anomalies(self):
        """
        Detects anomalies based on the current values of temperature, pressure and level of water.
        :return: if an anomaly has been detected (bool), info about the anomalies (string)
        """

        anomaly_detected = False
        info = ""

        # check temperature
        if self.temperature_water_core > self.temperature_water_core_boundaries.max():
            anomaly_detected = True
            # info = "Temperature of the water into the core higher than the maximum allowed.\n"
            info = "Temperatura dell'acqua nel nocciolo più alta del massimo consentito.\n"

        # check pressure
        if self.pressure_core > self.pressure_core_boundaries.max():
            anomaly_detected = True
            # info += "Pressure of the core higher than the maximum allowed.\n"
            info += "Pressione del nocciolo più alta del massimo consentito.\n"

        # check water level
        if self.level_water_steam_generator > self.level_water_steam_generator_boundaries.max():
            anomaly_detected = True
            # info += "Level of the water into the steam generator higher than the maximum allowed.\n"
            info += "Livello dell'acqua nel generatore di vapore più alta del massimo consentito.\n"
        elif self.level_water_steam_generator < self.level_water_steam_generator_boundaries.min():
            anomaly_detected = True
            # info += "Level of the water into the steam generator lower than the minimum allowed.\n"
            info += "Livello dell'acqua nel generatore di vapore più bassa del minimo consentito.\n"

        return anomaly_detected, info


    def set_reactor_power(self):
        """
        Set the power of the reactor: 0 if the functioning values are not satisfied.
        """

        if self.safety_rods == 1:
            self.reactor_power = self.reactor_power_boundaries.min()

        else:

            if self.check_functioning_values():

                self.reactor_power = 1000.0 - (self.no_steps * 5.5)  # the power decreases over time

                if self.regulatory_rods == 1:
                    self.reactor_power -= 200.0
                elif self.regulatory_rods == 2:
                    self.reactor_power -= 400.0

                if self.sustain_rods == 1:
                    self.reactor_power += 200.0
                elif self.sustain_rods == 2:
                    self.reactor_power += 400.0

                if self.reactor_power > self.reactor_power_boundaries.max():
                    self.reactor_power = self.reactor_power_boundaries.max()
                elif self.reactor_power < self.reactor_power_boundaries.min():
                    self.reactor_power = self.reactor_power_boundaries.min()

            else:
                self.reactor_power = self.reactor_power_boundaries.min()


    def check_functioning_values(self):
        return self.temperature_water_core >= self.temperature_water_core_boundaries.min() and \
               self.level_water_steam_generator >= self.level_water_steam_generator_boundaries.min()


    def get_observation(self):
        """
        :return: the features of the environemt.
        """
        obs = np.array([self.temperature_water_core, self.pressure_core, self.level_water_steam_generator,
                        self.reactor_power, self.safety_rods,
                        self.sustain_rods, self.fuel_rods, self.regulatory_rods], dtype=np.float)
        return obs


    def compute_energy(self):
        """
        :return: the amount of energy computed in a step based on the current reactor power.
        """
        if self.fuel_rods == 1:
            return self.reactor_power / 360.0  # kWh
        else:
            return 0.0


    def compute_reward(self, anomaly_detected, info, action, energy, action_with_effects):
        """

        :param anomaly_detected:
        :param info:
        :param action:
        :param energy:
        :param action_with_effects:
        :return:
        """

        if anomaly_detected:
            reward = -100.0

        else:
            if action_with_effects:
                # reward = energy + (energy * (self.critic_gamma * self.no_critic_steps))
                # reward = energy * (self.critic_gamma * self.no_critic_steps)
                # reward = energy * self.critic_multiply_factor * (self.no_critic_steps + 1)
                reward = energy * (self.no_critic_steps + 1)
            else:
                # reward = energy + (energy * (self.critic_gamma * self.no_critic_steps) - self.action_cost)
                # reward = energy * (self.critic_gamma * self.no_critic_steps) - self.action_cost
                # reward = (energy * self.critic_multiply_factor * self.no_critic_steps) - self.action_discount_factor
                reward = energy * self.action_discount_factor

        return reward


    def last_action_had_effects(self, action):
        """
        :param action:  the last action performed.
        :return:        True if 'action' had effect on the env based on its current features' values; False otherwise.
        """
        had_effects = False

        if action == SKIP or action == ADD_WATER_STEAM_GENERATOR:
            had_effects = True

        elif action == SET_SAFETY_RODS_DOWN:
            if self.safety_rods == 0:
                had_effects = True
            else:
                had_effects = False
        elif action == SET_SAFETY_RODS_UP:
            if self.safety_rods == 1:
                had_effects = True
            else:
                had_effects = False

        elif action == SET_SUSTAIN_RODS_UP:
            if self.sustain_rods == 1 or self.sustain_rods == 2:
                had_effects = True
            else:
                had_effects = False
        elif action == SET_SUSTAIN_RODS_MEDIUM:
            if self.sustain_rods == 0 or self.sustain_rods == 2:
                had_effects = True
            else:
                had_effects = False
        elif action == SET_SUSTAIN_RODS_DOWN:
            if self.sustain_rods == 0 or self.sustain_rods == 1:
                had_effects = True
            else:
                had_effects = False

        elif action == SET_FUEL_RODS_UP:
            if self.fuel_rods == 1:
                had_effects = True
            else:
                had_effects = False
        elif action == SET_FUEL_RODS_DOWN:
            if self.fuel_rods == 0:
                had_effects = True
            else:
                had_effects = False

        elif action == SET_REGULATORY_RODS_UP:
            if self.regulatory_rods == 1 or self.regulatory_rods == 2:
                had_effects = True
            else:
                had_effects = False
        elif action == SET_REGULATORY_RODS_MEDIUM:
            if self.regulatory_rods == 0 or self.regulatory_rods == 2:
                had_effects = True
            else:
                had_effects = False
        elif action == SET_REGULATORY_RODS_DOWN:
            if self.regulatory_rods == 0 or self.regulatory_rods == 1:
                had_effects = True
            else:
                had_effects = False

        return had_effects
