# ~/Apps/vios/constants.py
class Constants:
    CHEATSHEET = r"""
VIOS CHEATSHEET

Navigation
  Enter           Toggle Matrix (default) ↔ List view

  -- Matrix mode --
  h               Move left across streams
  l               Move right across streams
  j               Enter focused directory / open file
  k               Return to parent directory
  Ctrl+H          Page left (≈10% of streams)
  Ctrl+L          Page right (≈10% of streams)

  -- List mode --
  h               Parent directory (resets filter)
  l               Enter directory (resets filter) or open file
  j / k           Down / Up
  Ctrl+J          Jump down (≈10% of list)
  Ctrl+K          Jump up (≈10% of list)
  Ctrl+H          Go to previous directory in history
  Ctrl+L          Go to next directory in history
  Esc             Collapse inline expansions under current directory

Filtering (glob-style)
  /               Enter filter mode (type pattern)
                  • "rat" → matches items starting with "rat"
                  • "*.py" → all Python files
                  • "*test*" → contains "test"
                  • Press Enter to apply and persist filter
                  • Press / again to clear filter
  Esc             Cancel filter mode / clear pattern
  Ctrl+R          Clear filter, reset list, collapse expansions

Clipboard & Multi Operations
  m               Toggle mark on current item (✓) — auto-advance
  yy              Yank (copy) marked items (or current row) into clipboard
  dd              Cut marked items (or current row) into clipboard
  p               Paste clipboard into selected directory (or alongside selected file)
  x               Delete marked items or current entry immediately (bypass clipboard)

Command Mode
  :               Enter command mode
  :!<cmd>         Run shell command in current directory
  Esc             Cancel command mode
  Ctrl+P / Ctrl+N Navigate command history

Visual Mode
  v               Enter visual selection; press v again to add range to marks
  j / k           Extend/shrink selection while in visual mode
                  (Matrix mode freezes selected streams while active)
  Esc             Exit visual mode without adding range

Other
  ~               Collapse all expansions and return to ~
  c               Open config file in Vim
  t               Open terminal in current directory
  ?               Toggle this help
  q               Quit the app
  Ctrl+C          Quit immediately

Leader Commands (press "," first)
  ,xd             Toggle inline expansion/collapse for selection
  ,xc             Collapse all inline expansions
  ,dot            Toggle dotfiles visibility
  ,k / ,j         Jump to top / bottom
  ,sa / ,sma / ,smd Sort alphabetically / modified ↑ / modified ↓
  ,nf / ,nd       Create new file / directory in context
  ,rn             Rename selected item
  ,b              Toggle bookmark for current directory
  ,cp             Copy cd command for current path to clipboard
  ,cl             Clear clipboard contents
  ,cm             Clear all marks
  ,fo<token>      Open configured file shortcuts (e.g. ,fonotes)
  ,do<token>      Jump to directory shortcut (e.g. ,doga)
  ,to<token>      Open terminal at shortcut directory (e.g. ,toga)
  ,w<token>       Launch workspace shortcut (e.g. ,w1)
"""
