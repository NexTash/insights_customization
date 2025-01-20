import frappe
from insights.insights.doctype.insights_query.utils import InsightsDataSource, get_columns_with_inferred_types, update_sql
from insights.insights.doctype.insights_query.insights_raw_query import InsightsRawQueryController

def InsightsRawQueryControllerOverride(InsightsRawQueryController):
    def fetch_results(self, additional_filters=None):
        query = self.doc
        frappe.throw("lora")
        
        if additional_filters:
            query = self.apply_additional_filters(additional_filters)
        return InsightsDataSource.get_doc(self.doc.data_source).run_query(query)
    
    def apply_additional_filters(self, additional_filters):
        import re

        query =  self.doc.sql

        where_pattern = re.compile(r'\bWHERE\b', re.IGNORECASE)
        group_by_pattern = re.compile(r'\bGROUP BY\b', re.IGNORECASE)
        limit_pattern = re.compile(r'\bLIMIT\b', re.IGNORECASE)

        # Split query into parts based on important clauses
        parts = re.split(group_by_pattern, query, maxsplit=1)
        query_body = parts[0]  # Query body before GROUP BY
        group_by_clause = parts[1] if len(parts) > 1 else ""

        # Further split to handle LIMIT if it exists in the GROUP BY or main query
        limit_parts = re.split(limit_pattern, group_by_clause, maxsplit=1)
        group_by_clause = limit_parts[0] if len(limit_parts) > 0 else ""
        limit_clause = limit_parts[1] if len(limit_parts) > 1 else ""

        # Check if a WHERE clause exists
        if where_pattern.search(query_body):
            query_body += " AND "
        else:
            query_body += " WHERE "

        # Add additional filters
        additional_conditions = []
        for filter in additional_filters:
            column = filter.get("column")
            operator = filter.get("operator")
            value = filter.get("value")
            column = column.get("value")

            column = column.split(".")
            column = f"`{column[0]}`.{column[1]}"

            # Quote string values
            if column and operator and value:
                if isinstance(value, str):
                    value = f"'{value}'"

                if operator == "between":
                    value = value.split(',')
                    value = f"{value[0]}' AND '{value[1]}"
                
                additional_conditions.append(f"{column} {operator} {value}")

        # Append conditions to the query body
        query_body += " AND ".join(additional_conditions)

        # Reassemble the query
        final_query = query_body
        if group_by_clause:
            final_query += f" GROUP BY {group_by_clause.strip()}"
        if limit_clause:
            final_query += f" LIMIT {limit_clause.strip()}"

        # frappe.throw(f"{final_query}")
        self.doc.sql = final_query
        return self.doc
    
    