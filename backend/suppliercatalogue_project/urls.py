from zipfile import BadZipFile

from django.contrib import admin
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.urls import path
from django.views.decorators.http import require_http_methods
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


@require_http_methods(["GET", "POST"])
def preview(request):
    if request.method == "GET":
        return JsonResponse({"csrfToken": get_token(request)})

    file = request.FILES.get("file")
    if file is None or not file.name.lower().endswith(".xlsx"):
        return JsonResponse({"error": "Choose an .xlsx file."}, status=400)

    try:
        workbook = load_workbook(file, read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, KeyError):
        return JsonResponse({"error": "Could not read this Excel file."}, status=400)

    try:
        rows = workbook.active.iter_rows(values_only=True)
        headers = next(rows, ())

        for column in ("reference", "price_eur"):
            if column not in headers:
                return JsonResponse(
                    {"error": f"Missing required column: {column}"},
                    status=400,
                )

        reference_column = headers.index("reference")
        price_column = headers.index("price_eur")
        product_rows = list(rows)
        errors = []

        for row_number, row in enumerate(product_rows, start=2):
            if row[price_column] is None:
                reference = row[reference_column]
                errors.append(
                    f"Excel row {row_number}: product {reference} is missing a price."
                )

        return JsonResponse({
            "headers": headers,
            "rows": product_rows,
            "errors": errors,
        })
    finally:
        workbook.close()


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/preview/", preview),
]