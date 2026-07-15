# -*- coding: utf-8 -*-
"""On-demand installer for optional heavy dependencies (scikit-image, numba, ...).

Design follows the garmin_export mkgmap downloader: user-initiated only, no
silent auto-install, installs into a plugin-local libs directory added to
sys.path. See docs/PLAN_REALIZACII.md §7.
"""
