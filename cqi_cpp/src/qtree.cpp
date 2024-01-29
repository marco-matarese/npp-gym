#include "../include/qtree.hpp"
#include <algorithm>

typedef unordered_map<string, double> map;


/*
    UTIL FUNCTIONS
*/


bool compareOnlyTheDistances(pair<QTreeLeaf*, int> one, pair<QTreeLeaf*, int> two) {
    return one.second < two.second;
}


/*
    CLASS FUNCTIONS
*/


QTree::QTree(Box* stateSpace, Discrete* actionSpace, QTreeNode* root=nullptr, 
    double gamma=0.99, double alpha=0.1, double visitDecay=0.99, double splitThreshMax=1, double 
    splitThreshDecay=0.99, int numSplits=2) : QFunc(stateSpace, actionSpace) {
   
    if (!root) {
        vector<double>* low = this->stateSpace->low;
        vector<double>* high = this->stateSpace->high;
        vector<LeafSplit*>* splits = new vector<LeafSplit*>(); 

        for (size_t f = 0; f < low->size(); f++) {
            for (int i = 0; i < numSplits; i++) {
                vector<double>* zerosVector = Utils::zeros(actionSpace->size());
                int value = low->at(f) + (high->at(f) - low->at(f))/(numSplits + 1) * (i + 1);
                LeafSplit* toAdd = new LeafSplit(f, value, zerosVector, zerosVector, 0.5, 0.5);
                
                splits->push_back(toAdd);
            }
        }

        this->root = new QTreeLeaf(Utils::zeros(actionSpace->size()), 1, splits);
    } else {
        this->root = root;
    }

    this->params = new map();
    this->params->insert(map::value_type("gamma", gamma));
    this->params->insert(map::value_type("alpha", alpha));
    this->params->insert(map::value_type("visitDecay", visitDecay));
    this->params->insert(map::value_type("numSplits", numSplits));
    
    this->splitThreshMax = splitThreshMax;
    this->splitThreshDecay = splitThreshDecay;
    this->splitThresh = this->splitThreshMax;
    this->_justSplit = false;  // True if the most recent action resulted in a split
}

QTree::~QTree() {
    this->destroyEverything();
}

void QTree::destroyEverything() {
    delete this->params;
    for(auto x : alreadyExplained) {
        x.clear();
    }

    deallocateDT(this->root);
}

void QTree::deallocateDT(QTreeNode* node) {
    if(node == nullptr) return;
    if(node->isLeaf()) {
        QTreeLeaf* curr = dynamic_cast<QTreeLeaf*>(node);
        delete curr;
    }
    else {
        QTreeInternal* curr = dynamic_cast<QTreeInternal*>(node);
        deallocateDT(curr->leftChild);
        deallocateDT(curr->rightChild);
        delete curr;
    }
}


int QTree::selectA(State* s) {
    return Utils::argmax(this->root->getQS(s));
}

void QTree::takeTuple(State* s, Action* a, double r, State* s2, bool done) {
    this->_justSplit = false;
    this->selfCopy = NULL;

	// update a leaf directly
    this->update(s, a, r, s2, done);
	
    // modify tree
    if (this->root->maxSplitUtil(s) > this->splitThresh) {
        //printf("split\n");

        this->_justSplit = true;

        if (this->makeCopies) {
            this->selfCopy = new QTree(this->stateSpace, this->actionSpace, 
                this->root, this->params->at("gamma"), this->params->at("alpha"), 
                this->params->at("visitDecay"), this->splitThreshMax, 
                this->splitThreshDecay, this->params->at("numSplits"));
        }

        this->root = this->root->split(s, this->stateSpace->low, this->stateSpace->high, this->params);
        this->splitThresh = this->splitThreshMax;
    } else {
        this->splitThresh = this->splitThresh * this->splitThreshDecay;
    }
}

void QTree::update(State* s, Action* a, double r, State* s2, bool done) {
    double target = 0;

    if (done) {
        target = r;
    } else {
        vector<double>* QVals = this->root->getQS(s2);
        double QValsMax = Utils::max(QVals);

        target = r + this->params->at("gamma") * QValsMax;
    }

    this->root->update(s, a, target, this->params);
}

int QTree::numNodes() {
    return this->root->numNodes();
}

void QTree::printStructure() {
    this->root->printStructure("└", " ");
}
        
bool QTree::justSplit() {
    return this->_justSplit;
}

bool QTree::saveToFile(string path) {
    ofstream outdata;
    outdata.open(path,  ios::out | ios::binary);
    saveToFileRecursive(outdata, root);
    outdata.close();
    return true;
}

void QTree::saveToFileRecursive(ofstream &outdata, QTreeNode* n) {
    vector<double>* qs;
    double visits;
    int feature;
    double value;
    bool hasLeftChild;
    bool hasRightChild;

    // retrieve info in common
    visits = n->visits;

    if(n->isLeaf()) {
        QTreeLeaf *node = dynamic_cast<QTreeLeaf*>(n);

        // retrieve leaf info
        hasLeftChild = false;
        hasRightChild = false;
        qs = node->qs;

        // write info
        outdata << "leaf " << "visits " << visits << " qs ";
        for(double q : *qs) {
            outdata << q << " ";
        }
        outdata << endl;
    }
    else {
        QTreeInternal *node = dynamic_cast<QTreeInternal*>(n);

        // retrieve internal info
        feature = node->feature;
        value = node->value;
        if(node->leftChild->numNodes() > 0) {
            hasLeftChild = true;
        }
        else {
            hasLeftChild = false;
        }
        if(node->rightChild->numNodes() > 0) {
            hasRightChild = true;
        }
        else {
            hasRightChild = false;
        }

        // write info
        outdata << "internal " << "visits " << visits << " feature " << feature << " value " << value << " hasLeftChild " << hasLeftChild <<
        " hasRightChild " << hasRightChild << endl;
    }

    if(! n->isLeaf()) {
        QTreeInternal *node = dynamic_cast<QTreeInternal*>(n);

        // recursive calls (pre-order)
        if(hasLeftChild) {
            saveToFileRecursive(outdata, node->leftChild);
        }
        if(hasRightChild) {
            saveToFileRecursive(outdata, node->rightChild);
        }
    }

}

bool QTree::setRootFromFile(string path) {
    ifstream indata;
    indata.open(path);
    root = setRootFromFileRecursive(indata);
    indata.close();
    return true;
}

QTreeNode* QTree::setRootFromFileRecursive(ifstream& indata) {
    // read line from file
    string line;
    getline(indata, line);

    // split line by space
    stringstream ss(line);
    vector<string> splitLine;
    string s;
    while(getline(ss, s, ' ')) {
        splitLine.push_back(s);
    }

    double visits = stod(splitLine[2]);
    //cout << splitLine[2] << " " << visits << endl;
    //QTreeNode* node = nullptr;

    if(splitLine[0] == "internal") {
        // retrieve internal info and create internal node
        int feature = stoi(splitLine[4]);
        double value = stod(splitLine[6]);
        QTreeInternal* node = new QTreeInternal(nullptr, nullptr, feature, value, visits);

        //cout << splitLine[0] << " visits " << visits << " feature " << feature << " value " << value << endl;

        // recursive calls
        if(splitLine[8] == "1") {
            node->leftChild = setRootFromFileRecursive(indata);
        }
        else {
            node->leftChild = nullptr;
        }
        if(splitLine[10] == "1") {
            node->rightChild = setRootFromFileRecursive(indata);
        }
        else {
            node->rightChild = nullptr;
        }

        return node;
    }
    else {
        // retrieve leaf info and create leaf
        vector<double>* qs = new vector<double>();
        auto first = splitLine.begin() + 4;
        auto last = splitLine.end();
        vector<string> qsValues(first, last);
        for(string qVal : qsValues) {
            qs->push_back(stod(qVal));
        }
        QTreeLeaf* node = new QTreeLeaf(qs, visits, nullptr);

        /*
        cout << splitLine[0] << " visits " << visits << " qs ";
        for(double q : *qs) {
            cout << q << " ";
        }
        cout << endl;
        */

        return node;
    }
}

void QTree::infoWeightAnalysis(string path) {
    ofstream outdata;
    outdata.open(path);
    std::stack<infoNode> stack;
    std::stack<infoNode> visitStack;
    QTreeNode* curr = this->root;
    string lastDirection;

    while(!stack.empty() || curr != nullptr) {
        if(curr != nullptr) {

            // visit leaf
            if(curr->isLeaf()) {
                //QTreeLeaf* leaf = dynamic_cast<QTreeLeaf*>(curr);

                if(visitStack.empty()) {
                    visitStack = stack;
                }

                vector<pair<double, string>> infoArray[8];
                while(!visitStack.empty()) {
                    infoNode info = visitStack.top();
                    visitStack.pop();
                    int feature;
                    double value;

                    if(!info.node->isLeaf()) {
                        feature = dynamic_cast<QTreeInternal*>(info.node)->feature;
                        value = dynamic_cast<QTreeInternal*>(info.node)->value;
                    }

                    string dir = lastDirection;
                    pair<double, string> couple = pair<double, string>(value, dir);
                    infoArray[feature].insert(infoArray[feature].end(), couple);
                }

                for(int index = 0; index < 8; index++) {
                    if(infoArray[index].size() > 1) {
                        for(uint i = 0; i < infoArray[index].size(); i++) {
                            for(uint j = 0; j < infoArray[index].size(); j++) {
                                if(i != j) {
                                    pair<double, string> currInfo_1 = infoArray[index][i];
                                    pair<double, string> currInfo_2 = infoArray[index][j];
                                    if(currInfo_1.second == currInfo_2.second) {
                                        outdata << "feature " << index << " direction " << currInfo_1.second << " value 1 " <<
                                        currInfo_1.first << " value 2 " << currInfo_2.first << endl;
                                    }
                                }
                            }
                        }
                    }
                }
            }

            infoNode info = {curr, lastDirection};
            stack.push(info);
            if(curr->isLeaf()) {
                curr = nullptr;
            }
            else {
                QTreeInternal* tmpInternal = dynamic_cast<QTreeInternal*>(curr);
                QTreeNode* tmpNode = tmpInternal->leftChild;
                curr = tmpNode;
                lastDirection = "left";
            }
        }
        else {
            visitStack = stack;
            infoNode info = stack.top();
            curr = info.node;
            stack.pop();
            if(curr->isLeaf()) {
                curr = nullptr;
            }
            else {
                QTreeInternal* tmpInternal = dynamic_cast<QTreeInternal*>(curr);
                QTreeNode* tmpNode = tmpInternal->rightChild;
                curr = tmpNode;
                lastDirection = "right";
            }
        }
    }
}

std::vector<double> QTree::explain_useraware(int userAction, int action, std::vector<double> state, bool usingHigherNodes) {

    // find icub_action leaf: just a tree descent
    QTreeNode* icubAction = this->root;
    while(! icubAction->isLeaf()) {
        QTreeInternal* curr = dynamic_cast<QTreeInternal*>(icubAction);
        int feature = curr->feature;
        double value = curr->value;

        QTreeNode* tmp = nullptr;
        // here I don't need to check whether curr's children are nullptr
        if(state[feature] <= value) {
            icubAction = curr->leftChild;
        }
        else {
            icubAction = curr->rightChild;
        }
    }

    // now icubAction is leaf
    icubAction = dynamic_cast<QTreeLeaf*>(icubAction);

    // find all the k user_action leafs
    vector<QTreeNode*> userActions = findUserActionLeafs(userAction);

    // compute the leaf-to-leaf distance between the icub_action and the k user_actions
    vector<pair<QTreeLeaf*, int>> userActionsDistances;
    vector<pair<QTreeNode*, infoNode>> userActionsAncestors;
    for(QTreeNode* userAction : userActions) {
        infoNode currLowestCommonAncestor = getLowestCommonAncestor(this->root, icubAction, userAction);
        //cout << "common ancestor found" << endl;
        int currDist = computeLeafToLeafDistance(icubAction, userAction, currLowestCommonAncestor);
        //cout << "leaf to leaf distance computed" << endl;
        QTreeLeaf* currLeaf = dynamic_cast<QTreeLeaf*>(userAction);
        userActionsDistances.insert(userActionsDistances.end(), pair<QTreeLeaf*, int>(currLeaf, currDist));
        userActionsAncestors.insert(userActionsAncestors.end(), pair<QTreeNode*, infoNode>(userAction, currLowestCommonAncestor));
    }

    //cout << "ancestors found" << endl;

    // sort userActionsDistances by distance
    sort(userActionsDistances.begin(), userActionsDistances.end(), compareOnlyTheDistances);

    /*
    for(pair<QTreeNode*, infoNode> x : userActionsAncestors) {
        cout << x.first->visits << " ";
    }
    cout << endl;

    for(pair<QTreeLeaf*, int> x : userActionsDistances) {
        cout << x.first->visits << " " << x.second << endl;
    }
    */

    //cout << "distances sorted" << endl;

    // get the userAction = explanation's foil
    QTreeLeaf* userActionFoil = nullptr;
    if (userActionsDistances.front().second == 0) {
        // sometimes happens that one of the nodes is returned as ancestor
        userActionFoil = userActionsDistances.at(1).first;
    }
    else {
        userActionFoil = userActionsDistances.front().first;
    }

    // find the userActionFoil's ancestor: it is in userActionsAncestors
    // get the counterfactual internal node for fact and foil
    infoNode lowestCommonAncestorInfo;
    for(auto ancestorPair : userActionsAncestors) {
        QTreeNode* currUserAction = ancestorPair.first;
        if(currUserAction == userActionFoil) {
            lowestCommonAncestorInfo = ancestorPair.second;
            break;
        }
    }

    //cout << "user action ancestor found" << endl;
    //cout << lowestCommonAncestorInfo.node->visits << " " << lowestCommonAncestorInfo.direction << endl;

    // packing info for returning
    infoNode explanationInfo = lowestCommonAncestorInfo;
    QTreeInternal* explanationNode = dynamic_cast<QTreeInternal*>(explanationInfo.node);
    if (explanationNode == nullptr)
        cout << "bad cast on explanationNode" << endl;
    double feature = (double) explanationNode->feature;
    double value = explanationNode->value;
    double direction = -1.0;                                    // left
    if(explanationInfo.direction == "right") direction = 1.0;   // right
    vector<double> result = {feature, direction, value};
    // addTupleToAlreadyExplained(action, feature, direction, value);
    return result;
}


std::vector<QTreeNode*> QTree::findUserActionLeafs(int userAction) {
    vector<QTreeNode*> userActions;
    findUserActionLeafsRecursive(this->root, userAction, userActions);
    return userActions;
}

void QTree::findUserActionLeafsRecursive(QTreeNode* parent, int userAction, vector<QTreeNode*>& currUserActions) {

    if (parent == nullptr) {
        return;
    }

    if (parent->isLeaf()) {
        // once on a leaf, if it represents the user's action, then save it
        QTreeLeaf* currLeaf = dynamic_cast<QTreeLeaf*>(parent);
        int currAction = static_cast<int>(distance(currLeaf->qs->begin(), max_element(currLeaf->qs->begin(), currLeaf->qs->end())));

        // if the leaf is one of the k user actions, then save it
        if(currAction == userAction) {
            currUserActions.push_back(currLeaf);
        }
    }
    else {
        // in-order tree visit
        QTreeInternal* curr = dynamic_cast<QTreeInternal*>(parent);
        findUserActionLeafsRecursive(curr->leftChild, userAction, currUserActions);
        findUserActionLeafsRecursive(curr->rightChild, userAction, currUserActions);
    }
}


int QTree::computeLeafToLeafDistance(QTreeNode* icubAction, QTreeNode* userAction, infoNode lowestCommonAncestor) {
    // lowestCommonAncestor = getLowestCommonAncestor(this->root, icubAction, userAction);
    int dist1 = distanceBetweenNodes(lowestCommonAncestor.node, icubAction, 0);
    int dist2 = distanceBetweenNodes(lowestCommonAncestor.node, userAction, 0);
    return dist1 + dist2;
}

infoNode QTree::getLowestCommonAncestor(QTreeNode* root, QTreeNode* node1, QTreeNode* node2) {
    // I assume that node1 = iCubAction and node2 = userAction

    string direction;
    //root->isLeaf() ||
    if (root == nullptr || root == node1 || root == node2) {
        if (root == node1) {
            direction = "left";
        }
        else if (root == node2) {
            direction = "right";
        }
        infoNode resultInfo = {root, direction};
        return resultInfo;
    }

    if (root->isLeaf() && root != node1 && root != node2) {
        infoNode resultInfo = {nullptr, ""};
        return resultInfo;
    }

    QTreeInternal* rootInternal = new QTreeInternal();
    rootInternal = dynamic_cast<QTreeInternal*>(root);

    infoNode left = getLowestCommonAncestor(rootInternal->leftChild, node1, node2);
    infoNode right = getLowestCommonAncestor(rootInternal->rightChild, node1, node2);

    /*
    if (left.node != nullptr && right.node != nullptr) {
        QTreeNode* ret = nullptr;
        if (left.node == node1) {
            direction = "left";
            ret = root;
        }
        else if (right.node == node2) {
            direction = "right";
            ret = root;
        }

        infoNode resultInfo = {root, direction};
        return resultInfo;
    }
    */
    if (left.node == nullptr) {
        return right;
    }
    else if (right.node == nullptr) {
        return left;
    }
    else {
        if (left.node == node1)
            direction = "left";
        else
            direction = "right";
        infoNode resultInfo = {root, direction};
        return resultInfo;
    }
}

int QTree::distanceBetweenNodes(QTreeNode* ancestor, QTreeNode* node, int distance) {

    if (ancestor == node) {
        return distance;
    }
    if (ancestor == nullptr || ancestor->isLeaf()) {
        return -1;
    }


    QTreeInternal* ancestorInternal = new QTreeInternal();
    ancestorInternal = dynamic_cast<QTreeInternal*>(ancestor);

    int leftDistance = distanceBetweenNodes(ancestorInternal->leftChild, node, distance + 1);
    if (leftDistance == -1) {
        return distanceBetweenNodes(ancestorInternal->rightChild, node, distance + 1);
    }
    // else...
    return leftDistance;
}


std::vector<double> QTree::explain_classic(int action, std::vector<double> state, bool usingHigherNodes) {
    vector<infoNode> visited;
    QTreeNode* curr = this->root;

    // descent the tree until the robot's action
    // in the meanwhile, collect the candidate explanations
    while(! curr->isLeaf()) {
        QTreeInternal* currInternal = dynamic_cast<QTreeInternal*>(curr);
        int feature = currInternal->feature;
        double value = currInternal->value;

        infoNode currInfo;
        currInfo.node = currInternal;

        QTreeNode* tmp = nullptr;
        if(state[feature] <= value) {
            tmp = currInternal->leftChild;
            //currInfo.node = curr;
            currInfo.direction = "left";
        }
        else {
            tmp = currInternal->rightChild;
            //currInfo.node = curr;
            currInfo.direction = "right";
        }
        curr = tmp;

        if(usingHigherNodes) {
            visited.insert(visited.end(), currInfo);
        }
        else {
            visited.insert(visited.begin(), currInfo);
        }
    }
    //visited.erase(visited.end());

    // TODO: should I ensure only one explanation per feature, the most refined one?
    visited = deleteFeaturesAlreadyExplained(action, visited);

    infoNode explanationInfo = visited.front();
    QTreeInternal* explanationNode = dynamic_cast<QTreeInternal*>(explanationInfo.node);
    double feature = (double) explanationNode->feature;
    double value = explanationNode->value;
    double direction = -1.0;                                    // left
    if(explanationInfo.direction == "right") direction = 1.0;   // right

    vector<double> result = {feature, direction, value};

    addTupleToAlreadyExplained(action, feature, direction, value);

    return result;
}


vector<infoNode> QTree::deleteUselessInfoNodes(vector<infoNode> visited, bool usingHigherNodes) {

    for(uint i = 0; i < visited.size(); i++) {
        QTreeInternal* currI = dynamic_cast<QTreeInternal*>(visited[i].node);
        int featureI = currI->feature;
        double valueI = currI->value;
        string directionI = visited[i].direction;

        for(uint j = i + 1; j < visited.size(); j++) {
            QTreeInternal* currJ = dynamic_cast<QTreeInternal*>(visited[j].node);
            int featureJ = currJ->feature;
            double valueJ = currJ->value;
            string directionJ = visited[j].direction;
            bool sameFeature = featureI == featureJ;
            bool sameDirection = directionI == directionJ;

            if(usingHigherNodes) {
                if((directionI == "left" && (sameFeature && sameDirection && valueI <= valueJ)) ||
                // if the direction is left and the deeper value is equal or greater than the higher value OR...
                (directionI == "right" && (sameFeature && sameDirection && valueI >= valueJ))) {
                // if the direction is right and the deeper value is equal or smaller than the higher value

                    visited.erase(visited.begin() + j);
                    j--;
                }
            }
            else {
                // the other way round if not usingHigherNodes
                if((directionI == "left" && (sameFeature && sameDirection && valueI >= valueJ)) ||
                (directionI == "right" && (sameFeature && sameDirection && valueI <= valueJ))) {

                    visited.erase(visited.begin() + j);
                    j--;
                }
            }
        }
    }

    return visited;
}

vector<infoNode> QTree::deleteFeaturesAlreadyExplained(int action, vector<infoNode> visited) {

    vector<infoNode> safeCopy = vector<infoNode>(visited);
    vector<tuple<int, string, double>>* currAlreadyExplained =
    new vector<tuple<int, string, double>>(this->alreadyExplained[action]);
    //tuple<int, string, double> atLeastOneExplanation = currAlreadyExplained.front();
    //infoNode atLeastOneExplanation = {visited.front().node, visited.front().direction};

    for(auto x : *currAlreadyExplained) {
        int alreadyExplainedFeature = get<0>(x);
        string alreadyExplainedDirection = get<1>(x);
        double alreadyExplainedValue = get<2>(x);

        for(uint i = 0; i < visited.size(); i++) {
            QTreeInternal* node = dynamic_cast<QTreeInternal*>(visited[i].node);
            int visitedFeature = node->feature;
            string visitedDirection = visited[i].direction;
            double visitedValue = node->value;

            if(alreadyExplainedFeature == visitedFeature &&
            alreadyExplainedDirection == visitedDirection &&
            alreadyExplainedValue == visitedValue) {
                visited.erase(visited.begin() + i);
            }
        }
    }

    if(visited.empty()) {
        // when all the explanations have been given, redo from the beginning
        visited = safeCopy;
        this->alreadyExplained[action].clear();
    }

    return visited;
}


void QTree::addTupleToAlreadyExplained(int action, double feature, double direction, double value) {

    string directionStr = direction == -1.0 ? "left" : "right";
    tuple<int, string, double> curr = {(int)feature, directionStr, value};

    //if(find(this->alreadyExplained[action].begin(), this->alreadyExplained[action].end(), curr) ==
    //this->alreadyExplained[action].end()) {
        // alreadyExplained[action] doesn't contain curr: to insert
    this->alreadyExplained[action].insert(this->alreadyExplained[action].end(), curr);
    //}
}

double QTree::getAverageDepth() {
    int parentDepth = 0;
    int accumulateDepth = 0;
    int nodeCount = 0;
    recursiveDepth(this->root, parentDepth, accumulateDepth, nodeCount);
    return accumulateDepth / nodeCount;
}

void QTree::recursiveDepth(QTreeNode* parent, int& parentDepth, int& accumulateDepth, int& nodeCount) {
    if(! parent->isLeaf()) {
        QTreeInternal* curr = dynamic_cast<QTreeInternal*>(parent);
        parentDepth += 1;
        nodeCount += 1;
        accumulateDepth += parentDepth;
        recursiveDepth(curr->leftChild, parentDepth, accumulateDepth, nodeCount);
        recursiveDepth(curr->rightChild, parentDepth, accumulateDepth, nodeCount);
    }
}