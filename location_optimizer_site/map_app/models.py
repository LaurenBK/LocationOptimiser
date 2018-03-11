from django.db import models
from django.utils import timezone

# Create your models here.

class CentralSite(models.Model):
    address = models.CharField(max_length=200, primary_key=True)
    pub_date = models.DateTimeField('date published', default=timezone.now())   #date-time field
    lat =  models.FloatField(default=0)
    lng = models.FloatField(default=0)
    costPerMonth = models.FloatField(default=0)

    def __str__(self):
        return self.address

class Route(models.Model):
    site = models.ForeignKey(CentralSite, on_delete=models.CASCADE)  # link between question and the choices
    address = models.CharField(max_length=200)
    distance_km = models.FloatField('distance',default=0)
    duration_minutes = models.FloatField('time',default=0)
    type = models.CharField(max_length = 50, default = 'Unknown')
    deliveriesPerMonth = models.FloatField(default=0)
    routeCost = models.FloatField('time',default=0)
    routeCostPerMonth = models.FloatField('time', default=0)

    lat = models.FloatField(default=0)
    lng = models.FloatField(default=0)

    def __str__(self):
        return self.address

class TransportClasses(models.Model):
    transport = models.CharField(max_length=200, primary_key=True)
    costPerKm = models.FloatField('distance', default=0)

    def __str__(self):
        return self.transport