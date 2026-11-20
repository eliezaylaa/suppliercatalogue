from openpyxl import load_workbook

wb = load_workbook("supplier_products.xlsx")
ws = wb.active
for v in ws.iter_rows(min_row=2):
    for cell in v:
        if cell.value is None:
            cell.value = 0
            print("Filled", cell.coordinate)

wb.save("supplier_products_filled.xlsx")