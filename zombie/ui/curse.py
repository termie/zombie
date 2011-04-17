from __future__ import absolute_import

import curses
import logging
from curses import textpad

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
    curses.noecho()
    #self.win.border(0, 0, 0, 0, 0, 0, 0, 0)
    self.max_y, self.max_x = self.win.getmaxyx()
    self.win.hline(self.max_y - 2, 0, curses.ACS_HLINE, self.max_x)
    self.textwin = self.win.subwin(1, self.max_x, self.max_y - 1, 0)
    self.textbox = textpad.Textbox(self.textwin)
    self.win.refresh()

  def input_loop(self):
    while True:
      data = self.textbox.edit()
      self.handle_input(data)
      self.win.move(2, 0)
      self.win.deleteln()
      self.win.insertln()
      self.win.insstr(2, 0, data)
      self.win.hline(self.max_y - 2, 0, curses.ACS_HLINE, self.max_x)
      self.textwin.clear()
      self.win.refresh()
      #data = self.win.getch()
      #print self.textbox.edit()
      #self.textbox.do_command(data)
      #print data
      eventlet.sleep(0.1)
