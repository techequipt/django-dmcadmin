from django.conf.urls import url

from . import views

app_name = 'dmcadmin'

urlpatterns = [
    # /MCAdmin/
    url('login/', views.user_login, name='login'),
    url('logout/', views.user_logout, name='logout'),
    # manage command
    url('managecommand/add/', views.manage_command_add, name='add_manage_command'),
    url('managecommand/', views.ManageCommandView.as_view(), name='manage_command'),
    url('managetask/(?P<pk>\d+)/', views.ManageTaskDetailView.as_view(), name='manage_task_detail'),
    url('managetask/', views.ManageTaskListView.as_view(), name='manage_task'),
    url('', views.index, name='index'),
]