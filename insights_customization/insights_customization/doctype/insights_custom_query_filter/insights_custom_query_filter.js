// Copyright (c) 2025, NexTash (SMC-PVT) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Custom Query Filter", {
	refresh(frm) {
        frm.add_custom_button(__('Generate Dataset'), function () {
            // Ensure child table data is available
            if (!frm.doc.charts || frm.doc.charts.length === 0) {
                frappe.msgprint(__('No charts found in the child table.'));
                return;
            }

            // Initialize the dataset
            const dataset = {
                links: {},
                column: {},
                label: frm.doc.label || "",
            };

            // Process child table data
            frm.doc.charts.forEach((chart) => {
                const linkKey = chart.id || frappe.utils.get_random_int(100000, 999999).toString();

                dataset.links[linkKey] = {
                    label: chart.label || "",
                    column: chart.column || "",
                    table: chart.table || "",
                    type: chart.type || "",
                    table_label: chart.table_label || "",
                    data_source: chart.data_source || "",
                    description: chart.description || "",
                    value: chart.value || "",
                };
            });

            // Add data from the document fields
            dataset.column = {
                label: frm.doc.name1 || "",
                column: frm.doc.column || "",
                type: frm.doc.type || "Date",
                table: frm.doc.table || "",
                data_source: frm.doc.data_source || "",
                description: frm.doc.description || "",
                value: frm.doc.value || "",
            };

            // Add the dataset to the linked Insights Dashboard
            if (frm.doc.dashboard) {
                frappe.db.get_doc("Insights Dashboard", frm.doc.dashboard)
                    .then((dashboardDoc) => {
                        if (!dashboardDoc.items) {
                            dashboardDoc.items = [];
                        }

                        // Create a new child table item
                        const newItem = {
                            item_id:  Math.floor(100000 + Math.random() * 900000).toString(),
                            item_type: "Filter",
                            options: JSON.stringify(dataset),
                        };

                        dashboardDoc.items.push(newItem);

                        // Save the updated dashboard document
                        frappe.call({
                            method: "frappe.client.save",
                            args: {
                                doc: dashboardDoc,
                            },
                            callback: function (response) {
                                if (!response.exc) {
                                    frappe.msgprint(__('Dataset added to the linked Insights Dashboard successfully.'));
                                } else {
                                    frappe.msgprint(__('Failed to add the dataset to the linked Insights Dashboard.'));
                                }
                            },
                        });
                    })
                    .catch((error) => {
                        console.error("Error fetching the Insights Dashboard:", error);
                        frappe.msgprint(__('Could not fetch the linked Insights Dashboard.'));
                    });
            }
        });
    },
});
