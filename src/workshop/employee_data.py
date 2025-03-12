import json
import logging
import os
from typing import Optional
import aiosqlite
import pandas as pd
from terminal_colors import TerminalColors as tc

DATA_BASE = "/workspaces/build-your-first-agent-with-azure-ai-agent-service-workshop/src/workshop/database/employee-data.db"

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class EmployeeData:
    conn: Optional[aiosqlite.Connection]

    def __init__(self: "EmployeeData") -> None:
        self.conn = None

    async def connect(self: "EmployeeData") -> None:
        env = os.getenv("ENVIRONMENT", "local")
        db_uri = f"file:{DATA_BASE}?mode=ro"

        try:
            self.conn = await aiosqlite.connect(db_uri, uri=True)
            logger.debug("Database connection opened.")
        except aiosqlite.Error as e:
            logger.exception("An error occurred", exc_info=e)
            self.conn = None

    async def close(self: "EmployeeData") -> None:
        if self.conn:
            await self.conn.close()
            logger.debug("Database connection closed.")

    async def __get_table_names(self: "EmployeeData") -> list:
        """Return a list of table names."""
        table_names = []
        async with self.conn.execute("SELECT name FROM sqlite_master WHERE type='table';") as tables:
            table_names = [table[0] async for table in tables if table[0] != "sqlite_sequence"]
        return table_names

    async def __get_column_info(self: "EmployeeData", table_name: str) -> list:
        """Return a list of tuples containing column names and their types."""
        column_info = []
        async with self.conn.execute(f"PRAGMA table_info('{table_name}');") as columns:
            column_info = [f"{col[1]}: {col[2]}" async for col in columns]
        return column_info

    async def get_database_info(self: "EmployeeData") -> str:
        """Return a string containing the database schema information and common query fields."""
        table_dicts = []
        for table_name in await self.__get_table_names():
            columns_names = await self.__get_column_info(table_name)
            table_dicts.append({"table_name": table_name, "column_names": columns_names})

        database_info = "\n".join(
            [
                f"Table {table['table_name']} Schema: Columns: {', '.join(table['column_names'])}"
                for table in table_dicts
            ]
        )
        return database_info + "\n\n"

    async def async_fetch_employee_data_using_sqlite_query(self: "EmployeeData", sqlite_query: str) -> str:
        """
        This function is used to answer user questions about Contoso employee data by executing SQLite queries against the database.

        :param sqlite_query: The input should be a well-formed SQLite query to extract information based on the user's question. The query result will be returned as a JSON object.
        :return: Return data in JSON serializable format.
        :rtype: str
        """

        print(f"\n{tc.BLUE}Function Call Tools: async_fetch_employee_data_using_sqlite_query{tc.RESET}\n")
        print(f"{tc.BLUE}Executing query: {sqlite_query}{tc.RESET}\n")

        try:
            # Perform the query asynchronously
            async with self.conn.execute(sqlite_query) as cursor:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]

            if not rows:  # No need to create DataFrame if there are no rows
                return json.dumps("The query returned no results. Try a different question.")
            data = pd.DataFrame(rows, columns=columns)
            return data.to_json(index=False, orient="split")

        except Exception as e:
            return json.dumps({"SQLite query failed with error": str(e), "query": sqlite_query})
    
    async def async_add_employee_if_not_exists(self: "EmployeeData", name: str, age: int, department: str, position: str, salary: float, year_joined: int, region: str) -> str:
        """
        Add a new employee to the database if the employee does not already exist.

        :param name: The name of the employee.
        :param age: The age of the employee.
        :param department: The department of the employee.
        :param position: The position of the employee.
        :param salary: The salary of the employee.
        :param year_joined: The year the employee joined.
        :param region: The region of the employee.
        :return: A message indicating whether the employee was added or already exists.
        """
        try:
            # Check if the employee already exists
            query = "SELECT * FROM employees WHERE name = ?"
            async with self.conn.execute(query, (name,)) as cursor:
                existing_employee = await cursor.fetchone()

            if existing_employee:
                return json.dumps({"message": "Employee already exists.", "employee": existing_employee})

            # Insert the new employee
            insert_query = """
            INSERT INTO employees (name, age, department, position, salary, year_joined, region)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            await self.conn.execute(insert_query, (name, age, department, position, salary, year_joined, region))
            await self.conn.commit()
            return json.dumps({"message": "Employee added successfully."})

        except Exception as e:
            return json.dumps({"error": str(e)})
