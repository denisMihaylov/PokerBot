from collections import Counter
import logging

LOGGER = logging.getLogger('poker-hands')
LOGGER.setLevel(logging.ERROR)


class InvalidHandException(Exception):
    pass


class Hand(object):

    rank = -1

    def __init__(self, cards):
        if len(cards) != 5:
            raise InvalidHandException("Card count was not 5!")
        self.cards = sorted(cards)
        self._values_counter = Counter([card.value for card in self.cards])

    def __gt__(self, other):

        LOGGER.debug("Comparing: %s and %s" % (self, other))
        if self.rank != other.rank:
            return self.rank > other.rank

        return self._compare_same(other)

    def _compare_cards_high_to_low(self, other):
        card, other_card = None, None
        for card, other_card in zip(self.cards, other.cards):
            if card.value != other_card.value:
                break

        return card.value > other_card.value

    def _compare_same(self, other):
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

    def _filter_most_common(self):
        return filter(
            lambda a: a != self._values_counter.most_common(1)[0],
            self.cards)

    def _compare_highest(self, other):
        return self.cards[-1] > other.cards[-1]


class StraightFlush(Hand):

    rank = 8

    def __init__(self, cards):
        super(StraightFlush, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        return Flush.is_valid(cards) and Straight.is_valid(cards)

    def _compare_same(self, other):
        return self._compare_highest(other)


class FourOfAKind(Hand):

    rank = 7

    def __init__(self, cards):
        super(FourOfAKind, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        counter = Counter([card.value for card in cards])
        return max(counter.values()) == 4

    def __repeated_card4(self):
        return self._values_counter.most_common(1)[0]

    def _compare_same(self, other):
        if self.__repeated_card4() == other.__repeated_card4():
            return self._filter_most_common() > other._filter_most_common()
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
        return self._values_counter.most_common(1)[0]

    def _compare_same(self, other):
        if self.__repeated_card3() == other.__repeated_card3():
            first = self._values_counter.most_common(2)[1]
            second = other._values_counter.most_common(2)[1]
            return first > second
        return self.__repeated_card3() > other.__repeated_card3()


class Flush(Hand):

    rank = 5

    def __init__(self, cards):
        super(Flush, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        return all(card.suit == cards[0].suit for card in cards)

    def _compare_same(self, other):
        return self._compare_highest(other)


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

    def _compare_same(self, other):
        self._compare_highest(other)


class ThreeOfAKind(Hand):

    rank = 3

    def __init__(self, cards):
        super(ThreeOfAKind, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        counter = Counter([card.value for card in cards])
        return max(counter.values()) == 3

    def __repeated_card3(self):
        return self._values_counter.most_common(1)[0]

    def _compare_same(self, other):
        if self.__repeated_card3() == other.__repeated_card3():
            first = self._filter_most_common()
            second = other._filter_most_common()
            return first > second
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
        return self._values_counter.most_common(2)

    def _compare_same(self, other):
        high_pair, low_pair = sorted(self.__repeated_cards2_2())
        other_high_pair, other_low_pair = sorted(other.__repeated_cards2_2())
        if high_pair != other_high_pair:
            return high_pair > other_high_pair
        if low_pair != other_low_pair:
            return low_pair > other_low_pair
        first = self._values_counter.most_common(3)[-1]
        second = other._values_counter.most_common(3)[-1]
        return first > second


class Pair(Hand):

    rank = 1

    def __init__(self, cards):
        super(Pair, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        counter = Counter([card.value for card in cards])
        return max(counter.values()) == 2

    def __repeated_cards2(self):
        return self._values_counter.most_common(1)[0]

    def _compare_same(self, other):
        if self.__repeated_cards2() != other.__repeated_cards2():
            return self.__repeated_cards2() > other.__repeated_cards2()
        return self._filter_most_common() > other._filter_most_common()


class HighCard(Hand):

    rank = 0

    def __init__(self, cards):
        super(HighCard, self).__init__(cards)

    @staticmethod
    def is_valid(cards):
        return

    def _compare_same(self, other):
        return self._compare_highest(other)
