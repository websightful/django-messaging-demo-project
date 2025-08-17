from django.urls import path
from . import views

app_name = 'people'

urlpatterns = [
    path('', views.person_list, name='person_list'),
    path('<int:user_id>/', views.person_detail, name='person_detail'),
]
