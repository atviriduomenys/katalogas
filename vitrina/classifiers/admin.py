from django.contrib import admin

from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Licence
from vitrina.classifiers.models import Frequency


admin.site.register(Category)
admin.site.register(Licence)
admin.site.register(Frequency)
