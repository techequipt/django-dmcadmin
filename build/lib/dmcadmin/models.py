import os
import json
import subprocess
import signal
import psutil
import asyncio

from django.db import models
from django.utils.timezone import now
from django.db import transaction
from django.conf import settings

from .utils import get_path, get_manage_command_log_file, get_instance_file_name


class ManageTask(models.Model):
    class Meta:
        verbose_name = 'Manage task'
        verbose_name_plural = 'Manage tasks'

    STATES = [
        ('waiting', 'Waiting'),
        ('starting', 'Starting'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('error', 'Error'),
    ]

    pid = models.CharField('PID', max_length=36, blank=True, null=True)
    app = models.CharField('Application', max_length=255, blank=True, null=True)
    cls = models.CharField('Models class', max_length=255, blank=True, null=True)
    manage_command = models.CharField('Manage command name', max_length=255, blank=True, null=True)
    args = models.CharField(max_length=255, blank=True, null=True)
    kwargs = models.CharField(max_length=255, blank=True, null=True)
    log_file = models.CharField(max_length=255, blank=True, null=True)
    console_log_file = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField('Файл', upload_to=get_instance_file_name, blank=True, null=True)
    datetime_create = models.DateTimeField(default=now)
    state = models.CharField(max_length=35, choices=STATES, default=STATES[0][0])

    def __str__(self):
        return '{}'.format(self.id)

    def stop_process(self):
        # to be sure we kill all the children:
        os.killpg(int(self.pid), signal.SIGTERM)

    def proc_is_run(self):
        # получим объект процесса
        try:
            proc = psutil.Process(int(self.pid))
        except Exception:
            return False
        if not proc.is_running():
            return False
        return True


class ManageCommandData:
    """
    Class for storing django manage commands in file and async run the selected manage command.

    ...

    Attributes
    ----------
    app: str
        The django application name that uses manage command. Default - system (for base django manage command)
    cls_name: str
        The models class name that uses manage command. Default - system (for base django manage command)
        You can use models.ManageTask._meta.model_name for get cls_name in your application

    Methods
    -------
    add_manage_command_to_conf(
        app_name, cls_name, manage_command_name, description, template_media_path=None, args=[], kwargs={}
    )
        Add new manage command to store

        How to add new manage command:
        ```
        from dmcadmin.models import ManageCommandData
        mcd = ManageCommandData()
        mcd.add_manage_command_to_conf(
            'app_name', 'cls_name', 'manage_command_name', 'description', template_media_path=None, args=[], kwargs={}
        )
        ```
        * template_media_path - it is a path to import file template, if you created import manage command for
        import data. Save it in /static/
        Recomendation: import template file save to there: project_root/static/managecommand/import_templates/your_template_file.xlsx

        * args: add optional arguments as list ['key', 'key']
        * kwargs: add optional named arguments as dict {'key':'value', 'key':'value'}

        Example:
        ```
        mcd.add_manage_command_to_conf(
            'blog', 'post', 'blog_post_import', 'import new posts for blog',
            template_media_path='/static/managecommand/import_templates/new_blogs_post.xlsx',
            args=[], kwargs={}
        )
        ```

        * You can edit manage command stores file in editor, if you want.
        * After adding a new command, you need to restart the backend to see the new command on the web.

    get_manage_command_conf_data()
        Get manage commands from store. Return json data

    run_manage_command(manage_command_name, manage_command_args=[], manage_command_kwargs={}, is_system=True)
        Async run manage command, save running result to ManageTask
        Example:
        * command running in console: python manage.py dumpdata blog --indent 4
        * with use this method: ManageCommandData.call_manage_command('dumpdata',['blog'], {'indent':4})
    """

    def __init__(self, app='system', cls_name='system'):
        self.manage_command_conf_file = os.path.join(
            get_path(os.path.join(settings.BASE_DIR, 'static', 'managecommand', 'conf')),
            'manage_command.conf'
        )
        self.app = app
        self.cls_name = cls_name
        self.log_file_dir = None
        self.log_file_url = None
        self.process = None

    def get_manage_command_conf_data(self, app_name=None, cls_name=None):
        """
        :return manage commands from project_root/static/managecommand/conf/manage_command.conf
        """
        if os.path.isfile(self.manage_command_conf_file):
            with open(self.manage_command_conf_file) as json_file:
                data = json.load(json_file)
        else:
            with open(self.manage_command_conf_file, 'w') as json_file:
                # adding example command for first view
                data = {
                    "system": {
                        "system": [
                            {
                                "manage_command_name": "migrate",
                                "template_media_path": None,
                                "description": "execute migrations",
                                "manage_command_args": "[]",
                                "manage_command_kwargs": "{}"
                            },
                            {
                                "manage_command_name": "dumpdata",
                                "manage_command_args": [
                                    "dmcadmin"
                                ],
                                "manage_command_kwargs": {
                                    "indent": 4
                                },
                                "template_media_path": None,
                                "description": "dump dmcadmin"
                            }
                        ]
                    }
                }
                json.dump(data, json_file, indent=4)

        is_new_key = False
        app_data = None
        if app_name:
            app_data = data.get(app_name)
            if app_data is None:
                # add empty app name
                app_data = data[app_name] = {}
                is_new_key = True
        if app_name and cls_name:
            app_data = data[app_name].get(cls_name)
            if app_data is None:
                # add empty class name
                app_data = data[app_name][cls_name] = []
                is_new_key = True

        if is_new_key:
            # save data, if new key exists
            with open(self.manage_command_conf_file, 'w') as json_file:
                json.dump(data, json_file, indent=4)

        if app_data is not None:
            return app_data

        return data

    def add_manage_command_to_conf(self, app_name, cls_name, manage_command_name, description, template_media_path=None, args=[], kwargs={}):
        """
        Add new manage commands json string to stores file project_root/static/managecommand/conf/manage_command.conf
        Data format in stores file: json

        Parameters
        ----------
        manage_command_name: str
        template_media_path: str
            template_media_path - it is a path to import file template,
            if you created import manage command for import data. Save it in /static/
            Recomendation: import template file save to there:
                project_root/static/managecommand/import_templates/your_template_file.xlsx
        description: str
        args: list
            ['key', 'key']
        kwargs: dict
            {key:value, key:value}

        Returns
        -------
            manage_command_conf_file path

        Example:
        ```
        mcd.add_manage_command_to_conf(
            'blog', 'post', 'blog_post_import', 'import new posts for blog',
            template_media_path='/static/managecommand/import_templates/new_blogs_post.xlsx',
            args=[], kwargs={}
        )

        mcd.add_manage_command_to_conf(
            'system', 'system', 'dumpdata', 'dump dmcadmin', args=['dmcadmin'], kwargs={'indent':4}
        )
        ```
        * You can edit manage command stores file in editor, if you want.

        * After adding a new command, you need to restart the backend to see the new command on the web.
        """

        # before get_manage_command_conf_data check (create) keys app_name and cls_name in stores file
        self.get_manage_command_conf_data(app_name, cls_name)

        data = self.get_manage_command_conf_data()

        new_conf = {
            'manage_command_name': manage_command_name,
            'manage_command_args': args,
            'manage_command_kwargs': kwargs,
            'template_media_path': template_media_path,
            'description': description
        }

        data[app_name][cls_name].append(new_conf)

        with open(self.manage_command_conf_file, 'w') as json_file:
            json.dump(data, json_file,indent=4)

        return self.manage_command_conf_file

    def run_manage_command(self, manage_command_name, manage_command_args=[], manage_command_kwargs={}, is_system=True):
        """
        Async run manage.py command, which create result ManageTask
        :param manage_command_name:
        :param manage_command_args:
        :param manage_command_kwargs:
        :param is_system: set is_system=False, if you create ouwn maange command. then to your manage command send
        additional kwargs['log_file'] = log_file_dir и kwargs['manage_task_id'] = manage_task.id
        :return: pid running system process

        Example:
        * command running in console: python manage.py dumpdata blog --indent 4
        * with use this method: ManageCommandData.call_manage_command('dumpdata',['dmcadmin'], {'indent':4})

        """
        args = manage_command_args or []
        kwargs = manage_command_kwargs or {}
        log_file_dir, log_file_url, console_log_dir, console_log_url = get_manage_command_log_file(
            self.app, manage_command_name
        )
        self.log_file_dir = log_file_dir
        self.log_file_url = log_file_url
        manage_task = ManageTask.objects.create()
        import_file = kwargs.get('import_file')
        if import_file:
            # if import_file exists in kwargs
            is_system = False
        args.extend(['>', console_log_dir])
        if not is_system:
            # for your manage commands pass path to log_file and manage_task_id to save result
            kwargs['log_file'] = log_file_dir
            kwargs['manage_task_id'] = manage_task.id

        args_str = ' '.join([str(a) for a in args])
        kwargs_str = ' '.join(['--{} {}'.format(key, value) for key, value in kwargs.items()])
        call_cmd = ' '.join(['python', 'manage.py', manage_command_name, args_str, kwargs_str])

        with open(console_log_dir, 'w') as console_out_file:
            console_out_file.writelines(call_cmd)

        def run_cmd():
            process = subprocess.Popen(call_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            with open(console_log_dir, 'a') as console_out_file:
                console_out_file.write(f'Running command:\n{call_cmd}\n')

            manage_task.pid = process.pid
            manage_task.state = 'running'
            manage_task.save(update_fields=['pid','state'])

            stdout, stderr = process.communicate()
            print(f'[{call_cmd!r} exited with {process.returncode}]')
            if stdout:
                s_stdout = f'[stdout]\n{stdout.decode()}\n'
            else:
                s_stdout = f'[stdout]\nNone\n'
            # print(s_stdout)
            if stderr:
                s_stderr = f'[stderr]\n{stderr.decode()}\n'
            else:
                s_stderr = f'[stderr]\nNone\n'
            # print(s_stderr)

            # print(f'save stdout stderr in file {console_log_dir}')
            with open(console_log_dir, 'a') as console_out_file:
                console_out_file.write(f'Complete. Command run:\n{call_cmd}\n')
                console_out_file.write(s_stdout)
                console_out_file.write(s_stderr)

            # Save result in ManageTask
            new_manage_task = {
                'pid':process.pid,
                'app':self.app,
                'cls':self.cls_name,
                'manage_command':manage_command_name,
                'args':args,
                'kwargs':kwargs,
                'log_file':self.log_file_url,
                'console_log_file': console_log_url,
                'state': 'done'
            }
            for attr, value in new_manage_task.items():
                setattr(manage_task, attr, value)
            with transaction.atomic():
                manage_task.save()
            # print(f'Result saved in ManageTask: {manage_task.id}')

            # async check
            # time.sleep(10)
            print(f'run_cmd complete. call_cmd: {call_cmd}')

        # async run
        loop = asyncio.new_event_loop()
        loop.run_in_executor(None, run_cmd)

        return {'manage_task_id': manage_task.id, 'error': ''}
