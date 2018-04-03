#import django
#from django.conf.urls import include, url
from django.urls import re_path, include
from . import views

app_name = 'map_app'

map_app_patterns = [
    re_path(r'home/$', views.centralLocation, name="centralLocation"),#'^$' means that they shouldn't add anything to url
    #http://127.0.0.1:8000/map_app/
    re_path(r'otherLocations/$', views.otherLocations, name="otherLocations"),
    re_path(r'summary/$', views.downloadSummary, name ='summary'),
    re_path(r'detail/$', views.downloadDetail, name='detail'),
    re_path(r'orderOfDistance/$', views.downloadOrderedByDistance, name='ordered'),
    re_path(r'login/$', views.login_view, name='loginuser'),
    re_path(r'logout/$', views.logout_view, name='logoutuser'),
    re_path(r'register/$', views.register, name='registeruser'),
    # url(r'delete/$', views.deleteAllData, name='delete'),

]

urlpatterns = [
    re_path('/', include(map_app_patterns)),
]
