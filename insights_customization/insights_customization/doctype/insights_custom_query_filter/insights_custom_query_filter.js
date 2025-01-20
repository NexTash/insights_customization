// Copyright (c) 2025, NexTash (SMC-PVT) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Custom Query Filter", {
    onload: function (frm) {
        frm.set_query("id", "charts", function () {
            return {
                query: "insights_customization.insights_customization.doctype.insights_custom_query_filter.insights_custom_query_filter.get_insights_dashboard_item",
                filters: { dashboard: frm.doc.dashboard },
            };
        });
    },

    refresh(frm) {
        if (frm.is_new()) {
        frm.set_value("filter_id", Math.floor(100000 + Math.random() * 900000).toString());
        }

        if (!frm.is_new()) {
        frm.add_custom_button(__("Add/Update Config"), function () {
            frm.call("generate_dataset");
        });
        }
    },
});



