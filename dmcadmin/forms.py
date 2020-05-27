from django import forms
from dmcadmin.models import ManageTask


class ImportForm(forms.Form):
    file = forms.FileField()


class ManageCommandForm(forms.Form):
    manage_command_name = forms.CharField(
        label='Manage command name',
        required=True,
        widget= forms.TextInput(attrs={'class':'form-control'})
    )
    manage_command_args = forms.CharField(
        label='args list',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    manage_command_kwargs = forms.CharField(
        label='kwargs dict',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    import_file = forms.FileField(
        label='Import file (if required)',
        required=False,
        # widget=forms.ClearableFileInput(attrs={'class': 'custom-file-input'})
    )


class ManageTaskForm(forms.ModelForm):
    class Meta:
        model = ManageTask
        fields = [
            'id', 'state', 'pid', 'app', 'cls', 'manage_command', 'args', 'kwargs', 'log_file', 'console_log_file',
            'datetime_create'
        ]

    def __init__(self, *args, **kwargs):
        super(ManageTaskForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
