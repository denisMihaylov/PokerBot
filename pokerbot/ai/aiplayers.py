from pokerbot.poker.player import BasePlayer
from pokerbot.ai import strategies
import random
from pokerbot.poker.player import Call, Fold, Bet, Check
from pokerbot.ai import utils
import logging
from pokerbot.poker.deck import Card
import numpy
import itertools

LOGGER = logging.getLogger('poker-ai-players1')


class SimpleAIPlayer(BasePlayer):

    NAME = "Simple AI"

    def __init__(self, name, starting_money):
        super(SimpleAIPlayer, self).__init__(name, starting_money)
        self.strat = strategies.SimpleSaneStrategy(1, 1, 1, 1)

    def interact(self, _game):
        round_ = _game.current_round
        action = self.strat.rank(_game)
        while action not in self.available_actions(round_):
            action = self.strat.rank(_game)
        return action(self, round_)

    def get_amount(self, _min, _max):
        return random.randint(_min, _max)

class MonteCarloAI(BasePlayer):

    NAME = "MonteCarloAI"

    def interact(self, game):
        round_ = game.current_round
        my_cards = self.pocket
        players_count = len(round_.active_players)
        wins = [0.0] * players_count
        LOGGER.debug("Calculating win ration")
        for i in range(0, 100):
            community_cards = round_.community_cards
            community_cards = Card.random_cards(5 - len(community_cards)) + \
                community_cards
            players_cards = [my_cards] + [Card.random_cards(2) for i in
                range(players_count - 1)]
            best_hands = [
                utils.get_best_possible_hand(player_cards, community_cards)
                for player_cards in players_cards]
            winner_index = best_hands.index(max(best_hands))
            wins[winner_index] += 1
        available_actions = self.available_actions(round_)
        winner_index = wins.index(max(wins))
        LOGGER.debug("Win ratio calculated")
        if wins.index(max(wins)) == 0:
            if Bet in available_actions:
                return Bet(self, round_)
            if Call in available_actions:
                return Call(self, round_)
        if Check in available_actions:
            return Check(self, round_)
        if wins[0] / wins[winner_index] > 0.70 and Call in available_actions:
            return Call(self, round_)
        return Fold(self, round_)

    def get_amount(self, _min, _max):
        return random.randint(_min, _max)


MAX_OPPENENTS = 5

pre_flop_table = numpy.zeros((169, MAX_OPPENENTS))

def is_increasing(l):
    return all(a <= b for a, b in zip(l[:-1], l[1:]))

def get_all_possible_flops(num_cards):
    all_flops = list(itertools.permutations(range(2, 15), num_cards))
    return filter(is_increasing, all_flops)




def init_post_flop_table():
    if post_flop_table_initialized:
        return
    flop = 3 * [0]
    flop_id = 0
    for full_flop in get_all_possible_flops(5):
        flop = full_flop
        m = full_flop[3]
        n = full_flop[4]
        hole_id = 0
        for m in range(2, 29):
            continue if m in flop
            for n in range(m + 1, )
            if m < 14:
                pass


class NeuralAI(BasePlayer):

    NAME = "NeuralAI"

    def __init__(self, name, starting_mone)
        pass
