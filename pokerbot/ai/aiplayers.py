from pokerbot.poker.player import BasePlayer
from pokerbot.ai import strategies
import random
from pokerbot.poker.player import Call, Fold, Bet, Check
from pokerbot.ai import utils
import logging
from pokerbot.poker.deck import Card

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
        if wins.index(max(wins)) == 0:
            if Call in available_actions:
                return Call(self, round_)
            if Bet in available_actions:
                return Bet(self, round_)
        if Check in available_actions:
            return Check(self, round_)
        if wins[0] / wins[winner_index] > 0.70 and Call in available_actions:
            return Call(self, round_)
        return Fold(self, round_)

    def get_amount(self, _min, _max):
        return random.randint(_min, _max);
