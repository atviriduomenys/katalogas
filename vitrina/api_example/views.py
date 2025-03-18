import yaml
from django.http import JsonResponse
from .forms import FileUploadForm
from .models import ApiExample


def file_upload_view(request):
    if request.method == 'POST' and request.FILES.get('file'):
        model = request.POST.get('model')
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            try:
                file_content = uploaded_file.read().decode('utf-8')
                yaml.safe_load(file_content)
                existing_file = ApiExample.objects.filter(file_data=file_content).first()
                if existing_file:
                    return JsonResponse({"error": "Toks YAML failas jau buvo įkeltas anksčiau."}, status=400)
                file_instance = ApiExample(file_data=file_content, path=model)
                file_instance.save()

                return JsonResponse({"message": "YAML failas įkeltas sėkmingai."})

            except yaml.YAMLError as e:
                return JsonResponse({"error": f"Klaidingas YAML failas: {str(e)}"}, status=400)
        else:
            return JsonResponse({"error": "Neteisingas failas."}, status=400)

    return JsonResponse({"error": "Nepavyko įkelti failo."}, status=400)
