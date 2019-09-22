from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(models.PrimarySite)
admin.site.register(models.SecondarySite)
admin.site.register(models.TransportClasses)
