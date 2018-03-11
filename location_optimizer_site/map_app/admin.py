from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(models.CentralSite)
admin.site.register(models.Route)
admin.site.register(models.TransportClasses)
