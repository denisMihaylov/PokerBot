from pokerbot.poker.poker import Poker
from pokerbot.ai.aiplayers import MonteCarloAI
import logging
import time

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("poker-console")
LOGGER.setLevel(logging.INFO)

start = time.time()
players = [
    MonteCarloAI("Player 1", 1000),
    MonteCarloAI("Player 2", 1000),
    MonteCarloAI("Player 3", 1000),
    MonteCarloAI("Player 4", 1000)
]

game = Poker(players)
winner = game.play()

LOGGER.info("Winner is :%s" % winner)
LOGGER.info("GAME ENDED SUCCESSFULLY")
LOGGER.info("Elasped Time: %d s." % (time.time() - start))