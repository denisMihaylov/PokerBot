# coding=utf-8
from random import shuffle


class Suits:
    HEARTS = "Hearts"
    DIAMONDS = "Diamonds"
    CLUBS = "Clubs"
    SPADES = "Spades"
    SUITS = (HEARTS, DIAMONDS, CLUBS, SPADES)

symbols = {
    Suits.SPADES: u'♠ '.encode("utf-8"),
    Suits.HEARTS: u'♥ '.encode("utf-8"),
    Suits.DIAMONDS: u'♦ '.encode("utf-8"),
    Suits.CLUBS: u'♣ '.encode("utf-8")}


class Card(object):
    def __init__(self, value, suit):
        self.value = value
        self.suit = suit

    def __gt__(self, other):
        if not isinstance(other, Card):
            return False
        return self.value > other.value

    def __eq__(self, other):
        is_card_eq = self.value == other.value and self.suit == other.suit
        return isinstance(other, Card) and is_card_eq

    def __repr__(self):
        return str(self.value) + symbols[self.suit]

    def __str__(self):
        return str(self.value) + symbols[self.suit]

    def __hash__(self):
        return hash(self.value) ^ hash(self.suit)

    def color(self):
        if self.suit in (Suits.HEARTS, Suits.DIAMONDS):
            return "red"
        return "black"


class Deck(object):
    def __init__(self):
        self.cards = [
            Card(value, suit) for value in
            range(2, 14) for suit in Suits.SUITS]
        self.shuffle()

    def shuffle(self):
        shuffle(self.cards)

    def draw(self, number=1):
        drawn, self.cards = self.cards[:number], self.cards[number:]
        return drawn

    def draw_single(self):
        return self.cards.pop()

    def removeall(self, cards):
        '''
        remove a sequence of cards from the deck
        :param cards: cards to remove from the deck
        :return: sequence of remaining cards
        '''
        remaining = set(self.cards) - set(cards)
        self.cards = list(remaining)
        return remaining
