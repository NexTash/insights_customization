# Copyright (c) 2025, NexTash (SMC-PVT) Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class InsightsDashboardFilterLinks(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		column: DF.Data | None
		data_source: DF.Link | None
		description: DF.Data | None
		id: DF.Data | None
		label: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		table: DF.Data | None
		table_label: DF.Data | None
		type: DF.Data | None
		value: DF.Data | None
	# end: auto-generated types
	pass
