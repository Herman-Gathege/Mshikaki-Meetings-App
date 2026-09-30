"""Pure domain rules for Mshikaki.

This package must not import from `app.db`, `app.api` or `app.services`. It holds
the rules that make the product trustworthy - state machines, permissions, XP
caps, summary building - so they can be tested in milliseconds with no database
and no HTTP. `tests/unit/test_domain_purity.py` enforces the rule.
"""
