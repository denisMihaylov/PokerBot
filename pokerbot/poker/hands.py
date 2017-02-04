from collections import Counter
import logging

logging.basicConfig()
LOGGER = logging.getLogger('poker-hands')
LOGGER.setLevel(logging.WARN)


class InvalidHandException(Exception):
    pass


class Hand(object):

    rank = -1

    def __init__(self, cards):
        if len(cards) != 5:
            raise InvalidHandException("Card count was not 5!")
        self.cards = sorted(cards)
        self.values_counter = Counter([card.value for card in self.cards])

    def __gt__(self, other):

        LOGGER.debug("Comparing: %s and %s" % (self, other))
        if self.rank != other.rank:
            return self.rank > other.rank

        return self.compare_same(other)

    def __get_repeated_card(self, n):
        """
        get the n-th most repeated card. No promise is made about
        order of similarly repeated cards
        :param n: count rank of card to get
        (1, 2, 2, 3, 3)[1] -> 2 or 3, (1, 2, 2, 2)[0] -> 2 ...
        :return: nth most repeated card
        """
        return self.values_counter.most_common(5)[n]

    def compare_cards_high_to_low(self, other):
        card, other_card = None, None
        for card, other_card in zip(self.cards, other.cards):
            if card.value != other_card.value:
                break

        return card.value > other_card.value

    def compare_same(self, other):
        raise NotImplementedError("Can not compare an abstract hand!")

    @staticmethod
    def get_hand(cards):
        cards = sorted(cards)
        classification_candidates = [
            StraightFlush,
            FourOfAKind,
            FullHouse,
            Flush,
            Straight,
            ThreeOfAKind,
            TwoPairs,
            Pair,
        ]
        for candidate in classification_candidates:
            if candidate.is_valid(cards):
                LOGGER.debug("%s: %s" % (candidate.__name__, str(cards)))
                return candidate(cards)

        # nothing identified, play using highest cards
        return HighCard(cards)

    @staticmethod
    def is_valid(cards):
        raise NotImplemented("is_valid not implemented for abstract hand!")

    def __repr__(self):
        return "%s - %s" % (self.__class__, ','.join([
            str(card.value) + card.suit[0] for card in self.cards]))

    def __str__(self):
        return ", ".join(str(c) for c in self.cards)


class StraightFlush(Hand):

    rank = 8

    def __init__(self, cards):
        super(StraightFlush, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        sf = Flush.is_valid(cards) and Straight.is_valid(cards)
        return sf

    def compare_same(self, other):
        return self.compare_cards_high_to_low(other)


class FourOfAKind(Hand):

    rank = 7

    def __init__(self, cards):
        super(FourOfAKind, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        counter = Counter([card.value for card in cards])
        return max(counter.values()) == 4

    def __repeated_card4(self):
        return self.values_counter.most_common(1)[0]

    def compare_same(self, other):
        return self.__repeated_card4() > other.__repeated_card4()


class FullHouse(Hand):

    rank = 6

    def __init__(self, cards):
        super(FullHouse, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        counter = Counter([card.value for card in cards])
        return 2 in counter.values() and 3 in counter.values()

    def __repeated_card3(self):
        return self.values_counter.most_common(1)[0]

    def compare_same(self, other):
        return self.__repeated_card3() > other.__repeated_card3()


class Flush(Hand):

    rank = 5

    def __init__(self, cards):
        super(Flush, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        f = all(card.suit == cards[0].suit for card in cards)
        if f:
            LOGGER.debug("found flush!")
        return f

    def compare_same(self, other):
        return self.compare_cards_high_to_low(other)


class Straight(Hand):

    rank = 4

    def __init__(self, cards):
        super(Straight, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        values = sorted([card.value for card in cards])
        if values[-1] == 14 and values[0] == 2:
            return values[1:4] == [3, 4, 5]
        return values == range(values[0], values[0] + 5)

    def compare_same(self, other):
        self.compare_cards_high_to_low(other)


class ThreeOfAKind(Hand):

    rank = 3

    def __init__(self, cards):
        super(ThreeOfAKind, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        counter = Counter([card.value for card in cards])
        return max(counter.values()) == 3

    def __repeated_card3(self):
        return self.values_counter.most_common(1)[0]

    def compare_same(self, other):
        return self.__repeated_card3() > other.__repeated_card3()


class TwoPairs(Hand):

    rank = 2

    def __init__(self, cards):
        super(TwoPairs, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        counter = Counter([card.value for card in cards])
        return sorted(counter.values())[-2:] == [2, 2]

    def __repeated_cards2_2(self):
        return self.values_counter.most_common(2)

    def compare_same(self, other):
        high_pair, low_pair = self.__repeated_cards2_2()
        other_high_pair, other_low_pair = other.__repeated_cards2_2()
        if high_pair != other_high_pair:
            return high_pair > other_high_pair
        if low_pair != other_low_pair:
            return low_pair > other_low_pair

        return self.compare_cards_high_to_low


class Pair(Hand):

    rank = 1

    def __init__(self, cards):
        super(Pair, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        counter = Counter([card.value for card in cards])
        return max(counter.values()) == 2

    def __repeated_cards2(self):
        return self.values_counter.most_common(1)[0]

    def compare_same(self, other):
        if self.__repeated_cards2() != other.__repeated_cards2():
            return self.__repeated_cards2() > other.__repeated_cards2()

        return self.compare_cards_high_to_low(other)


class HighCard(Hand):

    rank = 0

    def __init__(self, cards):
        super(HighCard, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        return

    def compare_same(self, other):
        return self.compare_cards_high_to_low(other)
