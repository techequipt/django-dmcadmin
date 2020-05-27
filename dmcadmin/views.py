from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.views.generic import ListView, DetailView
from django.views import View

from .models import ManageCommandData, ManageTask
from . import forms


def handle_uploaded_file(f):
    file_path = '/tmp/{}'.format(f.name)
    with open(file_path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return file_path


class ManageCommandView(LoginRequiredMixin, View):
    form_class = forms.ManageCommandForm
    initial = {'key': 'value'}
    mcd = ManageCommandData()
    manage_commands_dict = mcd.get_manage_command_conf_data()
    template_name = 'dmcadmin/manage_command.html'
    login_url = '/dmcadmin/login/'
    manage_tasks = ManageTask.objects.filter(state='running').order_by('-id')
    manage_tasks_title_ext = 'in progress'

    def get(self, request, *args, **kwargs):

        # выбранная manage_command
        manage_command_to_run = eval(request.GET.get('manage_command_to_run', '{}'))
        cls_name = request.GET.get('cls_name','system')
        app_name = request.GET.get('app_name','system')
        self.mcd.cls_name = cls_name
        self.mcd.app = app_name
        self.initial = manage_command_to_run
        form = self.form_class(initial=self.initial)
        context = {
            'manage_commands': self.manage_commands_dict,
            'form': form,
            'manage_tasks': self.manage_tasks,
            'manage_tasks_title_ext': self.manage_tasks_title_ext
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        manage_command_response = {}
        if form.is_valid():
            manage_command_name = form.cleaned_data['manage_command_name']

            mc_kwargs = form.cleaned_data['manage_command_kwargs'].strip()
            manage_command_kwargs = {}

            def _add_kwargs(list_kwargs):
                for i in list_kwargs:
                    vals = i.split()
                    if len(vals) == 1 and '=' in vals[0]:
                        vals = vals[0].split('=')
                    if len(vals) == 2:
                        manage_command_kwargs[str(vals[0])] = str(vals[1])
                    elif len(vals) == 1:
                        manage_command_kwargs[str(vals[0])] = ''

            if mc_kwargs.startswith('--'):
                list_kwargs = mc_kwargs.split('--')
                _add_kwargs(list_kwargs)
            elif mc_kwargs.startswith('-'):
                list_kwargs = mc_kwargs.split('-')
                _add_kwargs(list_kwargs)
            elif mc_kwargs.startswith('{'):
                manage_command_kwargs = eval(mc_kwargs)
            else:
                manage_command_kwargs = {}

            mc_args = form.cleaned_data['manage_command_args'].strip()
            if mc_args.startswith('['):
                manage_command_args = eval(mc_args)
            elif mc_args:
                manage_command_args = mc_args.split()
            else:
                manage_command_args = []
            # manage_command_kwargs = eval(form.cleaned_data['manage_command_kwargs'] or '{}')
            is_system = True if self.mcd.app == 'system' else False
            if request.FILES:
                file_path = handle_uploaded_file(request.FILES['import_file'])
                manage_command_kwargs['import_file'] = '"{}"'.format(file_path)
            manage_command_response = self.mcd.run_manage_command(
                manage_command_name,
                manage_command_args,
                manage_command_kwargs,
                is_system=is_system
            )
            # return HttpResponseRedirect('/success/url/')

        form = self.form_class(initial=self.initial)
        context = {
            'manage_commands': self.manage_commands_dict,
            'form': form,
            'running_task': manage_command_response.get('manage_task_id'),
            'error_running_command': manage_command_response.get('error'),
            'manage_tasks': self.manage_tasks,
            'manage_tasks_title_ext': self.manage_tasks_title_ext
        }
        return render(request, self.template_name, context)


@login_required(login_url='/dmcadmin/login/')
def manage_command_add(request):
    context = {}
    return render(request, 'dmcadmin/manage_command_add.html', context)


class ManageTaskListView(LoginRequiredMixin, ListView):
    model = ManageTask
    queryset = ManageTask.objects.order_by('-id')
    context_object_name = 'manage_tasks'
    paginate_by = 10
    template_name = 'dmcadmin/manage_task.html'
    login_url = '/dmcadmin/login/'


class ManageTaskDetailView(LoginRequiredMixin, DetailView):
    model = ManageTask
    context_object_name = 'manage_task'
    template_name = 'dmcadmin/manage_task_detal.html'
    login_url = '/dmcadmin/login/'

    def get_object(self):
        obj = super().get_object()
        # check task state
        if obj.state not in ['done'] and not obj.proc_is_run():
            obj.state = 'error'
            obj.save(update_fields=['state'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = forms.ManageTaskForm(instance=self.object)
        context['manage_tasks'] = ManageTask.objects.all().order_by('-id')[:20]
        return context


@login_required(login_url='/dmcadmin/login/')
def index(request):
    context = {}
    return render(request, 'dmcadmin/index.html', context)


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request,user)
                return HttpResponseRedirect(reverse('dmcadmin:index'))
            else:
                return HttpResponse("Your account was inactive.")
        else:
            print("Someone tried to login and failed.")
            print("They used username: {} and password: {}".format(username,password))
            return HttpResponse("Invalid login details given")
    else:
        return render(request, 'dmcadmin/base/login.html', {})

def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('dmcadmin:index'))
