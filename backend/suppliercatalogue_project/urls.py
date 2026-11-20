import json
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile
from django.contrib import admin
from django.http import FileResponse, JsonResponse
from django.middleware.csrf import get_token
from django.urls import path
from django.views.decorators.http import require_http_methods, require_POST
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

def open_uploaded_workbook(request, *, for_preview):
    upload = request.FILES.get("file")

    if upload is None or not upload.name.lower().endswith(".xlsx"):
        raise ValueError("Choose an .xlsx file.")

    try:
        return load_workbook(
            upload,
            read_only=for_preview,
            data_only=for_preview,
        )
    except (BadZipFile, InvalidFileException, KeyError, OSError) as exc:
        raise ValueError("Could not read this Excel file.") from exc

def get_columns(headers):
    for name in ("reference", "price_eur"):
        if name not in headers:
            raise ValueError(f"Missing required column: {name}")
        if headers.count(name) > 1:
            raise ValueError(f"The column '{name}' appears more than once.")

    return headers.index("reference"), headers.index("price_eur")

def read_price(value, row_number):
    if value is None or str(value).strip() == "":
        raise ValueError(f"Excel row {row_number}: enter a price.")

    try:
        price = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Excel row {row_number}: enter a numeric price.") from exc

    if not price.is_finite() or price < 0:
        raise ValueError(f"Excel row {row_number}: enter a price of zero or more.")

    return price

@require_http_methods(["GET", "POST"])
def preview(request):
    if request.method == "GET":
        return JsonResponse({"csrfToken": get_token(request)})

    try:
        workbook = open_uploaded_workbook(request, for_preview=True)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        headers = next(rows, ())
        reference_column, price_column = get_columns(headers)
        product_rows = list(rows)
        errors = []

        for row_number, row in enumerate(product_rows, start=2):
            if row[price_column] is None:
                errors.append(
                    f"Excel row {row_number}: product "
                    f"{row[reference_column]} is missing a price."
                )

        return JsonResponse({
            "headers": headers,
            "rows": product_rows,
            "errors": errors,
        })
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    finally:
        workbook.close()


@require_POST
def download_corrected(request):
    try:
        prices = json.loads(request.POST.get("prices", "null"))
        if not isinstance(prices, list):
            raise ValueError("Preview the workbook before downloading it.")

        workbook = open_uploaded_workbook(request, for_preview=False)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        sheet = workbook.active
        headers = [cell.value for cell in sheet[1]]
        _, price_column = get_columns(headers)

        if len(prices) != sheet.max_row - 1:
            raise ValueError("The row count changed. Preview the file again.")

        # Each item contains the displayed price and whether the user edited it.
        for row_number, item in enumerate(prices, start=2):
            if not isinstance(item, dict):
                raise ValueError(f"Excel row {row_number}: invalid price data.")

            price = read_price(item.get("value"), row_number)

            if item.get("edited") is True:
                sheet.cell(row=row_number, column=price_column + 1).value = price

        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        original_name = Path(request.FILES["file"].name).stem
        return FileResponse(
            output,
            as_attachment=True,
            filename=f"{original_name}_corrected.xlsx",
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    finally:
        workbook.close()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/preview/", preview),
    path("api/download/", download_corrected),
]