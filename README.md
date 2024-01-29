# npp-gym
This project refers to a nuclear power plant (NPP) management task and contains:
- An [OpenAI Gym](https://www.gymlibrary.dev/) environemnt in which train a reinforcement learning agent.
- An AI agent which uses a decision tree (DT) build with the [Conservative Q-Improvement](https://arxiv.org/abs/1907.01180) (CQI) technique.
- An XAI model which can produce two explanation strategies: _classic_, following only the DT action path, and _user aware_, which produces a contrastive explanation given a _fact_.
- A GUI to perform the NPP management task and interact with the (X)AI agent.

## Dependancies
The following list contains the dependencies of the project. Please be sure to install all of them before using the NPP environment and/or DT model.

- [Conservative Q-Improvement](https://github.com/AMR-/Conservative-Q-Improvement)
- [gym](https://www.gymlibrary.dev/)
- [sklearn](https://scikit-learn.org/)
- [numpy](https://numpy.org/)

## Usage
This project is meant to be used for research purposes. The author wishes to thank Aaron M. Roth for providing support about the CQI method and code. This project has been developed and tested with Python 3.6.

An example of usage is reported in the main.py file.

1. Create the environment and set the action and observation spaces.
```python
env = NuclearPowerPlant()
discrete = Discrete(env.action_space.n)
box = convert_to_pybox(env.observation_space)
```

2. Create the decision tree (DT) using custom meta-parameters.
```python
alpha = 0.01
gamma = 0.8
split_threshold_max = 1000000
no_splits = 7
DT = QTree(box, discrete, None, gamma=gamma, alpha=alpha, visit_decay=0.999, split_thresh_max=1000000,
           split_thresh_decay=0.99, num_splits=3)
fileName = "models/DT.txt"
DT.set_root_from_file(fileName.encode())
```

3. Select the DT's action for a pre-defined state of the environment.
```python
obs = np.array([80, 30, 120, 910, 1, 0, 1, 0])
pystate = convert_to_pystate(obs)
action = DT.select_a(pystate)
print("action", action)
```

4. Explain the selected action using both explanation strategies.
```python
expl = DT.explain_classic(action, obs, False)
print("classical", expl)
expl = DT.explain_useraware(0, action, obs, True)
print("contrastive", expl)
```
