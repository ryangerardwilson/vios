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
  j               Down
  k               Up
  Ctrl+J          Jump down (≈10% of list)
  Ctrl+K          Jump up (≈10% of list)
  Ctrl+H          Go to previous directory in history
  Ctrl+L          Go to next directory in history
  e               Expand/collapse selected directory inline
  Esc             Collapse all expansions and return to ~

Filtering (glob-style)
  /               Enter filter mode (type pattern)
                  • "rat" → matches items starting with "rat"
                  • "*.py" → all Python files
                  • "*test*" → contains "test"
                  • Press Enter to apply and persist filter
                  • Press / again to clear filter
  Ctrl+R          Clear filter and show all items

Clipboard & Multi Operations
  yy              Yank (copy) marked items (or current row) into clipboard
  dd              Cut marked items (or current row) into clipboard
  x               Delete marked items or current entry immediately (bypass clipboard)
  m               Toggle mark on current item (✓) — auto-advance
  p               Paste clipboard into selected directory (or alongside selected file)

Command Mode
  :               Enter command mode
  :!<cmd>         Run shell command in current directory

Visual Mode
  v               Enter visual selection; press v again to add range to marks
  j / k           Extend/shrink selection while in visual mode
                  (Matrix mode freezes selected streams while active)
  Esc             Exit visual mode without adding range

Other
  t               Open terminal in current directory
  .               Toggle show hidden files/dirs
  ?               Toggle this help
  Ctrl+C          Quit the app

Leader Commands (prefix ",")
  ,k              Jump to top
  ,j              Jump to bottom
  ,sa             Sort alphabetically (default)
  ,sma            Sort by modified date ↑ (oldest first)
  ,smd            Sort by modified date ↓ (newest first)
  ,nf             Create new file (no open)
  ,nd             Create new directory
  ,rn             Rename selected item
  ,fo<token>      Open configured file shortcuts (e.g. ,fonotes)
  ,do<token>      Jump to directory shortcut (e.g. ,doga)
  ,to<token>      Open terminal at shortcut directory (e.g. ,toga)
  ,w<token>       Launch workspace shortcut (e.g. ,w1)
  ,cp             Copy cd command to dir path to clipboard
  ,cl             Clear clipboard
"""
