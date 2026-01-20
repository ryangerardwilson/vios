# ~/Apps/vios/modules/constants.py
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
  ,k              Jump to top
  ,j              Jump to bottom
  e               Expand/collapse selected directory inline

Sorting
  ,sa             Sort alphabetically (default)
  ,sma            Sort by modified date ↑ (oldest first)
  ,smd            Sort by modified date ↓ (newest first)

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
  p               Copy marked items here (overwrite) OR paste saved clipboard batch
  ,cl             Clear clipboard

Other
  v               Create new file and open in Vim
  nf              Create new file (no open)
  nd              Create new directory
  rn              Rename selected item
  cp              Copy cd command to dir path to clipboard
  t               Open terminal in current directory
  .               Toggle show hidden files/dirs
  ?               Toggle this help
  Ctrl+C          Quit the app
"""
