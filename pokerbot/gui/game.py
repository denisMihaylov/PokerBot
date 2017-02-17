# coding=utf-8
import tkinter as tk
import queue
import threading
import logging
import os

from pokerbot.poker import poker as ppoker, player as players

FORMAT = '%(name)s - %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
LOGGER = logging.getLogger("poker-gui")
LOGGER.setLevel(logging.INFO)

event_queue = queue.Queue()
gui_to_logic_queue = queue.Queue()


class MESSAGES:
    REFRESH = "refresh"


class Menu(tk.Frame):
    def __init__(self, master):
        tk.Frame.__init__(self, master, height=500, width=200)

        # hold player widgets
        self.players = []
        tk.Label(self, text="Players").grid(row=0)
        self.players_frame = tk.Frame(self, bd=2, relief=tk.SUNKEN)
        for idx, title in enumerate(["Name", "Money", "Type"]):
            tk.Label(self.players_frame, text=title).grid(row=0, column=idx)
        self.add_player_button = tk.Button(self.players_frame, text="Add player", command=self.add_player)
        self.add_player_button.grid(row=1, columnspan=3)
        self.player_count = 0
        self.players_frame.grid(row=1)
        start_button = tk.Button(self,
                                 text='Start!',
                                 command=lambda: self.make_game())
        start_button.grid(row=3, column=0)
        self.add_player()
        self.add_player()
        self.pack()

    def add_player(self):
        self.player_count += 1
        row = self.player_count
        self.add_player_button.grid_forget()

        _name_widget = tk.Entry(self.players_frame,
                                textvariable=tk.StringVar(self.players_frame, "Player %d" % self.player_count))
        _name_widget.grid(row=row)
        _cash_var = tk.IntVar(self.players_frame, 1000)
        _cash_widget = tk.Entry(self.players_frame, textvariable=_cash_var)
        _cash_widget.grid(row=row, column=1)
        _type_var = tk.StringVar(self.players_frame, players.HumanPlayer.NAME)
        _type_widget = tk.OptionMenu(self.players_frame, _type_var, *[k for k in PLAYER_TYPES.keys()])
        _type_widget.grid(row=row, column=2)

        # add to players
        self.players.append((_name_widget, _cash_var, _type_var))
        self.add_player_button.grid(row=row + 1, columnspan=3)

    def make_game(self):
        for widget in self.grid_slaves():
            widget.grid_forget()
        _players = [PLAYER_TYPES[_type_widget.get()](_name_widget.get(), _cash_widget.get()) for
                    _name_widget, _cash_widget, _type_widget in self.players]
        return Game(self, ppoker.Poker(_players))


ENABLE = 'active'
DISABLE = 'disabled'


class CallButton(tk.Button):
    def __init__(self, master):
        tk.Button.__init__(self, master, text="call NA")
        self.action = players.Call

    def disable(self):
        self['state'] = DISABLE

    def enable(self):
        self['state'] = ENABLE

    def refresh(self, player, _round):
        if not player or not _round or not self.action.is_valid(player, _round):
            self.disable()
        else:
            self['text'] = 'Call %d' % _round.pot.amount_to_call(player)
            self['command'] = lambda: player.queue.put(self.action(player, _round))
            self.enable()


class CheckButton(tk.Button):
    def __init__(self, master):
        tk.Button.__init__(self, master, text="check NA")
        self.action = players.Check

    def disable(self):
        self['state'] = DISABLE

    def enable(self):
        self['state'] = ENABLE

    def refresh(self, player, _round):
        if not player or not _round or not self.action.is_valid(player, _round):
            self.disable()
        else:
            self['text'] = 'Check'
            self['command'] = lambda: player.queue.put(self.action(player, _round))
            self.enable()


class BetButton(tk.OptionMenu):
    def __init__(self, master):
        self.bet_var = tk.StringVar(master)
        self.bet_var.set("Bet NA")
        tk.OptionMenu.__init__(self, master, self.bet_var, "Bet NA")
        self.action = players.Bet

    def disable(self):
        self['state'] = DISABLE

    def enable(self):
        self['state'] = ENABLE

    def refresh(self, player, _round):
        self['menu'].delete(0, tk.END)
        if not player or not _round or not self.action.is_valid(player, _round):
            self.disable()
        else:
            self.bet_var.set("Bet ...")
            minimum, maximum = _round.pot.minimum_to_bet(player), player.money
            step = max((maximum - minimum) // 10, 1)
            LOGGER.info("minimum: %d, maximum: %d, step: %d" % (minimum, maximum, step))

            def bet(_amount):
                return lambda: player.queue.put(players.Bet(player, _round, _amount))

            # add 10 betting options
            for amount in range(minimum, maximum, step):
                self['menu'].add_command(label="Bet %d" % amount,
                                         command=bet(amount))
            # add all-in option
            self['menu'].add_command(label="All In! (%d)" % maximum, command=bet(maximum))
            self.enable()


class FoldButton(tk.Button):
    def __init__(self, master):
        tk.Button.__init__(self, master, text="fold NA")
        self.action = players.Fold

    def disable(self):
        self['state'] = DISABLE

    def enable(self):
        self['state'] = ENABLE

    def refresh(self, player, _round):
        if not player or not _round or not self.action.is_valid(player, _round):
            self.disable()
        else:
            self['text'] = 'Fold'
            self['command'] = lambda: player.queue.put(self.action(player, _round))
            self.enable()


class GUIPlayer(tk.Frame):
    def __init__(self, master, player, moves):
        tk.Frame.__init__(self, master)
        self.is_pc = not isinstance(player, GUIHumanPlayer)
        player.player_frame = self
        self.player = player
        self.moves = moves
        self.master = master
        self.row = player.id + 1
        self.name_label = tk.Label(master, text=player.name)
        self.cash_label = tk.Label(master, text=player.money)
        self.name_label.grid(row=self.row, column=0)
        self.cash_label.grid(row=self.row, column=1)

        self.pocket1 = tk.Label(master, text='na')
        self.pocket2 = tk.Label(master, text='na')
        self.pocket1.grid(row=self.row, column=2)
        self.pocket2.grid(row=self.row, column=3)

        self.pot = tk.Label(master, text='na')
        self.pot.grid(row=self.row, column=4)

        self.move_buttons = {
            "check": CheckButton(master),
            "bet": BetButton(master),
            "fold": FoldButton(master),
            "call": CallButton(master),
        }
        # place action buttons
        for offset, move in enumerate(self.move_buttons.values()):
            move.grid(row=self.row, column=5 + offset)
        self.refresh(None)

    def refresh(self, _round):
        for move_button in self.move_buttons.values():
            move_button.refresh(self.player, _round)
            if self.is_pc:
                move_button.disable()
        if _round:
            self.pot['text'] = _round.pot.player_bet(self.player)
            self.cash_label['text'] = "%d" % self.player.money
            if self.is_pc or self.player is not _round.betting_player:
                self.pocket1['text'] = u'\u258A'.encode("utf-8").decode()
                self.pocket1['fg'] = "black"
                self.pocket2['text'] = u'\u258A'.encode("utf-8").decode()
                self.pocket2['fg'] = "black"
                self.disable()
            else:
                # show cards
                if self.player.pocket:
                    self.pocket1['text'] = self.player.pocket[0]
                    self.pocket1['fg'] = self.player.pocket[0].color()
                    self.pocket2['text'] = self.player.pocket[1]
                    self.pocket2['fg'] = self.player.pocket[1].color()

    def disable(self):
        for move_button in self.move_buttons.values():
            move_button['state'] = DISABLE


class GUIHumanPlayer(players.BasePlayer):
    NAME = 'Human'

    def __init__(self, name, money):
        super(GUIHumanPlayer, self).__init__(name, money)
        LOGGER.debug("Creating Human player %s" % self.name)
        self.queue = queue.Queue()
        self.player_frame = None
        self.gui = None

    def interact(self, _round):
        LOGGER.debug("refreshing gui before %s's action", self.name)

        # get move
        return self.queue.get()

    def get_amount(self, _min, _max):
        self.queue.get()

    @staticmethod
    def gui_get_amount(_min, _max):
        while True:
            amount_selected_event = threading.Event()
            popup = tk.Toplevel()
            title = tk.Label(popup, text="How much [%d - %d]?" % (_min, _max), height=0, width=100)
            title.pack()

            amount_var = tk.StringVar()
            amount_var.set("%d" % _min)
            entry = tk.Entry(popup, textvariable=amount_var)
            entry.pack()

            confirm_amount = tk.Button(popup, text="ok", command=lambda: amount_selected_event.set())
            confirm_amount.pack()

            amount_selected_event.wait()
            if not amount_var.get().isdigit():
                print("amount not a number")
                continue
            amount = int(amount_var.get())
            if not _min <= amount <= _max:
                print("amount not in range")
                continue
            return amount


class Game(object):
    def __init__(self, frame, logic):

        self.frame = frame

        self.game_logic = logic

        for player in self.game_logic.players:
            player.gui = self

        for offset, title in enumerate("Player,Money,Card 1,Card2,Invested".split(",")):
            tk.Label(self.frame, text=title).grid(row=0, column=offset)

        self.player_frames = {}
        for player in self.game_logic.players:
            player_frame = GUIPlayer(self.frame, player, [])
            player_frame.grid(row=player.id + 1)
            self.player_frames[player] = player_frame

        tk.Label(self.frame, text="Community Cards:").grid(row=len(self.game_logic.players) + 1, columnspan=9)

        self.community_cards = [tk.Label(self.frame, text='') for _ in range(5)]
        for offset, community_card in enumerate(self.community_cards):
            community_card.grid(row=len(self.game_logic.players) + 2, column=offset)

        self.round_log = tk.Text(self.frame, height=10)
        self.round_log.grid(row=len(self.game_logic.players) + 3, columnspan=9)

        self.game_log = tk.Text(self.frame, height=10)
        self.game_log.grid(row=len(self.game_logic.players) + 4, columnspan=9)

        # start game only after gui initialized
        self.game_thread = threading.Thread(target=self.game_logic.play)
        self.game_thread.start()
        self.frame.after(10, func=self.process_event_queue)
        self.frame.pack()

    @staticmethod
    def get_amount(_min, _max):
        print("get amount %d - %d" % (_min, _max))

    def process_event_queue(self):
        # this is needed to let UI thread update widgets
        # (tkinter does not support multi threading)
        try:
            message = self.game_logic.event_queue.get(block=False)
            LOGGER.info("processing event: %s", message) # too much output

            if message:
                LOGGER.debug("Got event: %s" % str(message))
                _round = self.game_logic.current_round
                for player_frame in self.player_frames.values():
                    player = player_frame.player
                    if _round:
                        LOGGER.debug("Populating: %s" % player.name)
                        player_frame.refresh(_round)
                    LOGGER.debug("refreshing community cards %s" % str(_round.community_cards))
                    for label, card in zip(self.community_cards, _round.community_cards + [''] * 5):
                        label['text'] = card
                        if card:
                            LOGGER.debug("setting color to: %s" % card.color())
                            label['fg'] = card.color()
                self.refresh_logs()
            self.frame.pack()
        except queue.Empty:
            pass # No new events
        self.frame.after(10, func=self.process_event_queue)

    def refresh_logs(self):
        self.round_log.delete(1.0, tk.END)
        self.round_log.insert(tk.END, os.linesep.join(
            str(action) for action in reversed(self.game_logic.current_round.action_log[-10:])))
        self.game_log.delete(1.0, tk.END)
        self.game_log.insert(tk.END, os.linesep.join(
            str(action) for action in reversed(self.game_logic.log[-10:])))


PLAYER_TYPES = {c.NAME: c for c in [GUIHumanPlayer, players.RandomPlayer]}

try:
    from pokerbot.ai.aiplayers import SimpleAIPlayer, MonteCarloAI
    from pokerbot.ai.holdemai import HoldemAI

    PLAYER_TYPES[SimpleAIPlayer.NAME] = SimpleAIPlayer
    PLAYER_TYPES[MonteCarloAI.NAME] = MonteCarloAI
    PLAYER_TYPES[HoldemAI.NAME] = HoldemAI
except ImportError:
    print("no ai player")


def main():
    root = tk.Tk()
    root.title("PokerBot")
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    Menu(root)
    root.mainloop()
