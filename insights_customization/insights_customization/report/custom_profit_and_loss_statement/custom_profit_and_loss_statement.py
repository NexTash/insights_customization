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

        # Calculate Gross Profit
        gross_profit = {"account_name": _("Gross Profit"), "account": None, "indent": 0, "is_group": 0}

        for period in period_list:
            key = period.key

            # Calculate total income and COGS for the current period using only leaf nodes
            total_income = sum(
                row.get(key, 0) for row in income if row.get("indent", 0) > 0 and not row.get("is_group", 0)
            )
            total_cogs = sum(
                row.get(key, 0) for row in cogs if row.get("indent", 0) > 0 and not row.get("is_group", 0)
            )

            # Assign the gross profit for this period
            gross_profit[key] = total_income - total_cogs

        # Append Gross Profit row after COGS
        data.append(gross_profit)

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