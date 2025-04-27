from typing import List, Dict


def generate_table_documentation(table_data: List[Dict]) -> List[Dict]:
    def format_columns(columns: List[Dict]) -> str:
        """Helper function to format column data"""
        return ", ".join([f"{col['column_name']} ({col['data_type']})" for col in columns])

    def format_relations(relations: List[Dict]) -> str:
        """Helper function to format foreign key relations"""
        return "\nIt has foreign key relations:\n" + "\n".join([
            f"- {rel['column']} => {rel['references']['schema']}.{rel['references']['table']}.{rel['references']['column']}"
            for rel in relations
        ])

    documents = []
    
    for table in table_data:
        schema = table["schema"]
        name = table["table_name"]
        columns_text = format_columns(table["columns"])
        doc_text = f"Table '{name}' in schema '{schema}' has columns: {columns_text}."

        if table["relations"]:
            doc_text += format_relations(table["relations"])

        documents.append({
            "text": doc_text,
            "metadata": {
                "table_name": name,
                "schema": schema
            }
        })

    return documents
