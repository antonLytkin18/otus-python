from django import forms


class BootstrapForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name in self.errors:
                field.widget.attrs['class'] += ' is-invalid'
            field.help_text = ''
