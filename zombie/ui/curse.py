import curses
import logging

import eventlet

from zombie import shared
from zombie.ui import base


class CursesUi(base.Ui):
  def __init__(self, character, waddress):
    super(CursesUi, self).__init__(character, waddress)
    self.win = None

  def init(self):
    super(CursesUi, self).init()
    self._setup_curses()

  def _setup_curses(self):
    curses.wrapper(self._curses_app)

  def _curses_app(self, stdscr):
    self.win = stdscr

  def input_loop(self):
    while True:
      data = self.win.getch()
      print data
      eventlet.sleep(0.1)
