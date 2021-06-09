from django.urls import path, re_path, include
from api import views

app_name = 'api'

urlpatterns = [
    re_path(r'^users/', include('users.urls')),
    re_path(r'^cloud/', include('cloud.urls')),
    path('testapiview/', views.testapiview),
]
