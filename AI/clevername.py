import random
import sys
import math
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))  # nopep8
from Player import Player
import Constants as c
from Construction import CONSTR_STATS
from Ant import UNIT_STATS
from Move import Move
from GameState import addCoords, subtractCoords
import AIPlayerUtils as utils


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
        if (our_food == 11 or
            enemy_queen is None or
                enemy_anthill.captureHealth == 0):
            return we_win
        # Initial lose condition checks:
        if (enemy_food == 11 or
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
        food_move = 100
        our_workers = [ant for ant in our_inv.ants if ant.type == c.WORKER]
        for ant in our_workers:
            ant_x = ant.coords[0]
            ant_y = ant.coords[1]
            for enemy in enemy_inv.ants:
                if ((abs(ant_x - enemy.coords[0]) > 3) and
                        (abs(ant_y - enemy.coords[1]) > 3)):
                    good_points += 60  # 50
                    total_points += 60  # 50
            if ant.carrying:
                total_points += food_move  # 50
                good_points += food_move  # 50

                for dist in range(2, 4):
                    for dropoff in food_drop_offs:
                        if ((abs(ant_x - dropoff[0]) < dist) and
                                (abs(ant_y - dropoff[1]) < dist)):
                            good_points += food_move - (dist * 25)
                            total_points += food_move - (dist * 25)

        # Depositing food is even better!
        if any([ant for ant in our_workers if ant.coords in food_drop_offs and ant.carrying]):
            total_points += food_move * 2  # 3000
            good_points += food_move * 2  # 3000

        # Raw ant numbers comparison
        total_points += (len(our_inv.ants) + len(enemy_inv.ants)) * 10  # 30
        good_points += len(our_inv.ants) * 10  # 30

        # Weighted ant types
        # Workers, first 3 are worth 20, the rest are penalized
        # STOP BUILDING SO MANY WORKERS PLEASE
        # our_workers = [ant for ant in our_inv.ants if ant.type == c.WORKER]
        # our_workers is defined above
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

        # prefer workers to not leave home
        our_range = [(x, y) for x in xrange(10) for y in xrange(5)]
        if len([ant for ant in our_workers if ant.coords not in our_range]) != 0:
            return .001
            # total_points += 100000

        # if len(enemy_workers) <= 3:
        #     total_points += len(enemy_workers) * 20
        # else:
        #     total_points += (len(enemy_workers) - 2) * 10 + 60

        # Offensive ants
        # Let's just say each ant is worth 120x its cost for now
        # TODO: Better weighting
        offensive = [c.SOLDIER, c.R_SOLDIER, c.DRONE]
        our_offense = [ant for ant in our_inv.ants if ant.type in offensive]
        enemy_offense = [
            ant for ant in enemy_inv.ants if ant.type in offensive]

        for ant in our_offense:
            ant_x = ant.coords[0]
            ant_y = ant.coords[1]
            attack_move = 160  # 3000
            good_points += UNIT_STATS[ant.type][c.COST] * 20  # 120
            total_points += UNIT_STATS[ant.type][c.COST] * 20  # 120
            # good if on enemy anthill
            if ant.coords == enemy_anthill.coords:
                total_points += 100  # 2000
                good_points += 100  # 2000
            for enemy_ant in enemy_inv.ants:
                enemy_x = enemy_ant.coords[0]
                enemy_y = enemy_ant.coords[1]
                x_dist = abs(ant_x - enemy_x)
                y_dist = abs(ant_y - enemy_y)

                # good if attacker ant attacks
                if (x_dist + y_dist) == 1:
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
            # total_points += 100000000000000

        # Queen stuff
        # Queen healths, big deal, each HP is worth 300!
        total_points += (our_queen.health + enemy_queen.health) * 100  # 300
        good_points += our_queen.health * 100  # 300
        queen_coords = our_queen.coords
        if queen_coords in food_drop_offs or queen_coords[1] > 2:
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
        # our_anthill = our_inv.getAnthill() Defined above
        total_points += (our_anthill.captureHealth +
                         enemy_anthill.captureHealth) * 200  # 700
        good_points += our_anthill.captureHealth * 200  # 700

        return float(good_points) / float(total_points)

    def evaluate_nodes(self, nodes):
        """Evalute a list of Nodes and returns the best score."""
        return max(nodes, key=lambda node: node.score)
        # return max([self.score_state(node.state) for node in nodes])

    def recursion_in_python_is_bad(self, state, depth_left, moves=None):
        """Silly Python."""
        max_score = 0.0
        # If we get a list of moves, just get rid of the END move(s)
        if moves is None:
            all_moves = [move for move in utils.listAllLegalMoves(
                state) if move.moveType != c.END]
        else:
            all_moves = [move for move in moves if move.moveType != c.END]

        if len(all_moves) == 0:
            return Node(Move(c.END, None, None), state, 0.5)

        next_states = [utils.getNextState(state, move) for move in all_moves]

        nodes = [Node(move, state)
                 for move, state in zip(all_moves, next_states)]

        # Recurse if needed.
        if depth_left > 0:
            for node in nodes:
                new_node = node
                if max_score == 0.0:
                    new_node = self.recursion_in_python_is_bad(
                        node.state, depth_left - 1)
                elif node.score > max_score:
                    max_score = node.score
                    new_node = self.recursion_in_python_is_bad(
                        node.state, depth_left - 1)
                if new_node.score > node.score:
                    node.score = new_node.score
                if max_score > 0.7:
                    break

        # Prevent the ants form getting stuck when all moves
        # are equal.
        random.shuffle(nodes)

        best_node = self.evaluate_nodes(nodes)

        if best_node.score <= 0.01:
            return Node(Move(c.END, None, None), state, 0.01)

        return best_node

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
        # moves = utils.listAllLegalMoves(currentState)
        # selectedMove = moves[random.randint(0, len(moves) - 1)]

        # # don't do a build move if there are already 3+ ants
        # numAnts = len(currentState.inventories[currentState.whoseTurn].ants)
        # while (selectedMove.moveType == c.BUILD and numAnts >= 3):
        #     selectedMove = moves[random.randint(0, len(moves) - 1)]

        # print self.score_state(currentState)
        # print self.recursion_in_python_is_bad(currentState, 1).score
        depth = 1
        node = self.recursion_in_python_is_bad(currentState, depth)

        print "Current: {}, next node: {}".format(self.score_state(currentState), node.score)

        return node.move

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


class Node(object):
    """
    Simple class for a search tree Node.
    """

    __slots__ = ('move', 'state', 'score', 'parent')

    def __init__(self, move, state, score=None, parent=None):
        self.move = move
        self.state = state
        self.score = score
        if score is None:
            self.score = AIPlayer.score_state(state)
        self.parent = None
