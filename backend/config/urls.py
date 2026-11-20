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
        return JsonResponse({"headers": headers, "rows": list(rows)})
    finally:
        workbook.close()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/preview/", preview),
]