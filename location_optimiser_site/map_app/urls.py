#import django
from django.conf.urls import include, url
from django.conf.urls import re_path
from . import views

app_name = 'map_app'

map_app_patterns = [
    re_path(r'home/$', views.upload_page,
            name="upload_page"),  # '^$' means that they shouldn't add anything to url
    #http://127.0.0.1:8000/map_app/
    # re_path(r'broken_addresses/$', views.download_broken_addresses,
    #         name='broken_addresses'),
    re_path(r'comparePrimary/$', views.comparePrimary,
            name="comparePrimary"),
    re_path(r'closestSiteCosts/$', views.closestSiteCosts,
            name="closestSiteCosts"),
    re_path(r'summary/$', views.downloadSummary,
            name='summary'),
    re_path(r'detail/$', views.downloadDetail,
            name='detail'),
    re_path(r'orderOfDistance/$', views.downloadOrderedByDistance,
            name='ordered'),
    # re_path(r'login/$', views.login_view,
    #         name='loginuser'),
    # re_path(r'logout/$', views.logout_view,
    #         name='logoutuser'),
    re_path(r'delete_user_data/$', views.delete_data,
            name='delete_user_data'),

]

urlpatterns = [
    re_path('/', include(map_app_patterns)),
]
