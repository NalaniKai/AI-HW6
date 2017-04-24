import random
import random
import sys
import math
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))  # nopep8
from Player import Player
import Constants as c
from Construction import CONSTR_STATS, Construction
from Ant import UNIT_STATS, Ant
from Move import Move
from GameState import addCoords, subtractCoords, GameState
import AIPlayerUtils as utils
import unittest
from Location import Location 
from Inventory import Inventory
from Building import Building
import json

class AIPlayer(Player):
    """
    Description:
        The responsibility of this class is to interact with the game
        by deciding a valid move based on a given game state. This class has
        methods that will be implemented by students in Dr. Nuxoll's AI course.

    Variables:
        playerId - The id of the player.
    """

    def __init__(self, inputPlayerId):
        """
        Creates a new Player

        Parameters:
            inputPlayerId - The id to give the new player (int)
        """
        super(AIPlayer, self).__init__(inputPlayerId, "Fluffy")
        self.alpha = .99    #for TD learning
        self.gamma = .15    #for TD learning
        self.conCurrentState = None #consolidated state to add to last ten states seen
        self.stateDict = None   #dictionary of past consolidated states seen
        with open('..\chunm18_linds17.json', 'r') as file:
            try:
                self.stateDict = json.load(file)
                print len(self.stateDict)
            except ValueError:
                self.stateDict = dict()
        self.pastTen = []           #last ten states seen (consolidated)
        self.PASTLIM = 10           #only look at last 10 states
        self.dLim = 3               #depth limit
        self.searchMult = 2.5       #generate search limits for depths
        self.searchLim = []         #search limit size control
        for i in range(self.dLim+1):
            self.searchLim.append((i)*self.searchMult)
            

    #@staticmethod
    def score_state(self, state):
        """
        score_state: Compute a 'goodness' score of a given state for the current player.
        The score is computed by tallying up a total number of possible 'points',
        as well as a number of 'good' points.

        Various elements are weighted heavier than others, by providing more points.
        Some metrics, like food difference, is weighted by difference between the two
        players.

        Note: This is a staticmethod, it can be called without instanceing this class.

        Parameters:
            state - GameState to score.
        """
        enemy_id = 1 - self.playerId 
        our_inv = state.inventories[self.playerId]
        enemy_inv = [inv for inv in state.inventories if inv.player == enemy_id].pop()
        we_win = 1.0
        enemy_win = 0.0
        our_food = our_inv.foodCount
        enemy_food = enemy_inv.foodCount
        food_difference = abs(our_food - enemy_food)
        our_anthill = our_inv.getAnthill()
        our_tunnel = our_inv.getTunnels()
        food_drop_offs = []
        if len(our_tunnel) != 0:
            food_drop_offs.append(our_tunnel[0].coords)
        food_drop_offs.append(our_anthill.coords)
        enemy_anthill = enemy_inv.getAnthill()
        our_queen = our_inv.getQueen()
        enemy_queen = enemy_inv.getQueen()
        food = utils.getConstrList(state, None, (c.FOOD,))

        # Total points possible
        total_points = 1
        # Good points earned
        good_points = 0

        # Initial win condition checks:
        if (our_food == c.FOOD_GOAL or
            enemy_queen is None or
                enemy_anthill.captureHealth == 0):
            return we_win
        # Initial lose condition checks:
        if (enemy_food == c.FOOD_GOAL or
            our_queen is None or
                our_anthill.captureHealth == 0):
            return enemy_win

        # Score food
        total_points += (our_food + enemy_food) * 50  
        good_points += our_food * 50  

        # Differences over, say, 3 are weighted heavier
        if food_difference > 3:
            total_points += food_difference * 100  
            if our_food > enemy_food:
                good_points += food_difference * 100  

        # Carrying food is good
        food_move = 150
        our_workers = [ant for ant in our_inv.ants if ant.type == c.WORKER]

        # Food drop off points
        dropping_off = [
            ant for ant in our_workers if ant.coords in food_drop_offs and ant.carrying]

        # Depositing food is even better!
        if len(dropping_off) != 0:
            total_points += food_move * 80  
            good_points += food_move * 80  

        picking_up = [
            ant for ant in our_workers if ant.coords in food]

        if len(picking_up) != 0:
            total_points += food_move * 50  
            good_points += food_move * 50  

        # Worker movement
        for ant in our_workers:
            ant_x = ant.coords[0]
            ant_y = ant.coords[1]
            for enemy in enemy_inv.ants:
                if ((abs(ant_x - enemy.coords[0]) > 3) and
                        (abs(ant_y - enemy.coords[1]) > 3)):
                    good_points += 30 
                    total_points += 30  
            if ant.carrying and ant not in dropping_off:
                # Good if carrying ants move toward a drop off.
                total_points += food_move 
                good_points += food_move 

                for dist in range(2, 6):
                    for dropoff in food_drop_offs:
                        if ((abs(ant_x - dropoff[0]) < dist) and
                                (abs(ant_y - dropoff[1]) < dist)):
                            good_points += food_move - (dist * 25)
                            total_points += food_move - (dist * 25)
            else:
                if food != []:      
                    for f in food:  
                        x_dist = abs(ant_x - f.coords[0])
                        y_dist = abs(ant_y - f.coords[1]) 

                        # weighted more if closer to food
                        for dist in range(2, 7):
                            if x_dist < dist and y_dist < dist:
                                good_points += 70 - (dist * 10)
                                total_points += 70 - (dist * 10)

        if len(our_workers) < 3:
            good_points += 800
            total_points += 800

        # Raw ant numbers comparison
        total_points += (len(our_inv.ants) + len(enemy_inv.ants)) * 10  
        good_points += len(our_inv.ants) * 10  

        # Weighted ant types
        # Workers, first 3 are worth 10, the rest are penalized
        enemy_workers = [ant for ant in enemy_inv.ants if ant.type == c.WORKER]
        if len(our_workers) <= 3:
            total_points += len(our_workers) * 10  
            good_points += len(our_workers) * 10  
        else:
            return 0.001
        total_points += len(enemy_workers) * 50

        # prefer workers to not leave home range
        our_range = [(x, y) for x in xrange(10) for y in xrange(5)]
        if len([ant for ant in our_workers if ant.coords not in our_range]) != 0:
            return .001

        # Offensive ants
        # Let's just say each ant is worth 20x its cost for now
        offensive = [c.SOLDIER, c.R_SOLDIER, c.DRONE]
        our_offense = [ant for ant in our_inv.ants if ant.type in offensive]
        enemy_offense = [
            ant for ant in enemy_inv.ants if ant.type in offensive]

        for ant in our_offense:
            ant_x = ant.coords[0]
            ant_y = ant.coords[1]
            attack_move = 150  
            good_points += UNIT_STATS[ant.type][c.COST] * 20
            total_points += UNIT_STATS[ant.type][c.COST] * 20

            if ant.type == c.R_SOLDIER:
                good_points += 300
                total_points += 300

            if ant.type == c.DRONE:
                good_points -= UNIT_STATS[ant.type][c.COST] * 20
                total_points -= UNIT_STATS[ant.type][c.COST] * 20
            
            # good if on enemy anthill
            if ant.coords == enemy_anthill.coords:
                total_points += 100
                good_points += 100
            for enemy_ant in enemy_inv.ants:
                enemy_x = enemy_ant.coords[0]
                enemy_y = enemy_ant.coords[1]
                x_dist = abs(ant_x - enemy_x)
                y_dist = abs(ant_y - enemy_y)

                # good if attacker ant attacks
                if x_dist + y_dist == 1:
                    good_points += attack_move * 2
                    total_points += attack_move * 2

                # weighted more if closer to attacking
                for dist in xrange(1, 8):
                    if x_dist < dist and y_dist < dist:
                        good_points += attack_move - (dist * 20) 
                        total_points += attack_move - (dist * 20)

        for ant in enemy_offense:
            total_points += UNIT_STATS[ant.type][c.COST] * 60  

        # Stop building if we have more than 5 ants
        if len(our_inv.ants) > 5:
            return .001 

        # Queen stuff
        # Queen healths, big deal, each HP is worth 100!
        total_points += (our_queen.health + enemy_queen.health) * 100
        good_points += our_queen.health * 100
        queen_coords = our_queen.coords
        if queen_coords in food_drop_offs or queen_coords[1] > 2 or queen_coords in food:
            # Stay off food_drop_offs and away from the front lines.
            total_points += 80

        # queen attacks if under threat
        for enemy_ant in enemy_inv.ants:
            enemy_x = enemy_ant.coords[0]
            enemy_y = enemy_ant.coords[1]
            x_dist = abs(queen_coords[0] - enemy_x)
            y_dist = abs(queen_coords[1] - enemy_y)

            if (x_dist + y_dist) == 1:
                good_points += 100  
                total_points += 100 

        # Anthill stuff
        total_points += (our_anthill.captureHealth +
                         enemy_anthill.captureHealth) * 100  
        good_points += our_anthill.captureHealth * 100  

        return float(good_points) / float(total_points)

    def evaluate_nodes(self, nodes, agents_turn):
        """Evalute a list of Nodes and returns the best score."""
        if agents_turn:
            return max(nodes, key=lambda node: node.score)

        return min(nodes, key=lambda node: node.score)

    def getPlacement(self, currentState):
        """
        getPlacement:
            The getPlacement method corresponds to the
            action taken on setup phase 1 and setup phase 2 of the game.
            In setup phase 1, the AI player will be passed a copy of the
            state as current_state which contains the board, accessed via
            current_state.board. The player will then return a list of 11 tuple
            coordinates (from their side of the board) that represent Locations
            to place the anthill and 9 grass pieces. In setup phase 2, the
            player will again be passed the state and needs to return a list
            of 2 tuple coordinates (on their opponent's side of the board)
            which represent locations to place the food sources.
            This is all that is necessary to complete the setup phases.

        Parameters:
          current_state - The current state of the game at the time the Game is
              requesting a placement from the player.(GameState)

        Return: If setup phase 1: list of eleven 2-tuples of ints ->
                    [(x1,y1), (x2,y2),...,(x10,y10)]
                If setup phase 2: list of two 2-tuples of ints ->
                    [(x1,y1), (x2,y2)]
        """
        numToPlace = 0
        # implemented by students to return their next move
        if currentState.phase == c.SETUP_PHASE_1:  # stuff on my side
            numToPlace = 11
            moves = []
            for i in range(0, numToPlace):
                move = None
                while move is None:
                    # Choose any x location
                    x = random.randint(0, 9)
                    # Choose any y location on your side of the board
                    y = random.randint(0, 3)
                    # Set the move if this space is empty
                    if currentState.board[x][y].constr is None and (x, y) not in moves:
                        move = (x, y)
                        # Just need to make the space non-empty. So I threw
                        # whatever I felt like in there.
                        currentState.board[x][y].constr is True
                moves.append(move)
            return moves
        elif currentState.phase == c.SETUP_PHASE_2:  # stuff on foe's side
            numToPlace = 2
            moves = []
            for i in range(0, numToPlace):
                move = None
                while move is None:
                    # Choose any x location
                    x = random.randint(0, 9)
                    # Choose any y location on enemy side of the board
                    y = random.randint(6, 9)
                    # Set the move if this space is empty
                    if currentState.board[x][y].constr is None and (x, y) not in moves:
                        move = (x, y)
                        # Just need to make the space non-empty. So I threw
                        # whatever I felt like in there.
                        currentState.board[x][y].constr is True
                moves.append(move)
            return moves
        else:
            return [(0, 0)]

    def consolidateState(self, currentState):
        '''
        Description: Turns currentState into a consolidated state list

        Parameters:
            currentState - game state 

        Return:
            consolidated state
        '''
        #initialize with 0
        newState = []
        for x in range(0,22):
            newState.append(0)

        #variables to fill in consolidated state
        enemyId = 1 - self.playerId
        enemyInv = [inv for inv in currentState.inventories if inv.player == enemyId].pop()
        enemyAnts = enemyInv.ants
        ourInv = [inv for inv in currentState.inventories if inv.player == self.playerId].pop()
        attacker = [c.SOLDIER, c.DRONE, c.R_SOLDIER]
        ourAttackers = [ant for ant in ourInv.ants if ant.type in attacker]
        attackerNum = len(ourAttackers)
        ourWorkers = [ant for ant in ourInv.ants if ant.type == c.WORKER]
        workerNum = len(ourWorkers)
        ourQueen = ourInv.getQueen()
        queenHealth = 0
        if ourQueen != None:
            queenHealth = ourQueen.health
        ourHill = ourInv.getAnthill()
        ourTunnel = ourInv.getTunnels()
        ourFood = utils.getConstrList(currentState, self.playerId, (c.FOOD,))
        foodAmount = ourInv.foodCount
        foodDropOffs = []
        if len(ourTunnel) != 0:
            foodDropOffs.append(ourTunnel[0].coords)
        foodDropOffs.append(ourHill.coords)

        #bins for attacker ant distances from the enemy ants
        for ant in ourAttackers:
            x = ant.coords[0]
            y = ant.coords[1]
            for enemy in enemyAnts:
                dist = abs(x - enemy.coords[0]) - abs(y - enemy.coords[1])
                if dist <= 1:
                    newState[0] = newState[0] + 1
                elif dist == 2:
                    newState[1] = newState[1] + 1
                else:
                    newState[2] = newState[2] + 1

        #bins for worker ants and proximity to food or dropping off food
        for ant in ourWorkers:
            x = ant.coords[0]
            y = ant.coords[1]
            if ant.carrying:
                for struct in foodDropOffs:
                    dist = abs(x - struct[0]) - abs(y - struct[1])
                    if dist <= 2:
                        newState[3] = newState[3] + 1
                    elif dist <= 4:
                        newState[4] = newState[4] + 1
            else:
                for food in ourFood:
                    dist = abs(x - food.coords[0]) - abs(y - food.coords[1])
                    if dist <= 2:
                        newState[5] = newState[5] + 1
                    elif dist <= 4:
                        newState[6] = newState[6] + 1

        if ourQueen != None:
            if ourQueen.coords in foodDropOffs:
                newState[7] = 1

        #fill in consolidated state slots for food count and queen health
        self.populateNewFoodAndQueen(newState, foodAmount, 8)
        self.populateNewFoodAndQueen(newState, queenHealth, 11)

        #fill in consolidated state slots for worker ants and attacker ants 
        self.populateNewOurAnts(newState, workerNum, 14)
        self.populateNewOurAnts(newState, attackerNum, 18)

        #to track whose turn it is for minimax
        if currentState.whoseTurn == self.playerId:
            newState[21] = 1

        #convert to tuple so can use as key in dictionary 
        newState = tuple(newState)

        #update the utility of each state
        if newState in self.stateDict:
            self.stateDict[str(newState)] = self.stateDict[str(newState)]-.01
        else:
            self.stateDict[str(newState)] = -.01

        return newState

    def populateNewFoodAndQueen(self, newState, value, pos): 
        '''
        Description: Fills food count and queen health in the consolidated state list

        Parameters:
            newState - the consolidated state; list
            value - the comparison for filling the bins for the input
            pos - position to fill the consolidated state list  
        '''
        if value < 3:
            newState[pos] = newState[pos] + 1
        elif value < 6:
            newState[pos+1] = newState[pos+1] + 1
        else:
            newState[pos+2] = newState[pos+2] + 1

    def populateNewOurAnts(self, newState, value, pos):
        '''
        Description: Fills worker ant and attacker ant numbers in the consolidated state list

        Parameters:
            newState - the consolidated state; list
            value - the comparison for filling the bins for the input
            pos - position to fill the consolidated state list  
        '''
        if value <= 1:
            newState[pos] = newState[pos] + 1
        elif value <= 2:
            newState[pos+1] = newState[pos+1] + 1
        elif value <= 3:
            newState[pos+2] = newState[pos+2] + 1
        else:
            newState[pos+3] = newState[pos+3] + 1


    def getMove(self, currentState):
        """
        Description:
            Gets the next move from the Player.

        Parameters:
          current_state - The current state of the game at the time the Game is
              requesting a move from the player. (GameState)

        Return: Move(moveType [int],
                     coordList [list of 2-tuples of ints],
                     buildType [int])
        """
        node = Node(None, currentState)
        node.beta = -2
        node.alpha = 2
        move = self.expand(node, self.dLim, True, -2,2)
        if move is None:
            return Move(c.END, None, None)

        #past ten states 
        if self.conCurrentState != None:
            self.pastTen.insert(0, self.conCurrentState)
            if len(self.pastTen) > self.PASTLIM:
                self.pastTen.pop()

        #all states has a -.01 reward unless there is a win or lose
        self.updateUtility(-.01)
        return move

    def getAttack(self, currentState, attackingAnt, enemyLocations):
        """
        Description:
            Gets the attack to be made from the Player

        Parameters:
          current_state - The current state of the game at the time the
                Game is requesting a move from the player. (GameState)
          attackingAnt - A clone of the ant currently making the attack. (Ant)
          enemyLocation - A list of coordinate locations for valid attacks
            (i.e. enemies within range) ([list of 2-tuples of ints])

        Return: A coordinate that matches one of the entries of enemyLocations.
                ((int,int))
        """
        # Attack a random enemy.
        return enemyLocations[random.randint(0, len(enemyLocations) - 1)]

    def expand(self, node, depth, maxPlayer,a,b):
        '''
        Description: Recursive method that searches for the best move to optimize resulting state at given depth
        prunes moves and general search space to save time
        
        Parameters:
           state - current state of the game
           depth - starting depth for search
        
        Return: overall score of nodes if the depth is greater than 0
        else, when depth is 0, returns the best move
        '''

        # if depth = 0 or node is terminal return heuristic
        conState = self.consolidateState(node.nextState)
        if depth == 0:
            return self.stateDict[str(conState)]
        
        #get all possible moves for the current player
        moves = utils.listAllLegalMoves(node.nextState)

        #remove illegal moves
        badmoves = []
        ourInv = [inv for inv in node.nextState.inventories if inv.player == self.playerId].pop()
        ourWorkers = [ant for ant in ourInv.ants if ant.type == c.WORKER]
        for i in moves:
            if (i.moveType == c.BUILD and i.buildType == c.TUNNEL) or \
               (i.moveType == c.BUILD and i.buildType == c.WORKER and len(ourWorkers) > 5) or \
               (i.moveType == c.MOVE_ANT and not utils.isPathOkForQueen(i.coordList) and\
                utils.getAntAt(node.nextState, i.coordList[0]).type == c.WORKER):
                badmoves.append(i)
        for m in badmoves:
            moves.remove(m)
            
        # prune moves randomly
        random.shuffle(moves)
        moves = moves[0:(len(moves)*depth)/self.dLim]
        
        #generate a list of all next game states
        gameStates = []
        for m in moves:
            gameStates.append(self.getNextStateAdversarial(node.nextState,m))        

        conGameStates = []      #consolidated game states of possible next states
        childrentemp = []
        children = []
        for n in range(len(gameStates)):
            conGameStates.append(self.consolidateState(gameStates[n]))
            childrentemp.append([gameStates[n], Node(moves[n], gameStates[n], self.stateDict[str(conGameStates[n])], node)])

        childrentemp = sorted(childrentemp, key=lambda x: x[0])
        if self.playerId == conState[21]:
            childrentemp = reversed(childrentemp)
        for n in childrentemp:
            if len(children) >= self.searchLim[depth]:
                break
            children.append(n[1])

        random.shuffle(children)

        # if depth = 0 or node is terminal return heuristic
        if len(children) == 0:
            return self.stateDict[str(conState)]

        if maxPlayer: #agent
            node.score = -2
            for child in children:
                v = self.expand(child, depth - 1, conState[21] == self.playerId, a,b)
                self.stateDict[str(conState)] = max(v, self.stateDict[str(conState)])
                if self.stateDict[str(conState)] >= b:
                    if depth == self.dLim:
                        self.conCurrentState = self.consolidateState(child.nextState)
                        return child.move
                    return self.stateDict[str(conState)]
                a = max(a, child.score)
            if depth == self.dLim:
                n = self.evaluate_nodes(children, True)
                self.conCurrentState = self.consolidateState(n.nextState)
                return n.move
            return self.evaluate_nodes(children, True).score#node.score
        else: #opponent
            node.score = 2
            for child in children:
                v = self.expand(child, depth - 1, conState[21] == self.playerId,a,b)
                node.score = min(v, self.stateDict[str(conState)])
                if self.stateDict[str(conState)] <= a:
                    return self.stateDict[str(conState)]
                b = min(b, self.stateDict[str(conState)])
            return self.evaluate_nodes(children, False).score

    def getNextStateAdversarial(self, currentState, move):
        '''
        Version of getNextStateAdversarial that calls this class' getNextState

        Description: This is the same as getNextState (above) except that it properly
        updates the hasMoved property on ants and the END move is processed correctly.

        Parameters:
        currentState - A clone of the current state (GameState)
        move - The move that the agent would take (Move)
        Return: A clone of what the state would look like if the move was made
        '''

        # variables I will need
        nextState = self.getNextState(currentState, move)
        myInv = utils.getCurrPlayerInventory(nextState)
        myAnts = myInv.ants

        # If an ant is moved update their coordinates and has moved
        if move.moveType == c.MOVE_ANT:
            startingCoord = move.coordList[0]
            for ant in myAnts:
                if ant.coords == startingCoord:
                    ant.hasMoved = True
        elif move.moveType == c.END:
            for ant in myAnts:
                ant.hasMoved = False
            nextState.whoseTurn = 1 - currentState.whoseTurn;
        return nextState

    @staticmethod
    def getNextState(currentState, move):
        """
        Version of genNextState with food carrying bug fixed.

        Description: Creates a copy of the given state and modifies the inventories in
        it to reflect what they would look like after a given move.  For efficiency,
        only the inventories are modified and the board is set to None.  The original
        (given) state is not modified.

        Parameters:
        currentState - A clone of the current state (GameState)
        move - The move that the agent would take (Move)

        Return: A clone of what the state would look like if the move was made
        """

        # variables I will need
        myGameState = currentState.fastclone()
        myInv = utils.getCurrPlayerInventory(myGameState)
        me = myGameState.whoseTurn
        myAnts = myInv.ants

        # If enemy ant is on my anthill or tunnel update capture health
        myTunnels = myInv.getTunnels()
        myAntHill = myInv.getAnthill()
        for myTunnel in myTunnels:
            ant = utils.getAntAt(myGameState, myTunnel.coords)
            if ant is not None:
                opponentsAnts = myGameState.inventories[not me].ants
                if ant in opponentsAnts:
                    myTunnel.captureHealth -= 1
        if utils.getAntAt(myGameState, myAntHill.coords) is not None:
            ant = utils.getAntAt(myGameState, myAntHill.coords)
            opponentsAnts = myGameState.inventories[not me].ants
            if ant in opponentsAnts:
                myAntHill.captureHealth -= 1

        # If an ant is built update list of ants
        antTypes = [c.WORKER, c.DRONE, c.SOLDIER, c.R_SOLDIER]
        if move.moveType == c.BUILD:
            if move.buildType in antTypes:
                ant = Ant(myInv.getAnthill().coords, move.buildType, me)
                myInv.ants.append(ant)
                # Update food count depending on ant built
                if move.buildType == c.WORKER:
                    myInv.foodCount -= 1
                elif move.buildType == c.DRONE or move.buildType == c.R_SOLDIER:
                    myInv.foodCount -= 2
                elif move.buildType == c.SOLDIER:
                    myInv.foodCount -= 3

        # If a building is built update list of buildings and the update food
        # count
        if move.moveType == c.BUILD:
            if move.buildType == c.TUNNEL:
                building = Construction(move.coordList[0], move.buildType)
                myInv.constrs.append(building)
                myInv.foodCount -= 3

        # If an ant is moved update their coordinates and has moved
        if move.moveType == c.MOVE_ANT:
            newCoord = move.coordList[len(move.coordList) - 1]
            startingCoord = move.coordList[0]
            for ant in myAnts:
                if ant.coords == startingCoord:
                    ant.coords = newCoord
                    ant.hasMoved = False
                    # If an ant is carrying food and ends on the anthill or tunnel
                    # drop the food
                    if ant.carrying and ant.coords == myInv.getAnthill().coords:
                        myInv.foodCount += 1
                        # ant.carrying = False
                    for tunnels in myTunnels:
                        if ant.carrying and (ant.coords == tunnels.coords):
                            myInv.foodCount += 1
                            # ant.carrying = False
                    # If an ant doesn't have food and ends on the food grab
                    # food
                    if not ant.carrying:
                        foods = utils.getConstrList(
                            myGameState, None, (c.FOOD,))
                        for food in foods:
                            if food.coords == ant.coords:
                                ant.carrying = True                        
                    # If my ant is close to an enemy ant attack it
                    if ant.type == c.WORKER:
                        continue 
                    adjacentTiles = utils.listAdjacent(ant.coords)
                    for adj in adjacentTiles:
                        # If ant is adjacent my ant
                        if utils.getAntAt(myGameState, adj) is not None:
                            closeAnt = utils.getAntAt(myGameState, adj)
                            if closeAnt.player != me:  # if the ant is not me
                                closeAnt.health = closeAnt.health - \
                                    UNIT_STATS[ant.type][c.ATTACK]  # attack
                                # If an enemy is attacked and looses all its health remove it from the other players
                                # inventory
                                if closeAnt.health <= 0:
                                    enemyAnts = myGameState.inventories[
                                        not me].ants
                                    for enemy in enemyAnts:
                                        if closeAnt.coords == enemy.coords:
                                            myGameState.inventories[
                                                not me].ants.remove(enemy)
                                # If attacked an ant already don't attack any
                                # more
                                break
        return myGameState


    def registerWin(self, haswon):
        '''
        Description:    Gets called after the game is over. Performs echoing of updated utilities to 
                        the ten most recent states. The reward is 1 if the agent wins and -1 if the 
                        agent loses.

        Parameters:
            haswon - whether or not the agent has won, boolean
        '''
        if(haswon):
            self.updateUtility(1)
        else:
            self.updateUtility(-1)

        #Minimizes alpha value over time
        self.alpha = self.alpha * .95

        #Dumps dictionary of consoolidated + values to file
        with open('chunm18_linds17.json', 'w') as file:
            json.dump(self.stateDict, file)
            file.flush()

    def updateUtility(self, reward):
        '''
        Description: Updates the utility of the last ten states given a reward value

        Parameters: reward - the reward value of the given state in reference to win, loss, or neither
        '''

        #The score of the previous state, assumed 0 at first
        last = 0
        self.gamma = .15
        #Loops through past ten states and updates scores in dictionary based on TD algorithm
        for x in range(0, len(self.pastTen)):
            state = self.pastTen[len(self.pastTen) - (x + 1)]
            currentVal = self.stateDict[str(state)]            
            self.stateDict[str(state)] = currentVal + self.alpha * (reward + self.gamma * (last - currentVal))
            self.gamma = self.gamma * 1.2            
            last = self.stateDict[str(state)]
##
#class to represent node containing info for next state given a move
##
class Node:
    """
    Simple class for a search tree Node.

    Each Node requires a Move and a GameState. If a score is not
    provided, then one is calculated with AIPlayer.score_state().
    """
    def __init__(self, move = None, nextState = None, score = 0, parent = None, child = None):
        self.move = move;
        self.nextState = nextState
        self.score = score
        self.parent = parent
        self.child = child
        self.beta = None
        self.alpha = None