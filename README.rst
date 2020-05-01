===========================
Django Manage Command Admin
===========================

DMCAdmin is a web-based app for managing the execution of Django manage commands.

Store your manage commands in a table, run async through the web and view the result.

Quick start
-----------

1. pip install django-dmcadmin

2. Add "dmcadmin" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'dmcadmin',
    ]

3. Include the dmcadmin URLconf in your project urls.py like this::

    url(r'^dmcadmin/', include('dmcadmin.urls')),

4. Run `python manage.py migrate` to create the dmcadmin models.

5. Start the development server and visit http://127.0.0.1:8000/dmcadmin/
   to run manage command.
