import os
from dotenv import load_dotenv
import psycopg2
from src.constants import *
# Load environment variables
load_dotenv('./.env_vars')

class DatabaseConnection:
    """Handles database connection and provides a cursor."""
    
    def __init__(self):
        self.host = HOST
        self.port = PORT
        self.database = DATABASE
        self.username = USERNAME  
        self.password = PASSWORD
        
        if not self.password:
            raise ValueError("Password is missing in environment variables.")

    def __enter__(self):
        """Establish the database connection and return the cursor."""
        self.conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.username,
            password=self.password
        )
        self.cur = self.conn.cursor()
        return self.cur

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close cursor and connection when exiting the context."""
        if hasattr(self, 'cur'):
            self.cur.close()
        if hasattr(self, 'conn'):
            self.conn.close()


class SchemaLoader:
    
    def __init__(self):
        self.schemas = ['location_management']

    def load_schema_definitions(self, schemas=None):
        """Loads the schema definitions and foreign key relations."""
        schemas = schemas or self.schemas  # Default to 'public' if no schemas provided
        table_info = []

        with DatabaseConnection() as cur:
            # Fetch all schema names except system schemas
            cur.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog');
            """)
            all_schemas = [row[0] for row in cur.fetchall()]
            schemas = schemas or all_schemas

            # Load the schema definition for each schema
            for schema in schemas:
                cur.execute("""
                    SELECT table_name, column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = %s;
                """, (schema,))
                rows = cur.fetchall()

                for table_name, column_name, data_type in rows:
                    table_data = next(
                        (item for item in table_info if item["table_name"] == table_name and item["schema"] == schema),
                        None
                    )
                    if table_data:
                        table_data["columns"].append({
                            "column_name": column_name,
                            "data_type": data_type
                        })
                    else:
                        table_info.append({
                            "schema": schema,
                            "table_name": table_name,
                            "columns": [{"column_name": column_name, "data_type": data_type}],
                            "relations": []
                        })

            # Fetch foreign key relations
            cur.execute("""
                SELECT
                    tc.table_schema AS source_schema,
                    tc.table_name AS source_table,
                    kcu.column_name AS source_column,
                    ccu.table_schema AS target_schema,
                    ccu.table_name AS target_table,
                    ccu.column_name AS target_column
                FROM
                    information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = ANY(%s);
            """, (schemas,))

            fk_rows = cur.fetchall()
            for source_schema, source_table, source_column, target_schema, target_table, target_column in fk_rows:
                table_data = next(
                    (item for item in table_info if item["table_name"] == source_table and item["schema"] == source_schema),
                    None
                )
                if table_data:
                    table_data["relations"].append({
                        "column": source_column,
                        "references": {
                            "schema": target_schema,
                            "table": target_table,
                            "column": target_column
                        }
                    })
            
        return table_info

def get_posrtgres_uri():
    postgres_uri = f"postgresql+psycopg2://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
    return postgres_uri


if __name__ == "__main__":
# Example usage:
    db_manager = SchemaLoader()
    schemas = db_manager.load_schema_definitions()
    print(schemas)