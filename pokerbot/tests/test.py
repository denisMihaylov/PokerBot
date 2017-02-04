import unittest
from pokerbot.poker import deck


class TestHands(unittest.TestCase):

    def test_detection(self):
        straight_flush = Hand.get_hand([
            deck.Card(value, 'Hearts') for value in range(5)])
        straight = Hand.get_hand([
            deck.Card(value, 'Hearts') for value in
            range(4)] + [deck.Card(4, 'Clubs')])
        assert max(straight, straight_flush) == straight_flush
