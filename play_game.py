# coding=utf-8
from pokerbot.poker.poker import Poker
from pokerbot.ai.aiplayers import MonteCarloAI
from pokerbot.ai.holdemai import HoldemAI
import logging
import time

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    LOGGER = logging.getLogger("poker-console")
    LOGGER.setLevel(logging.INFO)

    start = time.time()
    players = [
        MonteCarloAI("Player 1", 2000),
        MonteCarloAI("Player 2", 2000),
        MonteCarloAI("Player 3", 2000),
        MonteCarloAI("Player 4", 2000),
        MonteCarloAI("Player 5", 2000),
        MonteCarloAI("Player 6", 2000),
        MonteCarloAI("Player 7", 2000),
        HoldemAI("Holdem", 2000)
    ]

    game = Poker(players)
    winner = game.play()

    LOGGER.info("Winner is :%s" % winner)
    LOGGER.info("GAME ENDED SUCCESSFULLY")
    LOGGER.info("Elasped Time: %d s." % (time.time() - start))
