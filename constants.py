# ~/Apps/vios/constants.py
class Constants:
    CHEATSHEET = r"""
VIOS CHEATSHEET

Navigation
  Enter (Return)  Toggle Matrix (default) ↔ List view

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
  y               Yank (copy) all marked items into clipboard immediately
  yy              Yank current row into clipboard when nothing marked
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
  .               Repeat last repeatable command
  t               Open terminal in current directory
  ?               Toggle this help
  q               Quit the app
  Ctrl+C          Quit immediately

Leader Commands (press "," first)
  ,xr             Toggle inline expansion/collapse for selection
  ,xc             Collapse all inline expansions
  ,xar            Expand all directories recursively
  ,dot            Toggle dotfiles visibility
  ,conf           Open config file in Vim and reload
  ,k / ,j         Jump to top / bottom
  ,sa / ,sma / ,smd Sort alphabetically / modified ↑ / modified ↓
  ,nf / ,nd       Create new file / directory in context
  ,rn             Rename selected item
  ,b              Toggle bookmark for current directory
  ,cl             Clear clipboard contents
  ,cm             Clear all marks
"""
