# -*- coding: utf-8 -*-
"""Shared validation and safe defaults for the additional UI catalogues.

The English catalogue remains the key contract.  A locale must never expose an
English fallback to the user: values that are not a dedicated label or message
are replaced with a concise, localised help text.  This deliberately makes a
missing detailed translation visible during the human language pass without
leaving a mixed-language interface in a release build.
"""

import re

from .en import translations as ENGLISH


def build_catalog(overrides, generic_label, help_prefix, text_prefix):
    """Return a complete catalogue with placeholder parity to English.

    ``overrides`` contains the reviewed controls, messages and option labels.
    The remaining verbose help strings receive a localised concise message;
    this is preferable to silently displaying the English source language.
    """
    result = {}
    for key, source in ENGLISH.items():
        value = overrides.get(key)
        if value is None:
            prefix = help_prefix if key.startswith('tip_') else text_prefix
            value = prefix + generic_label
        fields = re.findall(r'\{\d+\}', source)
        for field in fields:
            if field not in value:
                value += ' ' + field
        result[key] = value
    if set(result) != set(ENGLISH):
        raise RuntimeError('translation key parity failure')
    return result
