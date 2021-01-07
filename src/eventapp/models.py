from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from eventapp.utils import text_to_id


class Profile(models.Model):
    user = models.OneToOneField(
        User, related_name="profile", on_delete=models.CASCADE, unique=True
    )
    matricula = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )

    def __str__(self):
        return str(self.user.username)


class ImovelUpdateLog(models.Model):
    datetime_started = models.DateTimeField(default=timezone.now)
    datetime = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )
    total = models.IntegerField(default=0)
    inalterados = models.IntegerField(default=0)
    alterados = models.IntegerField(default=0)
    novos = models.IntegerField(default=0)
    response = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )

    class Meta:
        ordering = ["-datetime"]


class Imovel(models.Model):

    # common
    codigo_lote = models.CharField(max_length=255)  # inscrlig
    logradouro = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )  # nlogrado
    numero = models.CharField(
        max_length=255, null=True, blank=True, default="S/N"
    )  # nnumimov
    bairro = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )  # nnomebai
    cep = models.CharField(max_length=255, null=True, blank=True, default="")
    area_lote = models.DecimalField(
        max_digits=10, decimal_places=2, null=True
    )  # nareater

    # properties
    inscricao_imobiliaria = models.CharField(
        unique=True, max_length=255
    )  # ninscrao
    codigo = models.CharField(unique=True, max_length=255)  # ncodimov
    matricula = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )  # nmatricu
    razao_social = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )  # nrazaoso
    complemento = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )  # ncomplem
    numero_contribuinte = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )  # ncodcont
    fracao_ideal = models.DecimalField(
        max_digits=10, decimal_places=2, null=True
    )  # nfracaoi
    zona = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )  # zon2012predom
    zona2012 = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )  # zon2012

    # control
    updated = models.DateTimeField(default=timezone.now)
    filedatetime = models.DateTimeField(default=timezone.now)

    def __str__(self):
        string = ""
        if self.codigo:
            string += str(self.codigo)
        if self.logradouro:
            string += " - " + self.logradouro
        if self.numero:
            string += ", n" + self.numero
        if self.complemento:
            string += ", " + self.complemento
        if self.bairro:
            string += " - " + self.bairro
        return string

    @property
    def name_string(self):
        string = ""
        if self.codigo:
            string += str(self.codigo)
        if self.logradouro:
            string += " - " + self.logradouro
        if self.numero:
            string += ", n" + self.numero
        if self.complemento:
            string += ", " + self.complemento
        if self.bairro:
            string += " - " + self.bairro
        return string


# ====NOTICES====
class Notice(models.Model):
    imovel = models.ForeignKey(
        Imovel,
        related_name="notices",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    document = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )
    date = models.DateField(default=timezone.now)
    address = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )
    description = models.TextField(null=True, blank=True, default="")
    owner = models.ForeignKey(
        User, related_name="notices", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["date", "id"]

    def css_name(self):
        already_in = []
        css_class_name = ""
        for notice_event in self.notice_events.all():
            if (
                notice_event.notice_event_type.show_start
                and notice_event.notice_event_type.id not in already_in
            ):
                if css_class_name:
                    css_class_name += ", "
                css_class_name += notice_event.notice_event_type.name_to_id
            already_in.append(notice_event.notice_event_type.id)
        return css_class_name


class NoticeEventType(models.Model):
    order = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=255, unique=True)
    short_name = models.CharField(max_length=255, unique=True)
    default_deadline = models.PositiveIntegerField(null=True, blank=True)
    default_deadline_working_days = models.BooleanField(default=False)
    default_concluded = models.BooleanField(default=False)
    css_color = models.CharField(max_length=10, null=True)
    show_concluded = models.BooleanField(default=True)
    show_report_number = models.BooleanField(default=False)
    show_deadline = models.BooleanField(default=True)
    show_fine = models.BooleanField(default=False)
    show_start = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return str(self.id) + "-" + self.short_name

    @property
    def name_to_id(self):
        return text_to_id(self.name)


class NoticeColor(models.Model):
    css_color = models.CharField(max_length=10, null=True)
    notice_event_types = models.ManyToManyField(NoticeEventType)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return str(self.css_color)

    def css_name(self):
        already_in = []
        css_class_name = ""
        for notice_event_type in self.notice_event_types.all():
            if (
                notice_event_type.show_start
                and notice_event_type.id not in already_in
            ):
                if css_class_name:
                    css_class_name += ", "
                css_class_name += notice_event_type.name_to_id
            already_in.append(notice_event_type.id)
        return css_class_name


class NoticeEvent(models.Model):
    date = models.DateField(default=timezone.now)
    identification = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )
    report_number = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )
    notice = models.ForeignKey(
        Notice, related_name="notice_events", on_delete=models.CASCADE
    )
    notice_event_type = models.ForeignKey(
        NoticeEventType, related_name="notice_events", on_delete=models.CASCADE
    )
    deadline = models.PositiveIntegerField(default=0)
    deadline_working_days = models.BooleanField(default=False)
    deadline_date = models.DateField(default=timezone.now)
    concluded = models.BooleanField(default=False)

    class Meta:
        ordering = ["notice", "notice_event_type", "id"]

    def __str__(self):
        return str(self.notice_event_type) + " - " + str(self.identification)

    def css_class_name(self):
        return (
            "notice_deadline_" + self.notice_event_type.name_to_id + "_color"
        )


class NoticeFine(models.Model):
    identification = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )
    date = models.DateField(default=timezone.now)
    notice_event = models.ForeignKey(
        NoticeEvent, related_name="notice_fines", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["notice_event", "date", "id"]

    def __str__(self):
        return str(self.date) + " - " + str(self.identification)


# ====SURVEYS====
class SurveyEventType(models.Model):
    order = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=255, unique=True)
    short_name = models.CharField(max_length=255, unique=True)
    css_color = models.CharField(max_length=10, null=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return str(self.id) + "-" + self.name

    @property
    def name_to_id(self):
        return text_to_id(self.short_name)


class SurveyEvent(models.Model):
    imovel = models.ForeignKey(
        Imovel,
        related_name="survey_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    document = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )
    identification = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )
    date = models.DateField(default=timezone.now)
    survey_event_type = models.ForeignKey(
        SurveyEventType, related_name="survey_events", on_delete=models.CASCADE
    )
    address = models.CharField(
        max_length=255, null=True, blank=True, default=""
    )
    description = models.TextField(null=True, blank=True, default="")
    concluded = models.BooleanField(default=False)
    owner = models.ForeignKey(
        User, related_name="surveys", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["date", "survey_event_type", "id"]

    def __str__(self):
        return str(self.date)

    def css_class_name(self):
        return "survey_" + self.survey_event_type.name_to_id + "_color"


# ====Atividades====
class Activity(models.Model):
    date = models.DateField(default=timezone.now)
    description = models.TextField(null=True, blank=True, default="")
    owner = models.ForeignKey(
        User, related_name="activitys", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["date", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "owner"], name="unique_per_day"
            )
        ]

    def __str__(self):
        return str(self.date)
