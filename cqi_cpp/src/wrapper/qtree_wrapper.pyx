# distutils: language = c++
# distutils: sources = qtree_wrapper.cpp

from libcpp.string cimport string
from libcpp.unordered_map cimport unordered_map
from libcpp.vector cimport vector

cdef extern from "../../include/state.hpp":
    cdef cppclass State:
        vector[double]* state
        State(vector[double]*)

cdef extern from "../../include/action.hpp":
    cdef cppclass Action:
        int value
        Action(int)

cdef extern from "../../include/discrete.hpp":
    cdef cppclass Discrete:
        int n
        Discrete(int)

        int sample()
        int size()
        bint contains(int)

cdef extern from "../../include/box.hpp":
    cdef cppclass Box:
        vector[double]* low
        vector[double]* high

        Box(vector[double]*, vector[double]*)
        vector[double]* sample()
        bint contains(vector[double]*)

cdef extern from "../../include/qtreenode.hpp":
    cdef cppclass QTreeNode:
        double visits

        QTreeNode(double visits)
        bint isLeaf()
        vector[double]* getQS(State*)
        void update(State* s, Action* a, int target, unordered_map[string, double]* params)
        void noVisitUpdate(unordered_map[string, double]* params)
        QTreeNode* split(State*, vector[double]*, vector[double]*, unordered_map[string, double]*)
        double maxSplitUtil(State*)
        int numNodes()
        void printStructure(string, string)

cdef extern from "../../include/qtree.hpp":
    cdef cppclass QTree:
        double splitThreshMax
        double splitThreshDecay
        int numSplits 
        QTreeNode* root
        bint _justSplit
        unordered_map[string, double]* params

        QTree(Box*, Discrete*, QTreeNode*, double, double, double, double, double, int)
        void destroyEverything()
        int selectA(State*)
        void takeTuple(State*, Action*, double, State*, bint)
        void update(State*, Action*, double, State*, bint)
        int numNodes()
        void printStructure()
        bint justSplit()
        bint saveToFile(string)
        bint setRootFromFile(string)
        void infoWeightAnalysis(string)
        vector[double] explain_classic(int, vector[double], bint)
        vector[double] explain_useraware(int, int, vector[double], bint)
        double getAverageDepth()

cdef class PyVector:
    cdef vector[double]* thisptr

    def __cinit__(self):
        self.thisptr = new vector[double]()
    def add(self, double f):
        self.thisptr.push_back(f)

cdef class PyBox:
    cdef Box* thisptr

    def __cinit__(self, PyVector low, PyVector high):
        self.thisptr = new Box(low.thisptr, high.thisptr)
    def contains(self, PyVector vec):
        return self.thisptr.contains(vec.thisptr)

cdef class PyDiscrete:
    cdef Discrete* thisptr

    def __cinit__(self, int n):
        self.thisptr = new Discrete(n)
    def sample(self):
        return self.thisptr.sample()
    def size(self):
        return self.thisptr.size()
    def contains(self, int x):
        return self.thisptr.contains(x)

cdef class PyState:
    cdef State* thisptr

    def __cinit__(self, PyVector state):
        self.thisptr = new State(state.thisptr)

cdef class PyAction:
    cdef Action* thisptr

    def __cinit__(self, int value):
        self.thisptr = new Action(value)

cdef class PyQTree:
    cdef QTree* thisptr

    def __cinit__(self, PyBox state_space, PyDiscrete action_space, None, double \
        gamma, double alpha, double visit_decay, double split_thresh_max, double \
        split_thresh_decay, int num_splits):
        self.thisptr = new QTree(state_space.thisptr, action_space.thisptr, NULL, \
        gamma, alpha, visit_decay, split_thresh_max, split_thresh_decay, num_splits)
    def __dealloc__(self):
        # self.thisptr.destroyEverything()
        del self.thisptr
    def select_a(self, PyState s):
        return self.thisptr.selectA(s.thisptr)
    def take_tuple(self, PyState s, PyAction a, double r, PyState s2, bint done):
        return self.thisptr.takeTuple(s.thisptr, a.thisptr, r, s2.thisptr, done)
    def update(self, PyState s, PyAction a, double r, PyState s2, bint done):
        return self.thisptr.update(s.thisptr, a.thisptr, r, s2.thisptr, done)
    def num_nodes(self):
        return self.thisptr.numNodes()
    def print_structure(self):
        return self.thisptr.printStructure()
    def just_split(self):
        return self.thisptr.justSplit()
    def save_to_file(self, string path):
        return self.thisptr.saveToFile(path)
    def set_root_from_file(self, string path):
        return self.thisptr.setRootFromFile(path)
    def info_weight_analysis(self, string path):
        return self.thisptr.infoWeightAnalysis(path)
    def explain_classic(self, int action, vector[double] state, bint usingHigherNodes):
        return self.thisptr.explain_classic(action, state, usingHigherNodes)
    def explain_useraware(self, int user_action, int action, vector[double] state, bint usingHigherNodes):
        return self.thisptr.explain_useraware(user_action, action, state, usingHigherNodes)
    def get_average_depth(self):
        return self.thisptr.getAverageDepth()
