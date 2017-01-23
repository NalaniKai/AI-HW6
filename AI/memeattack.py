# -*- coding: latin-1 -*-
import random
import sys
from os import path
# so other modules can be found in parent dir
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))  # nopep8
from Player import Player
import Constants as c
from Construction import CONSTR_STATS
from Ant import UNIT_STATS
from Move import Move
from GameState import addCoords
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
        super(AIPlayer, self).__init__(inputPlayerId, "Meme Attack")
        self.food = None
        self.tunnel = None
        self.current_state = None
        self.inv = None
        self.tried_drone = False
        self.move_list = []
        self.reset_move_list()

    def reset_move_list(self):
        self.move_list = ['attack', 'build', 'gather', 'queen']

    def getPlacement(self, current_state):
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
        if current_state.phase == c.SETUP_PHASE_1:
            placements = self.get_phase1_placement(current_state)
        else:
            placements = self.get_phase2_placement(current_state)
        return placements

    def getMove(self, current_state):
        """
        Description:
            The getMove method corresponds to the play phase of the
            game and requests from the player a Move object. All types are
            symbolic constants which can be referred to in Constants.py.
            The move object has a field for type (moveType) as well as field
            for relevant coordinate information (coordList). If for instance
            the player wishes to move an ant, they simply return a Move
            object where the type field is the MOVE_ANT constant and the
            coordList contains a listing of valid locations starting with
            an Ant and containing only unoccupied spaces thereafter.
            A build is similar to a move except the type is set as BUILD,
            a buildType is given, and a single coordinate is in the list
            representing the build location. For an end turn, no
            coordinates are necessary, just set the type as END and return.

        Parameters:
          current_state - The current state of the game at the time the Game is
              requesting a move from the player. (GameState)

        Return: Move(moveType [int],
                     coordList [list of 2-tuples of ints],
                     buildType [int])
        """
        self.inv = utils.getCurrPlayerInventory(current_state)
        self.current_state = current_state
        # pid = self.playerId
        # set up closest food and tunnel (only one tunnel)
        if self.tunnel is None:
            self.tunnel = utils.getConstrList(
                current_state, self.playerId, (c.TUNNEL,))[0]
        if self.food is None:
            # Adapted from FoodGatherer
            foods = utils.getConstrList(current_state, None, (c.FOOD,))
            # foods = [constr for constr in self.inv.constrs
            #          if constr.type == c.FOOD]
            self.food = foods[0]  # Pick first food
            best_dist = 1000  # Inf.
            for food in foods:
                dist = utils.stepsToReach(
                    current_state, self.tunnel.coords, food.coords)
                if dist < best_dist:
                    self.food = food
                    best_dist = dist

        # Find the anthill. Mostly used for Her Majesty.
        # Store the object to avoid calling things(???) repeatedly
        # if self.anthill is None:
        #     self.anthill = self.inv.getAnthill()

        # # Find the Queen. Mostly used for Her Majesty.
        # # Store the object to avoid calling things(???) repeatedly
        # if self.queen is None:
        #     self.queen = self.inv.getQueen()

        if 'queen' in self.move_list:
            qmove = self.move_queen()
            # Move the queen if needed
            if qmove is not None:
                return qmove

        # move = self.move_list.pop()
        if 'gather' in self.move_list:
            gmove = self.gather_food()
            if gmove is not None:
                return gmove
            # path = utils.createPathToward(current_state, )

        if 'build' in self.move_list:
            bmove = self.build_ants()
            if bmove is not None:
                return bmove

        if 'attack' in self.move_list:
            amove = self.move_to_attack()
            if amove is not None:
                return amove

        # Move(c.BUILD, None, c.DRONE)

        self.reset_move_list()
        return Move(c.END, None, None)

    def gather_food(self):
        """
        Generate Move object for food gathering strategy.
        Remove 'gather' from self.move_list when done.

        Return:
            Move object for next step in food gathering.
        """
        workers = utils.getAntList(
            self.current_state, self.playerId, (c.WORKER,))
        if len(workers) == 0:
            self.move_list.remove('gather')
            return None
        worker = workers[0]
        if worker.carrying:
            # If the worker has food, carry towards tunnel
            path = utils.createPathToward(
                self.current_state, worker.coords, self.tunnel.coords,
                UNIT_STATS[c.WORKER][c.MOVEMENT])
        else:
            path = utils.createPathToward(
                # if the worker does not have food, go get it
                self.current_state, worker.coords, self.food.coords,
                UNIT_STATS[c.WORKER][c.MOVEMENT])

        self.move_list.remove('gather')
        return Move(c.MOVE_ANT, path, None)

    def move_queen(self):
        """
        Generate Move object for queen moving strategy.
        Remove 'queen' from self.move_list when done.

        Return:
            Move object for next step in queen moving.
        """
        queen = self.inv.getQueen()
        # queen's range
        qrange = [(x, y) for x in xrange(10) for y in xrange(4)]
        move = None  # move to eventually make
        enemy_id = abs(self.playerId - 1)  # other player
        enemies = utils.getAntList(self.current_state, enemy_id)  # enemy ants

        enemies_in_range = [ant for ant in enemies if ant.coords in qrange]

        # Find the closest enemy, there are any
        if len(enemies_in_range):
            best_dist = 1000  # inf
            target = None  # ant to target
            for ant in enemies_in_range:
                dist = utils.stepsToReach(
                    self.current_state, queen.coords, ant.coords)
                if dist < best_dist:
                    target = ant
                    best_dist = dist
            path = utils.createPathToward(
                self.current_state, queen.coords, target.coords,
                UNIT_STATS[c.QUEEN][c.MOVEMENT])
            # self.move_list.remove('queen')
            # return Move(c.MOVE_ANT, path, None)
            move = Move(c.MOVE_ANT, path, None)

        # Make sure the queen isn't on the anthill or food
        anthill = self.inv.getAnthill()
        keep_offs = [food.coords for food in utils.getConstrList(
            self.current_state, None, (c.FOOD,))]
        keep_offs.append(anthill.coords)
        keep_offs.extend(utils.getConstrList(
            self.current_state, None, (c.TUNNEL,)))
        # keep_offs.append()
        if move is None and queen.coords in keep_offs:
            qcords = queen.coords
            # food_coords = [food.coords for food in utils.getConstrList(
            #     self.current_state, None, (c.FOOD,))]
            adjacents = utils.listReachableAdjacent(
                self.current_state, qcords, UNIT_STATS[c.QUEEN][c.MOVEMENT])
            # Only consider adjacents which are in our territory and don't
            # have food on them.
            adjacents = [
                coord for coord in adjacents if coord in qrange and
                coord not in keep_offs]
            path = utils.createPathToward(
                self.current_state, qcords, adjacents[0],
                UNIT_STATS[c.QUEEN][c.MOVEMENT])
            # self.move_list.remove('queen')
            # return Move(c.MOVE_ANT, path, None)
            move = Move(c.MOVE_ANT, path, None)
            # adjacents = [coord for coord in adjacents if self.current_state.bo]

        # Move off of food
        # food_coords = [food.coords for food in utils.getConstrList(
        #     self.current_state, None, (c.FOOD,))]
        # if queen.coords == food_coords[0] or queen.coords == food_coords[1]:

        self.move_list.remove('queen')
        return move

    def build_ants(self):
        """
        Generate Move object for the next move in the ant building strategy.
        Build a worker if they're all dead, or build a drone if one has
        not yet been built.

        Removes 'build' from self.move_list when done.

        Return:
            Move object for next step in ant building.
            None if no next step.
        """
        food_count = self.inv.foodCount
        anthill = self.inv.getAnthill()

        # initial check to see if we can build ants at all
        if (food_count == 0 or
                utils.getAntAt(self.current_state, anthill.coords) is not None):  # nopep8
            self.move_list.remove('build')
            return None

        ants = self.inv.ants
        workers = [ant for ant in ants if ant.type == c.WORKER]
        drones = [ant for ant in ants if ant.type == c.DRONE]
        move = None  # Move to eventually make

        # If the worker is dead, build a replacement
        if len(workers) == 0:
            move = Move(c.BUILD, [anthill.coords], c.WORKER)

        if (len(drones) == 0 and food_count >= 2 and
                move is None and not self.tried_drone):
            self.tried_drone = True
            move = Move(c.BUILD, [anthill.coords], c.DRONE)

        self.move_list.remove('build')
        return move

    def move_to_attack(self):
        """
        Generate Move object for the next move in the attack strategy.
        In essence, move any unmoved attacking-type ants (i.e. soldiers and drones)
        towards the nearest workers.

        Removes 'attack' from self.move_list when done.

        Return:
            Move object for next step in attacking.
            None if no next step.

        """
        attackers = [ant for ant in self.inv.ants
                     if ant.type != c.WORKER and
                     ant.type != c.QUEEN and
                     not ant.hasMoved]

        if len(attackers) == 0:
            self.move_list.remove('attack')
            return None

        drones = [ant for ant in attackers if ant.type == c.DRONE]

        enemies = utils.getAntList(self.current_state, abs(self.playerId - 1))
        e_workers = [ant for ant in enemies if ant.type == c.WORKER]

        if len(e_workers) == 0 or len(drones) == 0:
            self.move_list.remove('attack')
            return None

        # attack the nearest worker
        attack_dist = 1000  # inf
        target = e_workers[0]
        for enemy in e_workers:
            dist = utils.stepsToReach(
                self.current_state, drones[0].coords, enemy.coords)
            if dist < attack_dist:
                attack_dist = dist
                target = enemy

        path = utils.createPathToward(
            self.current_state, drones[0].coords, target.coords,
            UNIT_STATS[c.DRONE][c.MOVEMENT])
        return Move(c.MOVE_ANT, path, None)

    def getAttack(self, current_state, attackingAnt, enemyLocations):
        """
        Description:
            The getAttack method is called on the player whenever an ant
            completes a move and has a valid attack. It is assumed that
            an attack will always be made because there is no strategic
            advantage from withholding an attack. The AIPlayer is passed
            a copy of the state which again contains the board and also
            a clone of the attacking ant. The player is also passed a
            list of coordinate tuples which represent valid locations
            for attack. Hint: a random AI can simply return one of
            these coordinates for a valid attack.

        Parameters:
          current_state - The current state of the game at the time the
                Game is requesting a move from the player. (GameState)
          attackingAnt - A clone of the ant currently making the attack. (Ant)
          enemyLocation - A list of coordinate locations for valid attacks
            (i.e. enemies within range) ([list of 2-tuples of ints])

        Return: A coordinate that matches one of the entries of enemyLocations.
                ((int,int))
        """
        for enemy in enemyLocations:
            if utils.getAntAt(current_state, enemy).type == c.WORKER:
                return enemy
        return enemyLocations[0]

    def registerWin(self, hasWon):
        """
        Description:
            The last method, registerWin, is called when the game ends
            and simply indicates to the AI whether it has won or lost
            the game. This is to help with learning algorithms to
            develop more successful strategies.
        Parameters:
          hasWon - True if the player has won the game,
                False if the player lost. (Boolean)
        """
        # method templaste, not implemented
        self.food = None
        self.tunnel = None
        self.tried_drone = None
        pass

    def get_phase1_placement(self, current_state):
        """
        Returns properly formatted list of tuples for Phase 1
        placement of anthill, tunnel, and grass.

        Parameters:
          current_state - The current state of the game at the time the Game is
              requesting a move from the player. (GameState)
        """
        ant_hill = (7, 0)
        tunnel = (3, 1)
        grass = [(x, 3) for x in xrange(10) if x != ant_hill[0]]
        return [ant_hill, tunnel] + grass

    def get_phase2_placement(self, current_state):
        """
        Returns properly formatted list of tuples for Phase 2
        placement of food on enemy side.

        Parameters:
          current_state - The current state of the game at the time the Game is
              requesting a move from the player. (GameState)
        """
        enemy_id = abs(self.playerId - 1)
        enemy_anthill = utils.getConstrList(
            current_state, enemy_id, (c.ANTHILL,))[0]
        enemy_tunnel = utils.getConstrList(
            current_state, enemy_id, (c.TUNNEL,))[0]
        # enemy_grass = utils.getConstrList(current_state, enemy, (c.GRASS,))
        enemy_range = [(x, y) for x in xrange(10) for y in xrange(6, 10)]

        # place the food on the top row, close to our anthill if possible.
        our_anthill = utils.getConstrList(
            current_state, self.playerId, (c.ANTHILL,))[0]
        # TODO: Make attempted placement order more intelligent
        place_order = range(our_anthill.coords[0],
                            10) + range(our_anthill.coords[0])

        food_spots = []
        y = 6  # top enemy terrirory
        while len(food_spots) != 2:
            for x in place_order:
                if current_state.board[x][y].constr is None:
                    food_spots.append((x, y))
                    current_state.board[x][y].constr = True
                    break
            y += 1  # move down a row, will rarely happen

        return food_spots

        # def gather_food(self, current_state, my_inv):
