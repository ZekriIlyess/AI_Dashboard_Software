from datetime import datetime
from typing import List, Dict, Any

from nexus_types.database import SchemaInfo, TableInfo, ColumnInfo, ForeignKeyInfo, IndexInfo


class SchemaExtractor:
    """
    Extracts database schema (tables, columns, types, relationships).
    Currently implemented for PostgreSQL.
    """

    def __init__(self, pool):
        self.pool = pool

    async def extract_postgres_schema(self) -> SchemaInfo:
        """Extract schema from PostgreSQL information_schema."""
        
        # 1. Get Tables
        tables_query = """
            SELECT table_name, table_schema
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            AND table_type = 'BASE TABLE';
        """
        
        # 2. Get Columns
        columns_query = """
            SELECT table_name, column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema');
        """
        
        # 3. Get Primary Keys
        pks_query = """
            SELECT kcu.table_name, kcu.column_name
            FROM information_schema.table_constraints tco
            JOIN information_schema.key_column_usage kcu 
              ON kcu.constraint_name = tco.constraint_name
              AND kcu.constraint_schema = tco.constraint_schema
            WHERE tco.constraint_type = 'PRIMARY KEY';
        """
        
        # 4. Get Foreign Keys
        fks_query = """
            SELECT
                tc.table_name, kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE constraint_type = 'FOREIGN KEY';
        """
        
        async with self.pool.acquire() as conn:
            # We would normally execute these queries concurrently
            # For simplicity in this scaffold, we do them sequentially
            table_rows = await conn.fetch(tables_query)
            column_rows = await conn.fetch(columns_query)
            pk_rows = await conn.fetch(pks_query)
            fk_rows = await conn.fetch(fks_query)
            
        # Organize the data
        tables_dict = {}
        
        for row in table_rows:
            tables_dict[row['table_name']] = {
                'name': row['table_name'],
                'schema_name': row['table_schema'],
                'columns': [],
                'primary_key': [],
                'foreign_keys': [],
                'indexes': []
            }
            
        for row in pk_rows:
            if row['table_name'] in tables_dict:
                tables_dict[row['table_name']]['primary_key'].append(row['column_name'])
                
        for row in fk_rows:
            if row['table_name'] in tables_dict:
                tables_dict[row['table_name']]['foreign_keys'].append(
                    ForeignKeyInfo(
                        column=row['column_name'],
                        referenced_table=row['foreign_table_name'],
                        referenced_column=row['foreign_column_name']
                    )
                )
                
        total_columns = 0
        for row in column_rows:
            if row['table_name'] in tables_dict:
                is_pk = row['column_name'] in tables_dict[row['table_name']]['primary_key']
                
                is_fk = any(
                    fk.column == row['column_name'] 
                    for fk in tables_dict[row['table_name']]['foreign_keys']
                )
                
                col_info = ColumnInfo(
                    name=row['column_name'],
                    data_type=row['data_type'],
                    is_nullable=row['is_nullable'] == 'YES',
                    is_primary_key=is_pk,
                    is_foreign_key=is_fk,
                    default_value=row['column_default']
                )
                tables_dict[row['table_name']]['columns'].append(col_info)
                total_columns += 1
                
        # Build final models
        table_models = []
        for t_dict in tables_dict.values():
            table_models.append(TableInfo(**t_dict))
            
        return SchemaInfo(
            tables=table_models,
            total_tables=len(table_models),
            total_columns=total_columns,
            extracted_at=datetime.utcnow().isoformat()
        )
