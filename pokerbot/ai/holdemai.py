import numpy as np
from pokerbot.ai.neural_network import NeuralNetwork
from pokerbot.ai.analyzer import Analyzer, Card
from pokerbot.poker.player import Call, Fold, Bet, Check

from pokerbot.deuces.deuces import Card

from pokerbot.poker.player import BasePlayer

class HoldemAI(NeuralNetwork, BasePlayer):

    NAME = "Holdem AI"

    def __init__(self, name, starting_money, ID = None):
        NeuralNetwork.__init__(self, [9, 7, 5], ID)
        BasePlayer.__init__(self, name, starting_money)
        self.analyzer = Analyzer()

    def interact(self, _game):
        parsed = self.input_parser(_game)
        activated = list(self.activate(parsed))
        activated[-1] = self.rescale_output(activated[-1])
        #output = self.output_parser(activated, _game)
        #print("Output:", output)
        return Fold(self, _game.current_round)

    def get_amount(self, _min, _max):
        pass

    #remove after interact is completed
    def act(self, table_state):
        parsed = self.input_parser(table_state)
        activated = list(self.activate(parsed))
        # output vector interpreted as (raise, call, check, fold, bet_ammount)
        activated[-1] = self.rescale_output(activated[-1])
        return self.output_parser(activated, table_state)

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
        diff = active_players.index(self) - active_players.index(round_.button_player)
        if diff < 0:
            return len(active_players) + diff
        return diff

    # parses table_state from TableProxy into clean (mostly binary) data for neural network
    def input_parser(self, _game):
        round_ = _game.current_round
        players = round_.players
        active_players = round_.active_players
        chips_in_pot = round_.pot.total_pot_money
        chips_to_call = round_.pot.minimum_to_bet(self)
        num_opponents = len(active_players) - 1

        my_cards = self.convert_cards(self.pocket)
        community_cards = self.convert_cards(round_.community_cards)

        win_percent = self.get_win_percent(num_opponents, my_cards, community_cards)
        hands_until_dealer = self.get_hands_until_dealer(round_, active_players)
        my_stack = self.money

        # # binary data
        # hand_bin = [j for i in [HoldemAI.card_to_binlist(c) for c in hand] for j in i]
        # community = community + [0]*(5-len(community))
        # comm_bin = [j for i in [HoldemAI.card_to_binlist(c) for c in community] for j in i]
        #my_seat_bin = HoldemAI.bin_to_binlist(bin(my_seat)[2:].zfill(3))

        self.chip_mean = sum([p.money for p in active_players]) / len(active_players)
        self.chip_range = self.chip_mean * len(active_players) / 2

        #for p in players:
        #    p[0] = HoldemAI.bin_to_binlist(bin(p[0])[2:].zfill(3))
        #    p[1] = [(p[1]-self.chip_mean)/self.chip_range]
        #    p[2] = HoldemAI.bin_to_binlist(bin(p[2])[2:])
        #    p[3] = HoldemAI.bin_to_binlist(bin(p[3])[2:])


        # avg pot size in 8-person cash table No Limit Hold'em is reported to be ~6-10 big blinds
        # add: compute rolling average
        pot_centered = (chips_in_pot-8)/self.chip_range

        # average to call size will be assumed to be 1/3 of average pot (educated guess)
        # add: compute rolling average
        tocall_centered = (chips_to_call-8/3)/self.chip_range

        # treated same as tocall
        #lastraise_centered = (lastraise-8/3)/self.chip_range

        # center win percentage
        win_percent_centered = (win_percent-0.5)*2

        # combine binary and continuous data into one vector

        # my_seat_bin  uses 3 inputs
        #inputs_bin = my_seat_bin

        # pot_centered, tocall_centered, lastraise_centered, win_percent_centered each use 1 input
        inputs_cont = [pot_centered, tocall_centered, num_opponents, win_percent_centered]

        # each player addes 1 continuous input, and 2 binary inputs
        for p in players:
            #inputs_bin = inputs_bin + p[2] + p[3]
            inputs_cont.append(p.money)

        #inputs = HoldemAI.center_bin(inputs_bin) + inputs_cont
        print(inputs_cont)
        print(len(inputs_cont))
        return inputs_cont

    def rescale_output(self,num):
        # output of neural network is given from -1 to 1, we interpret this as a bet ammount as a percentage of the player's stack
        return int((num+1)*self.money/2)

    # parses output for PlayerControl
    def output_parser(self, response, table_state):
        tocall = table_state.get('tocall', None)
        my_stack = table_state.get('players')[table_state.get('my_seat')][1]
        bigblind = table_state.get('bigblind', None)
        minraise = table_state.get('minraise', None)

        bet_size = response[-1]
        bet_size += bigblind -(bet_size % bigblind)
        bet_size = max(bet_size, my_stack)
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
