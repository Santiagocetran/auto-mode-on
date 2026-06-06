"""Shared test helpers and fixtures."""

from unittest.mock import MagicMock


def make_query_mock(data=None, raises=None):
    """Return a MagicMock that simulates a supabase query-builder chain.

    Every chainable method (select, insert, update, eq, ilike, in_, limit, order)
    returns the same mock so the chain resolves cleanly. .execute() returns a
    response object with .data set to the provided list (or raises if given).
    """
    m = MagicMock()
    response = MagicMock()
    response.data = data if data is not None else []

    for method in ("select", "insert", "update", "eq", "ilike", "in_", "limit", "order"):
        getattr(m, method).return_value = m

    if raises is not None:
        m.execute.side_effect = raises
    else:
        m.execute.return_value = response

    return m


def make_db_mock(**table_data):
    """Return a mock db where each key is a table name mapped to (data, raises).

    Usage:
        db = make_db_mock(
            inbound_messages=([ {"id": "abc"} ], None),
            tasks=([], None),
        )
    Tables not listed in table_data return a permissive MagicMock.
    """
    table_mocks = {}
    for table_name, (data, raises) in table_data.items():
        table_mocks[table_name] = make_query_mock(data=data, raises=raises)

    db = MagicMock()
    db.table.side_effect = lambda name: table_mocks.get(name, make_query_mock(data=[]))
    return db
