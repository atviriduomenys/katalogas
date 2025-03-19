import yaml
from django.http import JsonResponse
from .forms import FileUploadForm
from .models import ApiExample
from ..datasets.models import Dataset
from django.shortcuts import get_object_or_404

def handle_yaml_file(uploaded_file):
    try:
        file_content = uploaded_file.read().decode('utf-8')
        if not file_content:
            raise ValueError

        yaml.safe_load(file_content)
        return file_content, None
    except yaml.YAMLError as e:
        return None, f"Klaidingas YAML failas: {str(e)}"
    except Exception as e:
        return None, f"Įvyko klaida apdorojant failą: {str(e)}"


def is_duplicate(file_content):
    return ApiExample.objects.filter(file_data=file_content).exists()


def file_upload_view(request, pk):
    dataset = get_object_or_404(Dataset, id=pk)

    if request.method != 'POST' or 'file' not in request.FILES:
        return JsonResponse({"error": "Nepavyko įkelti failo."}, status=400)

    form = FileUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"error": "Neteisingas failas."}, status=400)

    uploaded_file = request.FILES['file']
    file_content, error_message = handle_yaml_file(uploaded_file)

    if error_message:
        return JsonResponse({"error": error_message}, status=400)

    if is_duplicate(file_content):
        return JsonResponse({"error": "Toks YAML failas jau buvo įkeltas anksčiau."}, status=400)

    file_instance = ApiExample(file_data=file_content, dataset=dataset)
    file_instance.save()

    return JsonResponse({"message": "YAML failas įkeltas sėkmingai."})

