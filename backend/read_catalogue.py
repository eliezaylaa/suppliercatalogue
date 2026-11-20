from openpyxl import load_workbook

wb = load_workbook("supplier_products.xlsx")
ws = wb.active
for v in ws.iter_rows(values_only=True):
    print(v)
