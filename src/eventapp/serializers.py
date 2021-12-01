from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from eventapp.models import (Activity, Imovel, ImovelUpdateLog, Notice,
                             NoticeAppeal, NoticeColor, NoticeEvent,
                             NoticeEventType, NoticeEventTypeFile, NoticeFine,
                             Profile, ReportEvent, ReportEventType,
                             SurveyEvent, SurveyEventType, getDefaultImovel)
from eventapp.utils import add_days, count_days


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            "user_type",
            "matricula",
            "assistentes",
            "is_auditor",
            "is_assistente",
            "is_particular",
            "my_auditores",
        )
        read_only_fields = (
            "is_auditor",
            "is_assistente",
            "is_particular",
            "my_auditores",
        )


class UserProfileSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)
    last_login = serializers.DateTimeField(
        read_only=True, format="%Y-%m-%dT%H:%M"
    )
    date_joined = serializers.DateTimeField(
        read_only=True, format="%Y-%m-%dT%H:%M"
    )

    class Meta:
        model = User
        exclude = ("password",)
        read_only_fields = (
            "last_login",
            "date_joined",
            "is_superuser",
            "groups",
            "user_permissions",
        )

    @transaction.atomic
    def create(self, validated_data):
        profile_data = None
        if "profile" in validated_data.keys():
            profile_data = validated_data.pop("profile")
        user = User.objects.create(**validated_data)
        if profile_data:
            assistentes = profile_data.pop('assistentes')
            profile = Profile.objects.create(user=user, **profile_data)
            profile.assistentes.set(assistentes)
        else:
            Profile.objects.create(user=user)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        profile_data = None
        if "profile" in validated_data.keys():
            profile_data = validated_data.pop("profile")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        profile = Profile.objects.filter(user=instance).first()
        if not profile:
            profile = Profile.objects.create(user=instance)
        if profile_data:
            assistentes = profile_data.pop('assistentes')
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
            profile.assistentes.set(assistentes)
        return instance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
        )
        read_only_fields = (
            "id",
            "first_name",
            "last_name",
        )


class ChangePasswordSerializer(serializers.Serializer):
    model = User
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class ImovelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Imovel
        fields = (
            "id",
            "codigo_lote",
            "logradouro",
            "numero",
            "bairro",
            "cep",
            "area_lote",
            "inscricao_imobiliaria",
            "codigo",
            "matricula",
            "razao_social",
            "complemento",
            "numero_contribuinte",
            "name_string",
        )
        read_only_fields = ("name_string",)


class ImovelUpdateLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImovelUpdateLog
        fields = "__all__"


class NoticeEventTypeFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoticeEventTypeFile
        fields = "__all__"


class NoticeEventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoticeEventType
        fields = "__all__"


class NoticeColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoticeColor
        fields = ("id", "css_color", "notice_event_types", "css_name")
        read_only_fields = ("css_name",)


class NoticeAppealSerializer(serializers.ModelSerializer):
    start_date = serializers.DateField(format="%Y-%m-%d")
    end_date = serializers.DateField(
        format="%Y-%m-%d", required=False, allow_null=True
    )
    id = serializers.IntegerField(required=False)

    def to_internal_value(self, data):
        if "end_date" in data.keys():
            if data["end_date"] == "":
                data["end_date"] = None
        return super(NoticeAppealSerializer, self).to_internal_value(data)

    class Meta:
        model = NoticeAppeal
        fields = "__all__"
        read_only_fields = ("notice_event",)


class NoticeFineSerializer(serializers.ModelSerializer):
    date = serializers.DateField(format="%Y-%m-%d")
    id = serializers.IntegerField(required=False)

    class Meta:
        model = NoticeFine
        fields = "__all__"
        read_only_fields = ("notice_event",)


class NoticeEventSerializer(serializers.ModelSerializer):
    notice_fines = NoticeFineSerializer(many=True, required=False)
    notice_appeals = NoticeAppealSerializer(many=True, required=False)
    deadline_date = serializers.DateField(format="%Y-%m-%d", required=False)
    id = serializers.IntegerField(required=False)

    class Meta:
        model = NoticeEvent
        fields = (
            "id",
            "date",
            "identification",
            "report_number",
            "notice",
            "notice_event_type",
            "deadline",
            "deadline_working_days",
            "deadline_date",
            "concluded",
            "notice_fines",
            "notice_appeals",
            "is_frozen",
        )
        read_only_fields = (
            "is_frozen",
            "notice",
            "deadline_date",
        )


def update_or_create_multiple_notice_events(
    notice, notice_events_data, force_create=False
):
    keep_notice_event = []
    for notice_event in notice_events_data:
        if "notice_fines" in notice_event.keys():
            notice_fines_data = notice_event.pop("notice_fines")
        else:
            notice_fines_data = []
        if "notice_appeals" in notice_event.keys():
            notice_appeals_data = notice_event.pop("notice_appeals")
        else:
            notice_appeals_data = []
        if "id" in notice_event.keys():
            id = notice_event.pop("id")
        else:
            id = 0

        extensions = 0

        for notice_appeal in notice_appeals_data:
            if "extension" in notice_appeal.keys():
                extensions += notice_appeal["extension"]
            if (
                "start_date" in notice_appeal.keys()
                and "end_date" in notice_appeal.keys()
            ):
                extensions += count_days(
                    notice_appeal["start_date"],
                    notice_appeal["end_date"],
                    notice_event["deadline_working_days"],
                )

        deadline_date = add_days(
            notice_event["date"],
            (notice_event["deadline"] + extensions),
            notice_event["deadline_working_days"],
        )

        notice_event_instance = NoticeEvent.objects.filter(id=id).first()
        if notice_event_instance is not None and id != 0 and not force_create:
            for attr, value in notice_event.items():
                setattr(notice_event_instance, attr, value)
            notice_event_instance.deadline_date = deadline_date
            notice_event_instance.save()
        else:
            if "notice" in notice_event.keys():
                notice_event.pop("notice")
            if "deadline_date" in notice_event.keys():
                notice_event.pop("deadline_date")
            notice_event_instance = NoticeEvent.objects.create(
                **notice_event, notice=notice, deadline_date=deadline_date
            )
        keep_notice_event.append(notice_event_instance.id)
        # ====FINES====
        update_or_create_multiple_notice_fines(
            notice_event_instance, notice_fines_data, force_create
        )
        # ====APPEALS====
        update_or_create_multiple_notice_appeals(
            notice_event_instance, notice_appeals_data, force_create
        )
    for notice_event in notice.notice_events.all():
        if notice_event.id not in keep_notice_event:
            notice_event.delete()


def update_or_create_multiple_notice_fines(
    notice_event, notice_fines_data, force_create=False
):
    keep_fine_event = []
    for notice_fine in notice_fines_data:
        if "id" in notice_fine.keys():
            id = notice_fine.pop("id")
        else:
            id = 0
        notice_fine_instance = NoticeFine.objects.filter(id=id).first()
        if notice_fine_instance is not None and id != 0 and not force_create:
            for attr, value in notice_fine.items():
                setattr(notice_fine_instance, attr, value)
            notice_fine_instance.save()
        else:
            notice_fine_instance = NoticeFine.objects.create(
                **notice_fine, notice_event=notice_event
            )
        keep_fine_event.append(notice_fine_instance.id)
    for notice_fine in notice_event.notice_fines.all():
        if notice_fine.id not in keep_fine_event:
            notice_fine.delete()


def update_or_create_multiple_notice_appeals(
    notice_event, notice_appeals_data, force_create=False
):
    keep_appeals_event = []
    for notice_appeals in notice_appeals_data:
        if "id" in notice_appeals.keys():
            id = notice_appeals.pop("id")
        else:
            id = 0
        notice_appeals_instance = NoticeAppeal.objects.filter(id=id).first()
        if (
            notice_appeals_instance is not None
            and id != 0
            and not force_create
        ):
            for attr, value in notice_appeals.items():
                setattr(notice_appeals_instance, attr, value)
            notice_appeals_instance.save()
        else:
            notice_appeals_instance = NoticeAppeal.objects.create(
                **notice_appeals, notice_event=notice_event
            )
        keep_appeals_event.append(notice_appeals_instance.id)
    for notice_appeals in notice_event.notice_appeals.all():
        if notice_appeals.id not in keep_appeals_event:
            notice_appeals.delete()


class NoticeSerializer(serializers.ModelSerializer):
    notice_events = NoticeEventSerializer(many=True)
    date = serializers.DateField(format="%Y-%m-%d")
    imovel = ImovelSerializer(many=False, read_only=True)
    imovel_id = serializers.IntegerField()
    updated = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    class Meta:
        model = Notice
        fields = (
            "id",
            "imovel",
            "imovel_id",
            "document",
            "date",
            "address",
            "description",
            "owner",
            "last_user_to_update",
            "updated",
            "notice_events",
            "css_name",
        )
        read_only_fields = ("updated", "css_name",)

    @transaction.atomic
    def create(self, validated_data):
        if "notice_events" in validated_data.keys():
            notice_events_data = validated_data.pop("notice_events")
        else:
            notice_events_data = []
        if "imovel_id" in validated_data.keys():
            if validated_data["imovel_id"] == 0:
                validated_data["imovel_id"] = getDefaultImovel().id

        notice = Notice.objects.create(**validated_data)
        # ====NOTICE_EVENTS====
        update_or_create_multiple_notice_events(
            notice, notice_events_data, True
        )
        first_date_instance = notice.notice_events.order_by("date").first()
        if first_date_instance:
            notice.date = first_date_instance.date
            notice.save()
        return notice

    @transaction.atomic
    def update(self, instance, validated_data):
        if "notice_events" in validated_data.keys():
            notice_events_data = validated_data.pop("notice_events")
        else:
            notice_events_data = []
        if "imovel_id" in validated_data.keys():
            if validated_data["imovel_id"] == 0:
                validated_data["imovel_id"] = getDefaultImovel().id
        Notice.objects.filter(id=instance.id).update(**validated_data)
        notice = Notice.objects.get(id=instance.id)
        # ====NOTICE_EVENTS====
        update_or_create_multiple_notice_events(notice, notice_events_data)
        first_date_instance = notice.notice_events.order_by("date").first()
        if first_date_instance:
            notice.date = first_date_instance.date
            notice.save()
        return notice


class SurveyEventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyEventType
        fields = "__all__"


class SurveyEventSerializer(serializers.ModelSerializer):

    imovel = ImovelSerializer(many=False, read_only=True)
    date = serializers.DateField(format="%Y-%m-%d")
    imovel_id = serializers.IntegerField()

    class Meta:
        model = SurveyEvent
        fields = (
            "id",
            "imovel",
            "imovel_id",
            "document",
            "identification",
            "date",
            "survey_event_type",
            "address",
            "description",
            "concluded",
            "owner",
            "last_user_to_update",
        )

    @transaction.atomic
    def create(self, validated_data):
        if "imovel_id" in validated_data.keys():
            if validated_data["imovel_id"] == 0:
                validated_data["imovel_id"] = getDefaultImovel().id
        return SurveyEvent.objects.create(**validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        if "imovel_id" in validated_data.keys():
            if validated_data["imovel_id"] == 0:
                validated_data["imovel_id"] = getDefaultImovel().id
        SurveyEvent.objects.filter(id=instance.id).update(**validated_data)
        return SurveyEvent.objects.get(id=instance.id)


class ReportEventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportEventType
        fields = "__all__"


class ReportEventSerializer(serializers.ModelSerializer):

    imovel = ImovelSerializer(many=False, read_only=True)
    date = serializers.DateField(format="%Y-%m-%d")
    imovel_id = serializers.IntegerField()

    class Meta:
        model = ReportEvent
        fields = (
            "id",
            "imovel",
            "imovel_id",
            "document",
            "identification",
            "date",
            "report_event_type",
            "address",
            "description",
            "concluded",
            "owner",
            "last_user_to_update",
        )

    @transaction.atomic
    def create(self, validated_data):
        if "imovel_id" in validated_data.keys():
            if validated_data["imovel_id"] == 0:
                validated_data["imovel_id"] = getDefaultImovel().id
        return ReportEvent.objects.create(**validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        if "imovel_id" in validated_data.keys():
            if validated_data["imovel_id"] == 0:
                validated_data["imovel_id"] = getDefaultImovel().id
        ReportEvent.objects.filter(id=instance.id).update(**validated_data)
        return ReportEvent.objects.get(id=instance.id)


class ActivitySerializer(serializers.ModelSerializer):
    date = serializers.DateField(format="%Y-%m-%d")

    class Meta:
        model = Activity
        fields = "__all__"
