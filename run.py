"""Entry point for PyInstaller (it needs a script, not ``-m``)."""

from klicker.__main__ import main

raise SystemExit(main())
