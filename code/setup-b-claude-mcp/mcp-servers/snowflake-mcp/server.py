"""
Custom Snowflake MCP Server for Claude integration.
Provides tools for schema exploration and query execution.
"""

import os
import asyncio
from typing import Optional
import snowflake.connector
from mcp.server import Server
from mcp.types import Tool, TextContent, ListToolsResult


# Initialize MCP server
server = Server("snowflake-mcp")

# Global connection (in production, use proper connection pooling)
_connection: Optional[snowflake.connector.SnowflakeConnection] = None


def get_connection() -> snowflake.connector.SnowflakeConnection:
    """Get or create Snowflake connection."""
    global _connection
    if _connection is None or _connection.is_closed():
        _connection = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
        )
    return _connection


@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available Snowflake tools."""
    return [
        Tool(
            name="list_databases",
            description="List all accessible databases in Snowflake",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_schemas",
            description="List all schemas in a database",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "Database name",
                    }
                },
                "required": ["database"],
            },
        ),
        Tool(
            name="list_tables",
            description="List all tables in a schema",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string"},
                    "schema": {"type": "string"},
                },
                "required": ["database", "schema"],
            },
        ),
        Tool(
            name="describe_table",
            description="Get detailed schema information for a table including column names, types, and descriptions",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string"},
                    "schema": {"type": "string"},
                    "table": {"type": "string"},
                },
                "required": ["database", "schema", "table"],
            },
        ),
        Tool(
            name="execute_query",
            description="Execute a read-only SQL query and return results. Only SELECT queries are allowed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SELECT query to execute",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum rows to return (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="get_sample_data",
            description="Get sample rows from a table",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string"},
                    "schema": {"type": "string"},
                    "table": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["database", "schema", "table"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if name == "list_databases":
            cursor.execute("SHOW DATABASES")
            databases = [row[1] for row in cursor.fetchall()]
            return [TextContent(text="\n".join(databases))]

        elif name == "list_schemas":
            database = arguments["database"]
            cursor.execute(f"SHOW SCHEMAS IN DATABASE {database}")
            schemas = [row[1] for row in cursor.fetchall()]
            return [TextContent(text="\n".join(schemas))]

        elif name == "list_tables":
            database = arguments["database"]
            schema = arguments["schema"]
            cursor.execute(f"SHOW TABLES IN {database}.{schema}")
            tables = [row[1] for row in cursor.fetchall()]
            return [TextContent(text="\n".join(tables))]

        elif name == "describe_table":
            database = arguments["database"]
            schema = arguments["schema"]
            table = arguments["table"]

            # Get table description
            cursor.execute(f"""
                SELECT COMMENT
                FROM {database}.INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
            """)
            table_comment = cursor.fetchone()
            table_desc = table_comment[0] if table_comment and table_comment[0] else "No description"

            # Get column details
            cursor.execute(f"DESCRIBE TABLE {database}.{schema}.{table}")
            columns = cursor.fetchall()

            result = f"Table: {database}.{schema}.{table}\n"
            result += f"Description: {table_desc}\n\n"
            result += "Columns:\n"

            for col in columns:
                col_name = col[0]
                col_type = col[1]
                nullable = "NULL" if col[3] == "Y" else "NOT NULL"
                result += f"  - {col_name} ({col_type}) {nullable}\n"

            return [TextContent(text=result)]

        elif name == "execute_query":
            sql = arguments["sql"].strip()
            limit = arguments.get("limit", 100)

            # Security: Only allow SELECT queries
            if not sql.upper().startswith("SELECT"):
                return [TextContent(text="Error: Only SELECT queries are allowed")]

            # Add limit if not present
            if "LIMIT" not in sql.upper():
                sql = f"{sql} LIMIT {limit}"

            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            # Format as table
            result = " | ".join(columns) + "\n"
            result += "-" * len(result) + "\n"
            for row in rows:
                result += " | ".join(str(v) for v in row) + "\n"

            return [TextContent(text=result)]

        elif name == "get_sample_data":
            database = arguments["database"]
            schema = arguments["schema"]
            table = arguments["table"]
            limit = arguments.get("limit", 10)

            cursor.execute(f"SELECT * FROM {database}.{schema}.{table} LIMIT {limit}")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            result = f"Sample data from {database}.{schema}.{table}:\n\n"
            result += " | ".join(columns) + "\n"
            result += "-" * 50 + "\n"
            for row in rows:
                result += " | ".join(str(v)[:20] for v in row) + "\n"

            return [TextContent(text=result)]

        else:
            return [TextContent(text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(text=f"Error: {str(e)}")]
    finally:
        cursor.close()


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
