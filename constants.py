# ~/Apps/vios/constants.py
class Constants:
    CHEATSHEET = r"""
VIOS CHEATSHEET

Navigation
  h               Parent directory (resets filter)
  l / Enter       Enter directory (resets filter) or open file
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

Other
  v               Create new file and open in Vim
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
  ,cp             Copy cd command to dir path to clipboard
  ,cl             Clear clipboard
"""
