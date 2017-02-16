from random import choice
from collections import defaultdict
import logging
from pokerbot.poker.deck import Deck
from multiprocessing import Queue

LOGGER = logging.getLogger('poker-main')


class Events:
    PLAYER_BETTING = "Player betting"
    GAME_STARTED = "Game started"
    CARD_OPENED = "Card opened"
    ROUND_FINISHED = "Round finished"
    PLAYER_BET = "Player bet"
    GAME_FINISHED = "Game finished"


class Pot(object):
    def __init__(self, small_blind):
        self.bets = defaultdict(int)
        self.last_raise = small_blind * 2
        self.total_pot_money = 0

    @property
    def current_bet(self):
        return max(self.bets.values())

    def player_bet(self, player):
        return self.bets[player]

    def amount_to_call(self, player):
        return self.current_bet - self.bets[player]

    def minimum_to_bet(self, player):
        LOGGER.debug("current bet: %d, last raise: %d, player_bet: %d" % (
            self.current_bet, self.last_raise, self.player_bet(player)
        ))
        return max(0, self.amount_to_call(player) + self.last_raise)

    def maximum_to_bet(self, player, round_):
        max_raise = min([player1.money - self.minimum_to_bet(player1)
            for player1 in round_.active_players])
        return min(self.minimum_to_bet(player) + max_raise, player.money)

    def take_pot_for_player(self, player):
        player_bet = self.player_bet(player)

        winnings = 0
        # take amount from all bets
        for player, bet in self.bets.items():
            # see how much is possible to take from player
            possible_to_take = min(bet, player_bet)
            winnings += possible_to_take
            # remove as much as possible from player
            self.bets[player] -= possible_to_take

        return winnings

    def bet(self, player, amount):
        LOGGER.info("%s bets %d" % (player, amount))
        self.bets[player] += amount
        self.total_pot_money += amount


class Round(object):
    def __init__(self, players, button_player, small_blind, event_queue, game):
        self.game = game
        self.event_queue = event_queue
        self.players = players[:]
        self.folded_players = []
        self.small_blind = small_blind
        self.betting_player = None
        self.deck = Deck()
        self.community_cards = []
        self.button_player = button_player
        self.pot = Pot(self.small_blind)
        self.action_log = []
        LOGGER.info("Dealing cards")
        for player in self.players:
            player.set_pocket(self.deck.draw_single(), self.deck.draw_single())

    def bet(self, player, amount):
        self.event_queue.put(Events.PLAYER_BET)
        self.pot.bet(player, amount)

    def is_folded(self, player):
        return player in self.folded_players

    @property
    def active_players(self):
        return [player for player in
                self.players if player not in self.folded_players]

    def after(self, player):
        index = self.players.index(player)
        return self.players[(index + 1) % len(self.players)]

    def take_blinds(self):
        LOGGER.info("Taking blinds from players")
        self.small_blind_player().force_bet(self.small_blind, self)
        self.big_blind_player().force_bet(2 * self.small_blind, self)
        return self.betting_player

    def small_blind_player(self):
        return self.after(self.button_player)

    def big_blind_player(self):
        return self.after(self.after(self.button_player))

    def winner(self):
        # check if only a single player is left
        if len(self.players) - len(self.folded_players) == 1:
            return self.players[0]
        return None

    def pre_flop_betting(self):
        if self.winner() is not None:
            return
        self.betting_player = self.after(self.big_blind_player())
        self.place_bets()

    def pre_turn_betting(self):
        if self.winner() is not None:
            return
        self.betting_player = self.after(self.button_player)
        self.place_bets()

    def pre_river_betting(self):
        if self.winner() is not None:
            return
        self.betting_player = self.after(self.button_player)
        self.place_bets()

    def final_betting(self):
        if self.winner() is not None:
            return
        self.betting_player = self.after(self.button_player)
        self.place_bets()

    def next_betting_player(self):
        start = self.betting_player
        candidate = self.after(start)
        while candidate is not start:
            if candidate.can_bet(self):
                LOGGER.info("Found betting player %s" % candidate)
                return candidate
            LOGGER.info("Skipping player %s" % candidate)
            candidate = self.after(candidate)
        return None

    def place_bets(self):
        # when no betting players are left
        # self.betting_player will be set to None

        # set player first_bet to True to indicate this player is yet to bet
        for player in self.active_players:
            player.first_bet = True

        if not self.betting_player.can_bet(self):
            LOGGER.info("Skipping player: %s" % str(self.betting_player))
            self.betting_player = self.next_betting_player()

        while self.betting_player is not None:
            LOGGER.info("player %s is choosing an action",
                        self.betting_player)
            self.betting_player.first_bet = False
            self.event_queue.put(Events.PLAYER_BETTING)
            action = self.betting_player.interact(self.game)
            LOGGER.info("%s chose Action: %s" % (
                self.betting_player, action.__class__.__name__))
            self.action_log.append(action)
            action.apply()
            self.betting_player = self.next_betting_player()

        LOGGER.info("Done betting for pre_flop_round")

    def play(self):

        self.take_blinds()

        LOGGER.info("Playing first round (pre-flop)")
        self.pre_flop_betting()
        self.open_flop_cards()

        LOGGER.info("Playing first round (pre-turn)")
        self.pre_turn_betting()
        self.open_turn_cards()

        LOGGER.info("Playing first round (pre-river)")
        self.pre_river_betting()
        self.open_river_cards()
        self.final_betting()
        LOGGER.info("Round winners:")
        for winner_ in self.get_round_winners():
            LOGGER.info("%s" % winner_)
        return dict(self.finish_round())

    def open_card(self):
        self.event_queue.put(Events.CARD_OPENED)
        self.community_cards.append(self.deck.draw_single())

    def open_flop_cards(self):
        self.open_card()
        self.open_card()
        self.open_card()

    def open_turn_cards(self):
        self.open_card()

    def open_river_cards(self):
        self.open_card()

    def finish_round(self):
        self.event_queue.put(Events.ROUND_FINISHED)
        for winner_ in self.get_round_winners():
            winnings = self.pot.take_pot_for_player(winner_)
            LOGGER.info("Giving winnings (%d) to player: %s [%s]" % (
                winnings,
                winner_.name,
                winner_.best_hand(self.community_cards)))
            winner_.money += winnings
            yield winner_, winnings

    def get_round_winners(self):
        return sorted(
            set(self.players) - set(self.folded_players),
            key=lambda x: x.best_hand(self.community_cards),
            reverse=True
        )


class Poker(object):
    def __init__(self, players):

        # list of players who ran out of money
        self.finished_players = []

        # list of all players in game
        self.players = players

        self.button_player = choice(self.players)
        self.small_blind = 1
        self.rounds = []
        self.log = ["STARTING GAME..."]
        self.current_round = None
        self.event_queue = Queue()

    def winner(self):
        """
        :return: game's winner, if one exists (None otherwise)
        """
        return self.players[0] if len(self.players) == 1 else None

    def after(self, player):
        player_index = (self.players.index(player) + 1) % len(self.players)
        return self.players[player_index]

    def advance_button_player(self):
        self.button_player = self.after(self.button_player)
        while self.button_player.money == 0:
            # keep searching for valid button player
            self.button_player = self.after(self.button_player)

    def play(self):
        LOGGER.debug("Starting game")
        while self.winner() is None:
            self.event_queue.put(Events.GAME_STARTED)
            LOGGER.info("Playing round #%d" % (len(self.rounds) + 1))
            LOGGER.info("Players are:")
            for player in self.players:
                LOGGER.info("%s" % player)
            round_ = Round(
                self.players,
                self.button_player,
                self.small_blind,
                self.event_queue, self)
            self.current_round = round_
            winnings = round_.play()
            self.rounds.append(round_)

            for player, winning in winnings.items():
                hand = player.best_hand(round_.community_cards)
                self.log.append("Round %d - %s won %d with %s [%s]" % (
                    len(self.rounds) + 1,
                    player.name,
                    winning,
                    hand.__class__.__name__,
                    str(hand)))
            # move button (before possibly removing button player)
            self.advance_button_player()

            # set up players
            for player in self.players:
                if player.money == 0:
                    LOGGER.info("Player %s finished the game" % str(player))
                    self.finished_players.append(player)
                    self.players.remove(player)

        winner = self.winner()
        self.log.append("%s won the game." % winner)
        self.event_queue.put(Events.GAME_FINISHED)
        LOGGER.info("%s won the game.", winner)
        for player in self.players:
            player.on_game_ended(self)
        return self.winner()
