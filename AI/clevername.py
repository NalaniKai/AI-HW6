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
        super(AIPlayer, self).__init__(inputPlayerId, "Clever Name")

    @staticmethod
    def score_state(state):
        """
        Compute a 'goodness' score of a given state for the current player.
        The score is computed by tallying up a total number of possible 'points',
        as well as a number of 'good' points.

        Various elements are weighted heavier than others, by providing more points.
        Some metrics, like food difference, is weighted by difference between the two
        players.

        Note: This is a staticmethod, it can be called without instanceing this class.

        Parameters:
            state - GameState to score.
        """
        enemy_id = abs(state.whoseTurn - 1)
        our_inv = utils.getCurrPlayerInventory(state)
        enemy_inv = [
            inv for inv in state.inventories if inv.player == enemy_id].pop()
        we_win = 1.0
        enemy_win = 0.0
        our_food = our_inv.foodCount
        enemy_food = enemy_inv.foodCount
        food_difference = abs(our_food - enemy_food)
        our_anthill = our_inv.getAnthill()
        our_tunnel = our_inv.getTunnels()[0]
        enemy_anthill = enemy_inv.getAnthill()
        our_queen = our_inv.getQueen()
        enemy_queen = enemy_inv.getQueen()
        food_drop_offs = [our_tunnel.coords]
        food_drop_offs.append(our_anthill.coords)

        # Total points possible
        total_points = 1
        # Good points earned
        good_points = 0

        # enemy_id = abs(self.playerId - 1)

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
        total_points += (our_food + enemy_food) * 50  # 100
        good_points += our_food * 50  # 100
        # More points the greater the difference:
        # total_points += math.pow(5, abs(our_inv.foodCount - enemy_inv.foodCount))
        # if our_inv.foodCount > enemy_inv.foodCount:
        #     good_points += math.pow(5,
        #                             abs(our_inv.foodCount - enemy_inv.foodCount))
        # Differences over, say, 3 are weighted heavier
        if food_difference > 3:
            total_points += food_difference * 200  # 800
            if our_food > enemy_food:
                good_points += food_difference * 200  # 800

        # Carrying food is good
        # We don't really care about the enemy in this case,
        # so we'll just give ourselves a small bonus if we have food
        # dropping_off = []
        food_move = 100
        our_workers = [ant for ant in our_inv.ants if ant.type == c.WORKER]

        # Food drop off points
        dropping_off = [
            ant for ant in our_workers if ant.coords in food_drop_offs and ant.carrying]

        # Depositing food is even better!
        if len(dropping_off) != 0:
            total_points += food_move * 30  # 3000
            good_points += food_move * 30  # 3000
            # print dropping_off
            # Remove penalty for not carrying food

        # Worker movement
        for ant in our_workers:
            ant_x = ant.coords[0]
            ant_y = ant.coords[1]
            for enemy in enemy_inv.ants:
                if ((abs(ant_x - enemy.coords[0]) > 3) and
                        (abs(ant_y - enemy.coords[1]) > 3)):
                    good_points += 60  # 50
                    total_points += 60  # 50
            if ant.carrying and ant not in dropping_off:
                # Good if carrying ants move toward
                # a drop off.
                total_points += food_move  # 50
                good_points += food_move  # 50

                for dist in range(2, 4):
                    for dropoff in food_drop_offs:
                        if ((abs(ant_x - dropoff[0]) < dist) and
                                (abs(ant_y - dropoff[1]) < dist)):
                            good_points += food_move - (dist * 25)
                            total_points += food_move - (dist * 25)

        # Raw ant numbers comparison
        total_points += (len(our_inv.ants) + len(enemy_inv.ants)) * 10  # 30
        good_points += len(our_inv.ants) * 10  # 30

        # Weighted ant types
        # Workers, first 3 are worth 10, the rest are penalized
        enemy_workers = [ant for ant in enemy_inv.ants if ant.type == c.WORKER]
        if len(our_workers) <= 3:
            total_points += len(our_workers) * 10  # 20
            good_points += len(our_workers) * 10  # 20
        # elif len(our_workers) <= 4:
        #     total_points += (len(our_workers) - 3) * 100 + 60
        #     # total_points += math.pow((len(our_workers) - 3), 10) + 60
        #     good_points += 60
        else:
            # STOP IT
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
            attack_move = 160  # 3000
            good_points += UNIT_STATS[ant.type][c.COST] * 20
            total_points += UNIT_STATS[ant.type][c.COST] * 20
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
                        good_points += attack_move - (dist * 20)  # 350
                        total_points += attack_move - (dist * 20)

        for ant in enemy_offense:
            total_points += UNIT_STATS[ant.type][c.COST] * 60  # 120

        # Stop building if we have more than 5 ants
        if len(our_inv.ants) > 5:
            return .001

        # Queen stuff
        # Queen healths, big deal, each HP is worth 100!
        total_points += (our_queen.health + enemy_queen.health) * 100
        good_points += our_queen.health * 100
        queen_coords = our_queen.coords
        if queen_coords in food_drop_offs or queen_coords[1] > 2:
            # Stay off food_drop_offs and away from the front lines.
            return .001
            # total_points += 500000

        # queen attacks if under threat
        for enemy_ant in enemy_inv.ants:
            enemy_x = enemy_ant.coords[0]
            enemy_y = enemy_ant.coords[1]
            x_dist = abs(queen_coords[0] - enemy_x)
            y_dist = abs(queen_coords[1] - enemy_y)

            if (x_dist + y_dist) == 1:
                good_points += 200  # 600
                total_points += 200  # 600

        # Anthill stuff
        total_points += (our_anthill.captureHealth +
                         enemy_anthill.captureHealth) * 200  # 700
        good_points += our_anthill.captureHealth * 200  # 700

        return float(good_points) / float(total_points)

    def evaluate_nodes(self, nodes):
        """Evalute a list of Nodes and returns the best score."""
        return max(nodes, key=lambda node: node.score)
        # return max([self.score_state(node.state) for node in nodes])

    def get_best_move(self, state, depth_limit, moves=None):
        """
        Returns the best move for a given state, searching to a given
        depth limit. Uses score_state() to find how 'good' a certain move is.

        The first depth level is done here, remaining levels are done in
        analyze_subnodes() recursively.

        Parameters:
            state - GameState to analyze
            depth_limit - Depth limit for search

        Returns:
            Move with the best score.
        """
        # If we get a list of moves, just get rid of the END move(s)
        if moves is None:
            all_moves = [move for move in utils.listAllLegalMoves(
                state) if move.moveType != c.END]
        else:
            all_moves = [move for move in moves if move.moveType != c.END]

        # If there are moves left, then end the turn.
        if len(all_moves) == 0:
            return Move(c.END, None, None)
            # return Node(Move(c.END, None, None), state, 0.5)

        next_states = [self.getNextState(state, move) for move in all_moves]

        # Build first level of nodes
        nodes = [Node(move, state)
                 for move, state in zip(all_moves, next_states)]

        # Analyze the subnodes for this state. nodes is modified in-place.
        best_node = self.analyze_subnodes(state, depth_limit - 1, nodes=nodes)

        # If every move is bad, then just end the turn.
        if best_node.score <= 0.01:
            return Move(c.END, None, None)
            # return Node(Move(c.END, None, None), state, 0.01)

        return best_node.move

    def analyze_subnodes(self, state, depth_limit, nodes=None):
        """
        This is the recursive method. Function stack beware.

        Analyze each subnode of a given state to a given depth limit.
        Update each node's score and return the highest-scoring subnode.

        Parameters:
            state - GameState to analyze
            depth_limit - Depth limit for search
            nodes (optional) - List of subnodes. Used if first depth
                level is computed elsewhere (in get_best_move)

        Returns:
            Best scoring analyzed sub-node.
        """
        # If nodes haven't been passed, then expand the current
        # state's subnodes.
        if nodes is None:
            all_moves = [move for move in utils.listAllLegalMoves(
                state) if move.moveType != c.END]

            next_states = [self.getNextState(state, move)
                           for move in all_moves]

            nodes = [Node(move, state)
                     for move, state in zip(all_moves, next_states)]

        # Prune the bottom 4/5 of nodes by score
        nodes.sort(key=lambda node: node.score, reverse=True)
        if len(nodes) > 10:
            nodes = nodes[:len(nodes) / 5]

        # If the depth limit hasn't been reached,
        # analyze each subnode.
        if depth_limit >= 1:
            for node in nodes:
                # Set the node's score to the best score of its subnodes.
                best_node = self.analyze_subnodes(node.state, depth_limit - 1)
                node.score = best_node.score
                # If we have a good move, the just use it.
                if node.score > 0.7:
                    return node

        # Prevent the ants form getting stuck when all moves
        # are equal.
        random.shuffle(nodes)

        # Return the best node.
        return self.evaluate_nodes(nodes)

    def getPlacement(self, currentState):
        """
        Description:
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

        depth = 2
        move = self.get_best_move(currentState, depth)

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

    @staticmethod
    def getNextState(currentState, move):
        """
        Version of genNextState with food carrying bug fixed.
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


class Node(object):
    """
    Simple class for a search tree Node.

    Each Node requires a Move and a GameState. If a score is not
    provided, then one is calculated with AIPlayer.score_state().
    """

    __slots__ = ('move', 'state', 'score', 'parent')

    def __init__(self, move, state, score=None, parent=None):
        self.move = move
        self.state = state
        self.score = score
        if score is None:
            self.score = AIPlayer.score_state(state)
        self.parent = parent

class Unit_Tests(unittest.TestCase):

    def setup_state(self):
        board = [[Location((col, row)) for row in xrange(0,c.BOARD_LENGTH)] for col in xrange(0,c.BOARD_LENGTH)]
        p1Inventory = Inventory(c.PLAYER_ONE, [], [], 0)
        p2Inventory = Inventory(c.PLAYER_TWO, [], [], 0)
        neutralInventory = Inventory(c.NEUTRAL, [], [], 0)
        return GameState(board, [p1Inventory, p2Inventory, neutralInventory], c.SETUP_PHASE_1, c.PLAYER_ONE)

    def place_items(self, piece, constrsToPlace, state):
        #translate coords to match player
        piece = state.coordLookup(piece, state.whoseTurn)
        #get construction to place
        constr = constrsToPlace.pop(0)
        #give constr its coords
        constr.coords = piece
        #put constr on board
        state.board[piece[0]][piece[1]].constr = constr
        if constr.type == c.ANTHILL or constr.type == c.TUNNEL:
            #update the inventory
            state.inventories[state.whoseTurn].constrs.append(constr)
        else:  #grass and food
            state.inventories[c.NEUTRAL].constrs.append(constr)

    def setup_play(self, state):
        p1inventory = state.inventories[c.PLAYER_ONE]
        p2inventory = state.inventories[c.PLAYER_TWO]
        #get anthill coords
        p1AnthillCoords = p1inventory.constrs[0].coords
        p2AnthillCoords = p2inventory.constrs[0].coords
        #get tunnel coords
        p1TunnelCoords = p1inventory.constrs[1].coords
        p2TunnelCoords = p2inventory.constrs[1].coords
        #create queen and worker ants
        p1Queen = Ant(p1AnthillCoords, c.QUEEN, c.PLAYER_ONE)
        p2Queen = Ant(p2AnthillCoords, c.QUEEN, c.PLAYER_TWO)
        p1Worker = Ant(p1TunnelCoords, c.WORKER, c.PLAYER_ONE)
        p2Worker = Ant(p2TunnelCoords, c.WORKER, c.PLAYER_TWO)
        #put ants on board
        state.board[p1Queen.coords[0]][p1Queen.coords[1]].ant = p1Queen
        state.board[p2Queen.coords[0]][p2Queen.coords[1]].ant = p2Queen
        state.board[p1Worker.coords[0]][p1Worker.coords[1]].ant = p1Worker
        state.board[p2Worker.coords[0]][p2Worker.coords[1]].ant = p2Worker
        #add the queens to the inventories
        p1inventory.ants.append(p1Queen)
        p2inventory.ants.append(p2Queen)
        p1inventory.ants.append(p1Worker)
        p2inventory.ants.append(p2Worker)
        #give the players the initial food
        p1inventory.foodCount = 1
        p2inventory.foodCount = 1
        #change to play phase
        state.phase = c.PLAY_PHASE

    def create_state(self):
        ai = AIPlayer(0)
        self.state = self.setup_state()
        players = [c.PLAYER_ONE, c.PLAYER_TWO]

        for player in players:
            self.state.whoseTurn = player
            constrsToPlace = []
            constrsToPlace += [Building(None, c.ANTHILL, player)]
            constrsToPlace += [Building(None, c.TUNNEL, player)]
            constrsToPlace += [Construction(None, c.GRASS) for i in xrange(0,9)]

            setup = ai.getPlacement(self.state)

            for piece in setup:
                self.place_items(piece, constrsToPlace, self.state)

            self.state.flipBoard()

        self.state.phase = c.SETUP_PHASE_2

        for player in players:
            self.state.whoseTurn = player
            constrsToPlace = []
            constrsToPlace += [Construction(None, c.FOOD) for i in xrange(0,2)]

            setup = ai.getPlacement(self.state)

            for food in setup:
                self.place_items(food, constrsToPlace, self.state)

            self.state.flipBoard()

        self.setup_play(self.state)
        return self.state
        
        #self.failIf(a.getNextState(self, self.state))

    def test_one(self):
        self.state = self.create_state()
        
        
        #self.failIf(a.getNextState(self, self.state))

def main():
    unittest.main()

if __name__ == '__main__':
    main()

