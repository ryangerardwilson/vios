# ~/Apps/vios/modules/constants.py
class Constants:
    CHEATSHEET = r"""
VIOS CHEATSHEET

Navigation
  h               Parent directory (resets filter)
  l / Enter       Enter directory (resets filter) or open file
  j               Down
  k               Up
  ,k              Jump to top
  ,j              Jump to bottom

Filtering (glob-style)
  /               Enter filter mode (type pattern)
                  • "rat" → matches items starting with "rat"
                  • "*.py" → all Python files
                  • "*test*" → contains "test"
                  • Press Enter to apply and persist filter
                  • Press / again to clear filter
  Ctrl+R          Clear filter and show all items

Clipboard & Multi Operations
  y               Start yank (copy) — yy to confirm
  d               Delete marked items OR start cut/delete — dd to confirm
  m               Toggle mark on current item (✓) — auto-advance
  p               Copy marked items here (overwrite) OR paste single clipboard
  x               Cut/move marked items here (overwrite)
  Ctrl+L          Clear clipboard

File Opening
  • Text files (.py, .txt, .md, etc.) → Vim
  • PDF files → Zathura

Other
  v               Create new file and open in Vim
  nf              Create new file (no open)
  nd              Create new directory
  rn              Rename selected item
  t               Open terminal in current directory
  .               Toggle show hidden files/dirs
  ?               Toggle this help
  Ctrl+C          Quit the app
"""
