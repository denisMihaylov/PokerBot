from itertools import combinations
import os
import sys
import logging
from pokerbot.poker.hands import Hand
import random


LOGGER = logging.getLogger('poker-players')


class Action(object):

    def __init__(self, player, round_):
        self.player = player
        self.round = round_

    @staticmethod
    def is_valid(player, round_):
        raise NotImplementedError("Can not validate abstract Action")

    def apply(self):
        raise NotImplementedError("Can not apply abstract Action")


class AmountableAction(Action):

    def __init__(self, player, round_, amount):
        super(AmountableAction, self).__init__(player, round_)
        self.amount = amount

    @staticmethod
    def is_valid(player, round_):
        raise NotImplementedError("Can not validate abstract Action")

    def apply(self):
        raise NotImplementedError("Can not apply abstract Action")


class Fold(Action):

    name = "Fold"

    @staticmethod
    def is_valid(player, round_):
        return player not in round_.folded_players

    def apply(self):
        self.round.folded_players.append(self.player)

    def __str__(self):
        return "Player %s folds" % self.player


class Check(Action):

    name = "Check"

    @staticmethod
    def is_valid(player, round_):
        pot = round_.pot
        return pot.player_bet(player) == pot.current_bet

    def apply(self):
        self.player.checked = True

    def __str__(self):
        return "Player %s checks" % self.player


class Call(AmountableAction):

    name = "Call"

    def __init__(self, player, round_):
        super(Call, self).__init__(
            player,
            round_,
            round_.pot.amount_to_call(player))

    @staticmethod
    def is_valid(player, round_):
        return player.money >= round_.pot.amount_to_call(player) > 0

    def apply(self):
        self.player.bet(self.amount, self.round)

    def __str__(self):
        return "Player %s calls %d" % (self.player, self.amount)


class Bet(AmountableAction):

    name = "Bet"

    MAX_RAISE = 30

    def __init__(self, player, round_, amount=None):
        bet_min = round_.pot.minimum_to_bet(player)
        bet_max = round_.pot.maximum_to_bet(player, round_)
        bet_max = min(bet_min + Bet.MAX_RAISE, bet_max)
        LOGGER.info("Setting bet limits to %d-%d" % (bet_min, bet_max))

        while (amount is None) or (bet_min > amount or amount > bet_max):
            try:
                amount = int(player.get_amount(bet_min, bet_max))
            except ValueError as e:
                LOGGER.error("Error while getting ammount: %s", str(e))
                sys.exit(0)
        LOGGER.debug("Player %s bet: %d" % (player, amount))

        super(Bet, self).__init__(player, round_, amount)

    @staticmethod
    def is_valid(player, round_):
        bet_max = round_.pot.maximum_to_bet(player, round_)
        return bet_max >= round_.pot.minimum_to_bet(player) > 0

    def apply(self):
        self.player.money -= self.amount
        self.round.bet(self.player, self.amount)

    def __str__(self):
        return "Player %s bets %d" % (self.player.name, self.amount)


class NotEnoughMoneyException(Exception):
    pass


class BasePlayer(object):

    ids = 0

    def __init__(self, name, starting_money):
        self.id = BasePlayer.ids
        BasePlayer.ids += 1
        self.name = name
        self.pocket = None
        self.money = starting_money
        self.first_bet = False
        self.checked = False

    def on_game_ended(self, game):
        pass

    def __str__(self):
        return "[name: %s, money: %s]" % (self.name, self.money)

    def set_pocket(self, card1, card2):
        self.pocket = [card1, card2]

    def bet(self, amount, round_):
        if amount > self.money:
            raise NotEnoughMoneyException(
                "Player " + self.name + " does not have enough money (" +
                self.money + "/" + amount + ")"
            )
        self.money -= amount
        round_.bet(self, amount)

    def force_bet(self, amount, round_):
        """
        Force a bet from the player, even if
        the amount exceeds the player's funds
        :param amount: the amount to force on the player
        :return:
                amount of money actually taken
        """
        LOGGER.info("Forcing %s to bet %d" % (self.name, amount))
        amount = min(amount, self.money)
        self.bet(amount, round_)
        return amount

    def interact(self, _game):
        raise NotImplementedError(
            "Interact is not implemented on the Player's base class")

    def get_amount(self, _min, _max):
        raise NotImplementedError(
            "get_amount is not implemented on the Player's base class")

    def is_folded(self, round_):
        return round_.is_folded(self)

    def can_bet(self, round_):
        return len(round_.active_players) > 1 and self.money > 0 and \
            self.first_bet or (
                not self.is_folded(round_) and
                round_.pot.amount_to_call(self) > 0)

    @staticmethod
    def generate_possible_hands(pocket, community_cards):
        return [
            Hand.get_hand(cards) for cards in
            combinations(community_cards + pocket, r=5)]

    def possible_hands(self, community_cards):
        return BasePlayer.generate_possible_hands(self.pocket, community_cards)

    def best_hand(self, community_cards):
        best_hand = max(self.possible_hands(community_cards))
        return best_hand

    def available_actions(self, _round):
        LOGGER.debug("fetching available moves")
        if not _round:
            LOGGER.debug("0 moves for false round")
            return []
        LOGGER.debug("round is ok, fetching moves")
        return list(filter(
            lambda x: x.is_valid(self, _round),
            [Check, Call, Bet, Fold]))

    def choose_action_message(self, round_):
        return os.linesep.join([
            "%s, your cards are %s please choose an action:" %
            (self.name, self.pocket)
        ] + ['. '.join(
            [str(index), action_name.__name__]
        ) for index, action_name in enumerate(self.available_actions(round_))
        ] + ["Community cards: %s" % round_.community_cards] +
            ["%s bet %d" % (player, round_.pot.player_bet(player))
                for player in round_.players])


class HumanPlayer(BasePlayer):

    NAME = "Human"

    def interact(self, _game):
        round_ = _game.current_round
        action = None
        while action is None:
            try:
                available_actions = self.available_actions(round_)
                action = available_actions[
                    int(input(self.choose_action_message(round_)))]
                return action(self, round_)
            except ValueError:
                pass
            except IndexError:
                pass

    def get_amount(self, _min, _max):
        return input("How much [%d - %d]?" % (_min, _max))


class RandomPlayer(BasePlayer):

    NAME = "Random Action"

    def interact(self, _game):
        round_ = _game.current_round
        return random.choice(self.available_actions(round_))(self, round_)

    def get_amount(self, _min, _max):
        return random.randint(_min, _max)
