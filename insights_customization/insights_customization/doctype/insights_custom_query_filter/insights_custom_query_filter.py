# Copyright (c) 2025, NexTash (SMC-PVT) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class InsightsCustomQueryFilter(Document):
	@frappe.whitelist()
	def generate_dataset(doc):
		if not doc.get("charts") or len(doc.get("charts")) == 0:
			frappe.throw("No charts found in the child table.")

		dataset = {
			"links": {},
			"column": {},
			"label": doc.get("label", "")
		}

		dataset["column"] = {
			"type": doc.get("type", "Date"),
			"value": doc.get("value", ""),
		}

		for chart in doc.get("charts"):
			link_key = chart.get("item_id")

			dataset["links"][link_key] = {
				"value": chart.get("value", ""),
			}

		dashboard_name = doc.get("dashboard")
		if dashboard_name:
			dashboard_doc = frappe.get_doc("Insights Dashboard", dashboard_name)

			if not dashboard_doc.get("items"):
				dashboard_doc.items = []

			existing_item = next((item for item in dashboard_doc.items if item.item_id == doc.get("filter_id")), None)

			if existing_item:
				existing_item.options = frappe.as_json(dataset)
				msg = "Config updated in the linked Insights Dashboard."
			else:
				new_item = {
					"item_id": doc.get("filter_id"),
					"item_type": "Filter",
					"options": frappe.as_json(dataset),
				}
				dashboard_doc.append("items", new_item)
				msg = "Config added to the linked Insights Dashboard successfully."

			frappe.msgprint(msg)
			dashboard_doc.save()

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_insights_dashboard_item(doctype, txt, searchfield, start, page_len, filters):
	filters = filters or {}

	sql = f"""
			SELECT
				id_item.name,
				id_item.item_id,
				id_item.options
			FROM
				`tabInsights Dashboard Item` id_item
			JOIN
				`tabInsights Dashboard` id_parent ON id_item.parent = id_parent.name
			WHERE
				id_item.item_type = 'Row' AND
				id_parent.name = '{filters.get("dashboard")}';
		"""

	charts = frappe.db.sql(sql, as_dict = True)

	docs = []
	for row in charts:
		description = f"{row.get('item_id')}, {frappe.parse_json(row.get('options')).get('title')}"
		docs.append([row.get('name'), description])
	
	return docs

