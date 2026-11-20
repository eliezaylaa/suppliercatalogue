from openpyxl import load_workbook

wb = load_workbook("supplier_products.xlsx")
ws = wb.active
for v in ws.iter_rows(values_only=True):
    for value in v:
        if value is None:
            value = 0
        print(value)
