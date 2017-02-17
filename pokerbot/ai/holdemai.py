import numpy as np
from pokerbot.ai.neural_network import NeuralNetwork
from pokerbot.ai.analyzer import Analyzer, Card
from pokerbot.poker.player import Call, Fold, Bet, Check
import random
from pokerbot.deuces.deuces import Card

from pokerbot.poker.player import BasePlayer

class HoldemAI(NeuralNetwork, BasePlayer):

    NAME = "Holdem AI"

    def __init__(self, name, starting_money = 1000, ID = '46e292f0-28bd-4953-9d70-d1ee109130af'):
        NeuralNetwork.__init__(self, [31, 20, 5], ID)
        BasePlayer.__init__(self, name, starting_money)
        self.analyzer = Analyzer()

    def interact(self, _game):
        action = self.act(_game)
        round_ = _game.current_round
        print("Action: ", action)
        if action[0] == 'fold':
            return Fold(self, round_)
        if action[0] == 'call':
            return Call(self, round_)
        if action[0] == 'check':
            return Check(self, round_)
        if action[0] == 'raise':
            return Bet(self, round_)

    def get_amount(self, _min, _max):
        return random.randint(_min, _max)

    #remove after interact is completed
    def act(self, _game):
        parsed = self.input_parser(_game)
        activated = list(self.activate(parsed))
        # output vector interpreted as (raise, call, check, fold, bet_ammount)
        activated[-1] = self.rescale_output(activated[-1])
        return self.output_parser(activated, _game)

    def convert_cards(self, cards):
        return [Card.new(card.parse()) for card in cards]

    def get_win_percent(self, num_opponents, my_cards, community_cards):
        self.analyzer.set_num_opponents(num_opponents)
        self.analyzer.set_pocket_cards(*my_cards)
        for card in community_cards:
            self.analyzer.community_card(card)

        # computes win percentage as proxy for hand data and community data
        win_percent = self.analyzer.analyze()
        self.analyzer.reset()
        return win_percent

    def get_hands_until_dealer(self, round_, active_players):
        result = 0
        current_player = self
        while True:
            if current_player is round_.button_player:
                return result
            result += 1
            index = round_.players.index(current_player)
            current_player = round_.players[(index + 1) % len(round_.players)]

    # parses table_state from TableProxy into clean (mostly binary) data for neural network
    def input_parser(self, _game):
        inputs = 31 * [0]
        round_ = _game.current_round
        big_blind = round_.small_blind * 2
        players = round_.players
        active_players = round_.active_players
        num_opponents = len(active_players) - 1

        my_cards = self.convert_cards(self.pocket)
        community_cards = self.convert_cards(round_.community_cards)

        #HERE STARTS
        hand = self.convert_cards(self.pocket)
        community = self.convert_cards(round_.community_cards)
        my_seat = self.get_hands_until_dealer(round_, active_players) % 8
        pot = round_.pot.total_pot_money / big_blind
        tocall = round_.pot.amount_to_call(self) / big_blind
        lastraise = round_.pot.last_raise / big_blind

        # make note of our own stack
        self.my_stack = self.money

        # setup analyzer
        self.analyzer.set_num_opponents(num_opponents)
        self.analyzer.set_pocket_cards(*hand)
        for card in community:
            self.analyzer.community_card(card)

        # computes win percentage as proxy for hand data and community data
        win_percent = self.analyzer.analyze()
        print("Win percent: ", win_percent)
        self.analyzer.reset()

        # # binary data
        # hand_bin = [j for i in [HoldemAI.card_to_binlist(c) for c in hand] for j in i]
        # community = community + [0]*(5-len(community))
        # comm_bin = [j for i in [HoldemAI.card_to_binlist(c) for c in community] for j in i]
        my_seat_bin = HoldemAI.bin_to_binlist(bin(my_seat)[2:].zfill(3))

        # continuous data
        # normalize chip data by bigblind
        #for p in players:
        #    p[1] = p[1]/bigblind
        #pot = pot/bigblind
        #tocall = tocall/bigblind
        #lastraise = lastraise/bigblind

        self.chip_mean = sum([p.money for p in players]) / len(players) / big_blind
        self.chip_range = self.chip_mean * len(players) / 2
        print("Chip Mean: ", self.chip_mean)
        print("Chip Range: ", self.chip_range)

        # avg pot size in 8-person cash table No Limit Hold'em is reported to be ~6-10 big blinds
        # add: compute rolling average
        pot_centered = (pot - len(players)) / self.chip_range
        print("Pot: ", pot)
        print("Pot centered: ", pot_centered)

        # average to call size will be assumed to be 1/3 of average pot (educated guess)
        # add: compute rolling average
        tocall_centered = (tocall - len(players) / 3) / self.chip_range

        # treated same as tocall
        lastraise_centered = (lastraise - len(players) / 3) / self.chip_range

        # center win percentage
        win_percent_centered = (win_percent - 0.5) * 2

        # combine binary and continuous data into one vector

        # my_seat_bin  uses 3 inputs
        inputs_bin = my_seat_bin

        # pot_centered, tocall_centered, lastraise_centered, win_percent_centered each use 1 input
        inputs_cont = [pot_centered, tocall_centered, lastraise_centered, win_percent_centered]

        # each player addes 1 continuous input, and 2 binary inputs
        for p in players:
            p2 = HoldemAI.bin_to_binlist(bin(p in active_players)[2:])
            p3 = HoldemAI.bin_to_binlist(bin(False)[2:])
            inputs_bin = inputs_bin + p2 + p3
            inputs_cont = inputs_cont + [(p.money / big_blind - self.chip_mean) / self.chip_range]
        if len(players) < 8:
            inputs_bin = inputs_bin + (8 - len(players)) * [0, 0]
            inputs_cont = inputs_cont + (8 - len(players)) * [0]

        inputs = HoldemAI.center_bin(inputs_bin) + inputs_cont
        if len(inputs) < 31:
            inputs = inputs + (31 - len(inputs)) * [0]

        print("Starts Here")
        print(*inputs, sep='\n')
        return inputs

    def rescale_output(self,num):
        # output of neural network is given from -1 to 1, we interpret this as a bet ammount as a percentage of the player's stack
        return int((num+1)*self.money/2)

    # parses output for PlayerControl
    def output_parser(self, response, _game):
        round_ = _game.current_round
        tocall = round_.pot.amount_to_call(self)
        my_stack = self.money
        bigblind = round_.small_blind * 2
        minraise = round_.pot.minimum_to_bet(self)

        bet_size = response[-1]
        bet_size += bigblind -(bet_size % bigblind)
        bet_size = max(bet_size, my_stack)
        print(response)
        # response[0:4] = [raise_confidence, call_confidence, check_confidence, fold_confidence]
        if tocall > 0:
            # choose between raise, call, fold
            move_idx = np.argmax(response[:2] + response[3:-1])
            # 0 - Raise
            # 1 - Call
            # 3 - Fold
            if move_idx == 0:
                if bet_size < minraise:
                    return ('call', tocall)
                if tocall >= my_stack or tocall >= bet_size:
                    return ('call', tocall)
                return ('raise', min(max(bet_size, minraise), my_stack))
            elif move_idx == 1:
                return ('call', tocall)
            else:
                return ('fold', -1)
        else:
            # 0 - Raise
            # 2 - Check
            move_idx = np.argmax(response[:1] + response[2:-2])
            print("MoveID: ", move_idx)
            if move_idx == 0:
                return ('raise', bet_size)
            else:
                return ('check', 0)

    # takes card from deuces Card class (reprsented by int) and gives its 29 digit binary representation in a list, first 3 bits are unused
    @staticmethod
    def card_to_binlist(card):
        return [ord(b)-48 for b in bin(card)[2:].zfill(29)]

    @staticmethod
    def bin_to_binlist(bin_num):
        return [ord(b)-48 for b in bin_num]

    @staticmethod
    def center_bin(num):
        return list(map(lambda x: -1 if x==0 else x, num))
