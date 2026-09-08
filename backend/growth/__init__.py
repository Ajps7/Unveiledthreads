"""Network Effects Command Center — the growth engine behind /admin/growth.

Layering, deliberately strict:

  benchmarks.py  bands, stage gates and the reasoning behind each number
  metrics.py     pure formulas over plain data (liquidity, density, cohorts)
  diagnostics.py loop scoring, named failure modes, stage sequencing
  playbook.py    the play library, triggered and ranked by ICE then by stage
  simulator.py   the flywheel model with its feedback loops closed
  narrative.py   the executive memo
  collector.py   the ONLY module that touches Mongo

Everything except `collector` is stdlib-only and side-effect free, so the
judgment can be unit-tested against synthetic marketplaces without a
database, a web server, or waiting for real traffic.
"""
