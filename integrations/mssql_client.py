"""
Read-only MSSQL client for the KGC Website UAT database.

Uses pymssql to connect to the Azure SQL database and fetch data
from the Orders and Customers tables.
"""

from __future__ import annotations

import logging
from typing import Any

import pymssql
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_connection():
    """Return a pymssql connection using Django settings."""
    cfg = settings.MSSQL_CONFIG
    return pymssql.connect(
        server=cfg["server"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        login_timeout=10,
        timeout=15,
    )


def _fetch_all(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Execute a read-only query and return rows as list of dicts."""
    conn = _get_connection()
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()


def get_orders_by_customer_id(customer_id: str) -> list[dict[str, Any]]:
    """Fetch all orders for a given CustomerId from the Orders table."""
    query = "SELECT * FROM Orders WHERE CustomerId = %s ORDER BY CreatedOn DESC"
    return _fetch_all(query, (customer_id,))


def get_customer_by_customer_id(customer_id: str) -> dict[str, Any] | None:
    """Fetch a single customer row by CustomerId from the Customers table."""
    query = "SELECT * FROM Customers WHERE CustomerId = %s"
    rows = _fetch_all(query, (customer_id,))
    return rows[0] if rows else None


def get_customer_by_email(email: str) -> dict[str, Any] | None:
    """Fetch a single customer row by Email from the Customers table."""
    query = "SELECT * FROM Customers WHERE Email = %s"
    rows = _fetch_all(query, (email,))
    return rows[0] if rows else None


def get_customer_orders_with_details(customer_id: str) -> dict[str, Any]:
    """
    Fetch a customer and all their orders from the external MSSQL database.
    Returns a dict with customer info and their orders list.
    """
    customer = get_customer_by_customer_id(customer_id)
    orders = get_orders_by_customer_id(customer_id)

    return {
        "customer": customer,
        "orders": orders,
        "total_orders": len(orders),
    }
