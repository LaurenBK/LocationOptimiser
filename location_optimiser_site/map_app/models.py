from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

# Create your models here.


class PrimarySite(models.Model):
    address = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published', default=timezone.now)   #date-time field
    lat = models.FloatField(default=0)
    lng = models.FloatField(default=0)
    user = models.CharField(max_length=50)
    costPerMonth = models.FloatField(default=0)

    def __str__(self):
        return self.address


class SecondarySite(models.Model):
    site = models.ForeignKey(PrimarySite,
                             on_delete=models.CASCADE)  # link between question and the choices
    address = models.CharField(max_length=200)
    user = models.CharField(max_length=50)
    distance_km = models.FloatField('distance', default=0)
    duration_minutes = models.FloatField('minutes', default=0)
    type = models.CharField(max_length=50, default='Unknown')
    deliveriesPerMonth = models.FloatField(default=0)
    SiteCost = models.FloatField('time', default=0)
    SiteCostPerMonth = models.FloatField('time', default=0)

    lat = models.FloatField(default=0)
    lng = models.FloatField(default=0)

    def __str__(self):
        return self.address


class TransportClasses(models.Model):
    transport = models.CharField(max_length=200)
    costPerKm = models.FloatField('distance', default=0)
    user = models.CharField(max_length=50)

    def __str__(self):
        return self.transport


# class BrokenAddresses(models.Model):
#     address = models.CharField(max_length=200)
#     user = models.CharField(max_length=50)
#
#     def __str__(self):
#         return self.address
#
