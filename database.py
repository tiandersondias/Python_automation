import pandas as pd
import psycopg


def read_query_dataframe(conn: psycopg.Connection, query: str) -> pd.DataFrame:
    """Execute a PostgreSQL query and return its rows as a DataFrame."""
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [column.name for column in cursor.description or ()]
    return pd.DataFrame(rows, columns=columns)
