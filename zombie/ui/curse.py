from __future__ import absolute_import

import curses
import logging
from curses import textpad

import eventlet

from zombie import shared
from zombie.ui import base

REALLY_BIG_STRING = """ASDBASDKL:AJSDLKAJSDAKLSJD
ASDKLJASDLAJKSD
ASD
AKLSDJLAKSDJFASDFASDASDl
ASDLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLASDASDASDLLLLLLLLLLLLLLLLLLLASDASDASDASD
Asdasdlasdl
asdafKLASDAKLSD

ASDASDASDASD
"""

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
    self.textwin = self.win.subwin(1, self.max_x, self.max_y - 1, 0)
    self.textbox = textpad.Textbox(self.textwin)
    self.topbar = self.win.subwin(1, self.max_x, 0, 0)
    self.main = self.win.subwin(self.max_y - 4, self.max_x, 2, 0)
    self.main_y, self.main_x = self.main.getmaxyx()
    self.draw_sections()
    self.win.refresh()
    self.replace(REALLY_BIG_STRING)

  def topbar(self, text):
    self.topbar.clear()
    self.topbar.addnstr(0, 0, text, self.max_x)
    self.topbar.refresh()

  def replace(self, text):
    """Replace the main area with the text."""
    self.main.clear()
    self.main.addstr(0, 0, text)
    self.main.refresh()

  def append(self, text):
    """Append text to the main area, scrolling it up."""
    while text:
      line = text[:self.main_x - 1]
      text = text[self.main_x - 1:]
      self._append_line(line)
    self.main.refresh()

  def _append_line(self, text):
    self.main.move(0, 0)
    self.main.deleteln()
    self.main.move(self.main_y - 1, 0)
    self.main.clrtoeol()
    self.main.addnstr(self.main_y - 1, 0, text, self.main_x)

  def draw_sections(self):
    """Redraw the appropriate screen sections."""
    self.win.hline(1, 0, curses.ACS_HLINE, self.max_x)
    self.win.hline(self.max_y - 2, 0, curses.ACS_HLINE, self.max_x)
    pass

  def refresh(self):
    """Refresh the screen."""
    pass

  def input_loop(self):
    while True:
      data = self.textbox.edit()
      self.handle_input(data)
      self.textwin.clear()
      self.textwin.refresh()
      eventlet.sleep(0.1)

  def _cmd_connect(self, cmd, args):
    super(CursesUi, self)._cmd_connect(cmd, args)
    self.append('Connected to %s' % args)
    self.topbar('(%s)' % args)
