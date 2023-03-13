
from django.db import models
from django.utils.translation import ugettext_lazy as _


class NumberCharField(models.CharField):

    description = _("String with only numbers (up to %(max_length)s)")

    def to_python(self, value: str) -> str:
        value = super().to_python(value)
        only_number = ''.join(filter(str.isdigit, value)) if value else value
        if only_number == '':
            only_number = None
        return only_number
