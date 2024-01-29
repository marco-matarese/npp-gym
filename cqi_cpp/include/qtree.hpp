#include "qfunc.hpp"

#include <string>
#include <iostream>
#include <fstream>
#include <vector>
#include <sstream>
#include <stack>
#include <utility>
#include <tuple>

using std::ofstream;
using std::ifstream;

using namespace std;

struct infoNode {
    QTreeNode* node;
    string direction;   // left - right
};



class QTree: public QFunc {
    public:
        double splitThreshMax, splitThreshDecay, splitThresh; 
        QTreeNode* root;
        bool _justSplit;
        unordered_map<string, double>* params;
        vector<tuple<int, string, double>> alreadyExplained[12];

        QTree(Box*, Discrete*, QTreeNode*, double, double, double, double, double, int);
        ~QTree();
        void destroyEverything();
        void deallocateDT(QTreeNode* node);
        int selectA(State*);
        void takeTuple(State*, Action*, double, State*, bool);
        void update(State*, Action*, double, State*, bool);
        int numNodes();
        void printStructure();
        bool justSplit();
        bool saveToFile(string path);
        void saveToFileRecursive(ofstream &outdata, QTreeNode* node);
        bool setRootFromFile(string path);
        QTreeNode* setRootFromFileRecursive(ifstream &indata);
        void infoWeightAnalysis(string path);
        vector<double> explain_useraware(int user_action, int action, vector<double> state, bool usingHigherNodes);
        vector<QTreeNode*> findUserActionLeafs(int user_action);
        void findUserActionLeafsRecursive(QTreeNode* parent, int user_action, vector<QTreeNode*>& curr_user_actions);
        int computeLeafToLeafDistance(QTreeNode* icubAction, QTreeNode* userAction, infoNode lowestCommonAncestor);
        infoNode getLowestCommonAncestor(QTreeNode* root, QTreeNode* node1, QTreeNode* node2);
        int distanceBetweenNodes(QTreeNode* ancestor, QTreeNode* node, int distance);
        vector<double> explain_classic(int action, vector<double> state, bool usingHigherNodes);
        void addTupleToAlreadyExplained(int action, double feature, double direction, double value);
        vector<infoNode> deleteFeaturesAlreadyExplained(int action, vector<infoNode> visited);
        vector<infoNode> deleteUselessInfoNodes(vector<infoNode> visited, bool usingHigherNodes);
        double getAverageDepth();
        void recursiveDepth(QTreeNode* parent, int& parentDepth, int& accumulateDepth, int& nodeCount);
};
