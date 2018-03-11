import django
from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'home/$', views.centralLocation, name="centralLocation"),#'^$' means that they shouldn't add anything to url
    #http://127.0.0.1:8000/map_app/
    url(r'otherLocations/$', views.otherLocations, name="otherLocations"),
    url(r'summary/$', views.downloadSummary, name ='summary'),
    url(r'detail/$', views.downloadDetail, name='detail'),
    url(r'orderOfDistance/$', views.downloadOrderedByDistance, name='ordered'),
    url(r'login/$', views.login_view, name='loginuser'),
    url(r'logout/$', views.logout_view, name='logoutuser'),
    url(r'register/$', views.register, name='registeruser'),
    # url(r'delete/$', views.deleteAllData, name='delete'),

]
