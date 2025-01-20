# Copyright (c) 2025, NexTash (SMC-PVT) Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class InsightsCustomQueryFilter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from insights.insights.doctype.insights_dashboard_filter_links.insights_dashboard_filter_links import InsightsDashboardFilterLinks

		charts: DF.Table[InsightsDashboardFilterLinks]
		column: DF.Data | None
		dashboard: DF.Link | None
		data_source: DF.Link | None
		description: DF.Data | None
		filter_id: DF.Data | None
		label: DF.Data | None
		name1: DF.Data | None
		reference_doctype: DF.Data | None
		reference_doctype_fieldname: DF.Data | None
		table: DF.Data | None
		type: DF.Data | None
		value: DF.Data | None
	# end: auto-generated types
	pass
