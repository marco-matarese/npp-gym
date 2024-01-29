# npp-gym
This project refers to a nuclear power plant (NPP) management task and contains:
# An [OpenAI Gym](https://www.gymlibrary.dev/) environemnt in which train a reinforcement learning agent.
# An AI agent which uses a decision tree (DT) build with the [Conservative Q-Improvement](https://arxiv.org/abs/1907.01180) (CQI) technique.
# An XAI model which can produce two explanation strategies: classic, following only the DT action path, and contrastive, which produces a contrastive explanation given a _fact_.
# A GUI with which perform the NPP management task and interact with the (X)AI agent.

## Dependancies
The following list contains the dependancies of the project. Please, be sure to install all of them before using the NPP environment and/or DT model.

# [Conservative Q-Improvement](https://github.com/AMR-/Conservative-Q-Improvement)
# gym
# sklearn
# numpy

## Usage
This project is meant to be used for research purposes. The author wishes to thank Aaron M. Roth for providing support about the CQI method and code.
