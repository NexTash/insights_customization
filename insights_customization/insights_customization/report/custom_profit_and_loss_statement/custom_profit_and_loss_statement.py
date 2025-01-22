# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)


def execute(filters=None):
    period_list = get_period_list(
        filters.from_fiscal_year,
        filters.to_fiscal_year,
        filters.period_start_date,
        filters.period_end_date,
        filters.filter_based_on,
        filters.periodicity,
        company=filters.company,
    )

    # Fetch income and expense data
    income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

    # Ensure expense is assigned before use
    expense = get_data(
        filters.company,
        "Expense",
        "Debit",
        period_list,
        filters=filters,
        accumulated_values=filters.accumulated_values,
        ignore_closing_entries=True,
        ignore_accumulated_values_for_fy=True,
    )

    # Separate Cost of Goods Sold (COGS) from other expenses
    cogs_accounts = frappe.get_all("Account", filters={"account_type": "Cost of Goods Sold"}, pluck="name")
    cogs = [row for row in expense if "account" in row and row["account"] in cogs_accounts]
    other_expenses = [row for row in expense if "account" in row and row["account"] not in cogs_accounts]
    

    # Prepare the data for the report
    data = []
    if income:
        data.append({"account_name": _("Income"), "account": None, "indent": 0, "is_group": 1})
        data.extend(income)
    if cogs:
        data.append({"account_name": _("Cost of Goods Sold"), "account": None, "indent": 0, "is_group": 1})
        data.extend(cogs)

        gross_profit = calculate_gross_profit(income, cogs, period_list)

        if gross_profit:
            # First append the general gross profit entry
            # data.append({
            #     "account_name": _("Gross Profit"),
            #     "account": None,
            #     "indent": 0,
            #     "is_group": 0
            # })

            # Now, append the actual gross profit values for each period
            for period_data in gross_profit:
                data.append(period_data)

    if other_expenses:
        data.append({"account_name": _("Other Expenses"), "account": None, "indent": 0, "is_group": 1})
        data.extend(other_expenses)

    # Calculate net profit or loss
    net_profit_loss = get_net_profit_loss(
        income, expense, period_list, filters.company, filters.presentation_currency
    )
    if net_profit_loss:
        data.append(net_profit_loss)

    # Generate columns and chart data
    columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)
    chart = get_chart_data(filters, columns, income, expense, net_profit_loss)

    currency = filters.presentation_currency or frappe.get_cached_value(
        "Company", filters.company, "default_currency"
    )
    report_summary, primitive_summary = get_report_summary(
        period_list, filters.periodicity, income, expense, net_profit_loss, currency, filters
    )

    return columns, data, None, chart, report_summary, primitive_summary


def get_report_summary(
    period_list, periodicity, income, expense, net_profit_loss, currency, filters, consolidated=False, cogs=None
):
    net_income, net_expense, net_profit, net_cogs = 0.0, 0.0, 0.0, 0.0

    # from consolidated financial statement
    if filters.get("accumulated_in_group_company"):
        period_list = get_filtered_list_for_consolidated_report(filters, period_list)

    if filters.accumulated_values:
        # when 'accumulated_values' is enabled, periods have running balance.
        # so, last period will have the net amount.
        key = period_list[-1].key
        if income:
            net_income = income[-2].get(key)
        if expense:
            net_expense = expense[-2].get(key)
        if cogs:
            net_cogs = cogs[-2].get(key)
        if net_profit_loss:
            net_profit = net_profit_loss.get(key)
    else:
        for period in period_list:
            key = period if consolidated else period.key
            if income:
                net_income += income[-2].get(key)
            if expense:
                net_expense += expense[-2].get(key)
            if cogs:
                net_cogs += cogs[-2].get(key)
            if net_profit_loss:
                net_profit += net_profit_loss.get(key)

    if len(period_list) == 1 and periodicity == "Yearly":
        profit_label = _("Profit This Year")
        income_label = _("Total Income This Year")
        expense_label = _("Total Expense This Year")
        cogs_label = _("Cost of Goods Sold This Year")
    else:
        profit_label = _("Net Profit")
        income_label = _("Total Income")
        expense_label = _("Total Expense")
        cogs_label = _("Cost of Goods Sold")

    return [
        {"value": net_income, "label": income_label, "datatype": "Currency", "currency": currency},
        {"value": net_cogs, "label": cogs_label, "datatype": "Currency", "currency": currency},
        {"type": "separator", "value": "-"},
        {"value": net_expense, "label": expense_label, "datatype": "Currency", "currency": currency},
        {"type": "separator", "value": "=", "color": "blue"},
        {
            "value": net_profit,
            "indicator": "Green" if net_profit > 0 else "Red",
            "label": profit_label,
            "datatype": "Currency",
            "currency": currency,
        },
    ], net_profit


def get_net_profit_loss(income, expense, period_list, company, currency=None, consolidated=False):
    total = 0
    net_profit_loss = {
        "account_name": "'" + _("Profit for the year") + "'",
        "account": "'" + _("Profit for the year") + "'",
        "warn_if_negative": True,
        "currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
    }

    has_value = False

    for period in period_list:
        key = period if consolidated else period.key
        total_income = flt(income[-2][key], 3) if income else 0
        total_expense = flt(expense[-2][key], 3) if expense else 0

        net_profit_loss[key] = total_income - total_expense

        if net_profit_loss[key]:
            has_value = True

        total += flt(net_profit_loss[key])
        net_profit_loss["total"] = total

    if has_value:
        return net_profit_loss


def get_chart_data(filters, columns, income, expense, net_profit_loss):
	labels = [d.get("label") for d in columns[2:]]

	income_data, expense_data, net_profit = [], [], []

	cogs_data = []

	for p in columns[2:]:
		# if cogs:
		# 	cogs_data.append(cogs[-2].get(p.get("fieldname")))
		if income:
			income_data.append(income[-2].get(p.get("fieldname")))
		if expense:
			expense_data.append(expense[-2].get(p.get("fieldname")))
		if net_profit_loss:
			net_profit.append(net_profit_loss.get(p.get("fieldname")))
    
	datasets = []
	if income_data:
		datasets.append({"name": _("Income"), "values": income_data})
	if cogs_data:
		datasets.append({"name": _("Cost of Goods Sold"), "values": cogs_data})
	if expense_data:
		datasets.append({"name": _("Expense"), "values": expense_data})
	if net_profit:
		datasets.append({"name": _("Net Profit/Loss"), "values": net_profit})



	# for p in columns[2:]:
	# 	if income:
	# 		income_data.append(income[-2].get(p.get("fieldname")))
	# 	if expense:
	# 		expense_data.append(expense[-2].get(p.get("fieldname")))
	# 	if net_profit_loss:
	# 		net_profit.append(net_profit_loss.get(p.get("fieldname")))

	# datasets = []
	# if income_data:
	# 	datasets.append({"name": _("Income"), "values": income_data})
	# if expense_data:
	# 	datasets.append({"name": _("Expense"), "values": expense_data})
	# if net_profit:
	# 	datasets.append({"name": _("Net Profit/Loss"), "values": net_profit})
	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"

	return chart

def calculate_gross_profit(income, cogs, period_list):
    gross_profit = []

    # Iterate through each period
    for period in period_list:
        key = period.key  # Get the period key (e.g., jan_2025)

        # Get income for the period, excluding groups or totals
        period_income = [
            row for row in income
            if key in row and flt(row.get(key)) > 0 and not row.get("is_group") and not row.get("account_name", "").startswith("'Total")
        ]
        
        # Get Cost of Goods Sold (COGS) for the period, excluding groups
        period_cogs = [
            row for row in cogs
            if key in row and flt(row.get(key)) > 0 and not row.get("is_group")
        ]

        # Sum up income and COGS for the current period
        total_income = sum(flt(row.get(key), 3) for row in period_income)
        total_cogs = sum(flt(row.get(key), 3) for row in period_cogs)

        # Calculate the gross profit for the current period
        gross_profit_value = total_income - total_cogs

        # Only add a "Gross Profit" entry if there is a valid gross profit value
        if gross_profit_value != 0:
            gross_profit.append({
                "account_name": _("Gross Profit"),
                "account": None,
                key: gross_profit_value,
                "currency": frappe.defaults.get_global_default("currency"),
            })

    # Return the list with gross profit calculated for each period
    return gross_profit