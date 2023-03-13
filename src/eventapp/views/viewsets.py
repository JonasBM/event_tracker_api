from django.contrib.auth.models import User
from django.db.models import Case, Q, When
from eventapp.models import (Activity, Imovel, Notice, NoticeColor,
                             NoticeEventType, NoticeEventTypeFile, ReportEvent,
                             ReportEventType, SurveyEvent, SurveyEventType)
from eventapp.serializers import (ActivitySerializer, ImovelSerializer,
                                  NoticeColorSerializer,
                                  NoticeEventTypeFileSerializer,
                                  NoticeEventTypeSerializer, NoticeSerializer,
                                  ReportEventSerializer,
                                  ReportEventTypeSerializer,
                                  SurveyEventSerializer,
                                  SurveyEventTypeSerializer,
                                  UserProfileSerializer, UserSerializer)
from eventapp.utils import getDateFromString
from eventapp.views.permissions import (IsAdminUserOrIsAuthenticatedReadOnly,
                                        IsAdminUserOrIsOwner,)
from rest_framework import permissions, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response


class UserProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAdminUserOrIsOwner,
    ]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return User.objects.order_by(
                "first_name",
                "last_name",
            ).all()
        elif self.request.user.is_staff:
            return User.objects.order_by(
                "first_name",
                "last_name",
            ).filter(is_superuser=False)
        else:
            return User.objects.filter(id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            password = None
            if "password" in request.data.keys():
                password = request.data.pop("password")
            response = super(UserProfileViewSet, self).create(
                request, *args, **kwargs
            )
            if password:
                user = User.objects.filter(id=response.data["id"]).first()
                if user:
                    user.set_password(password)
                    user.save()
                    return response
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        if not self.request.user.is_staff:
            request.data.pop("is_superuser")
            request.data.pop("is_staff")
            request.data.pop("is_active")
            request.data.pop("groups")
            request.data.pop("user_permissions")
            request.data["profile"].pop("user_type")
        else:
            password = None
            if "password" in request.data.keys():
                password = request.data.pop("password")
            if password:
                user = User.objects.filter(id=request.data["id"]).first()
                if user:
                    user.set_password(password)
                    user.save()
        return super(UserProfileViewSet, self).update(request, *args, **kwargs)


class LimitedResultsSetPagination(PageNumberPagination):
    page_size = 11
    page_size_query_param = "page_size"
    max_page_size = 1000


class ImovelViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    serializer_class = ImovelSerializer
    queryset = Imovel.objects.all()
    pagination_class = LimitedResultsSetPagination

    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

    def get_queryset(self):

        queryset = Imovel.objects

        query = None

        imovel_id = self.request.query_params.get("id", None)
        if imovel_id:
            query = Q(id=imovel_id)

        query_logradouro = None
        street = self.request.query_params.get("street", None)
        if street:
            query_logradouro = Q(logradouro__trigram_similar=street)

        query_number = Q()
        number = self.request.query_params.get("number", None)
        if number:
            query_number = Q(numero__unaccent__icontains=number)

        query_complemento = Q()
        complemento = self.request.query_params.get("complemento", None)
        if complemento:
            query_complemento = Q(complemento__unaccent__icontains=complemento)

        query_bairro = Q()
        bairro = self.request.query_params.get("bairro", None)
        if bairro:
            query_bairro = Q(bairro__unaccent__icontains=bairro)

        query_codigo = None
        codigo = self.request.query_params.get("codigo", None)

        if codigo:
            query_codigo = Q(codigo__unaccent__icontains=codigo)

        query_inscricao_imobiliaria = None
        inscricao_imobiliaria = self.request.query_params.get(
            "inscricao_imobiliaria", None
        )
        if inscricao_imobiliaria:
            query_inscricao_imobiliaria = Q(
                inscricao_imobiliaria__startswith=inscricao_imobiliaria
            )

        if query_logradouro:
            if query:
                query = Q(
                    query | query_logradouro,
                    query_number,
                    query_complemento,
                    query_bairro,
                )
            else:
                query = Q(
                    query_logradouro,
                    query_number,
                    query_complemento,
                    query_bairro,
                )

        if query_codigo and not query_number:
            if query:
                query = Q(query | query_codigo)
            else:
                query = Q(query_codigo)

        if query_inscricao_imobiliaria and not query_number:
            if query:
                query = Q(query | query_inscricao_imobiliaria)
            else:
                query = Q(query_inscricao_imobiliaria)

        if query:
            queryset = queryset.filter(query)

        case_id = When(id=None, then=0)
        if imovel_id:
            case_id = When(id=imovel_id, then=0)

        case_codigo = When(codigo=None, then=1)
        if codigo:
            case_codigo = When(codigo=codigo, then=1)

        return (
            queryset.all()
            .order_by(Case(case_id, case_codigo, default=2))
            .all()
        )


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = User.objects
        # assistente_only = self.request.query_params.get("assistente_only", False)
        # if assistente_only:
        #     queryset = queryset.filter(profile__user_type=Profile.ASSISTENTE)

        if self.request.user.is_superuser:
            queryset = queryset.order_by(
                Case(When(id=self.request.user.id, then=0), default=1),
                "first_name",
                "last_name",
            ).all()
        elif (
            self.request.user.is_staff
            or not self.request.user.profile.is_particular()
        ):
            queryset = queryset.order_by(
                Case(When(id=self.request.user.id, then=0), default=1),
                "first_name",
                "last_name",
            ).filter(is_superuser=False)
        else:
            queryset = queryset.filter(id=self.request.user.id)
        return queryset


class NoticeEventTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAdminUserOrIsAuthenticatedReadOnly,
    ]
    serializer_class = NoticeEventTypeSerializer
    queryset = NoticeEventType.objects.all()


class NoticeEventTypeFileViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAdminUserOrIsAuthenticatedReadOnly,
    ]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = NoticeEventTypeFileSerializer
    queryset = NoticeEventTypeFile.objects.all()


class NoticeColorViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAdminUserOrIsAuthenticatedReadOnly,
    ]
    serializer_class = NoticeColorSerializer
    queryset = NoticeColor.objects.all()


class SurveyEventTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAdminUserOrIsAuthenticatedReadOnly,
    ]
    serializer_class = SurveyEventTypeSerializer
    queryset = SurveyEventType.objects.all()


class ReportEventTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAdminUserOrIsAuthenticatedReadOnly,
    ]
    serializer_class = ReportEventTypeSerializer
    queryset = ReportEventType.objects.all()


class UserNoticeViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    serializer_class = NoticeSerializer

    def get_queryset(self):
        start_date = getDateFromString(
            self.request.query_params.get("start_date", None)
        )
        end_date = getDateFromString(
            self.request.query_params.get("end_date", None)
        )

        if (
            not self.request.user.is_staff
            and self.request.user.profile.is_particular()
        ):
            queryset = Notice.objects.filter(owner=self.request.user)
        else:
            user_id = self.request.query_params.get("user_id", None)
            if user_id:
                queryset = Notice.objects.filter(owner=user_id)
            else:
                queryset = Notice.objects

        if start_date and end_date:
            query_notice = Q(notice_events__date__range=[start_date, end_date])
            query_deadline = Q(
                notice_events__deadline_date__range=[start_date, end_date]
            )
            queryset = queryset.distinct().filter(
                query_notice | query_deadline
            )
        elif start_date:
            query_notice = Q(notice_events__date__gte=start_date)
            query_deadline = Q(notice_events__deadline_date__gte=start_date)
            queryset = queryset.distinct().filter(
                query_notice | query_deadline
            )
        elif end_date:
            query_notice = Q(notice_events__date__lte=end_date)
            query_deadline = Q(notice_events__deadline_date__lte=end_date)
            queryset = queryset.distinct().filter(
                query_notice | query_deadline
            )

        imovel_id = self.request.query_params.get("imovel_id", None)
        if imovel_id:
            queryset = queryset.filter(imovel_id=imovel_id)

        identification = self.request.query_params.get("identification", None)
        if identification:
            queryset = queryset.distinct().filter(
                notice_events__identification__unaccent__icontains=identification
            )

        document = self.request.query_params.get("document", None)
        if document:
            queryset = queryset.filter(document__unaccent__icontains=document)

        concluded = self.request.query_params.get("concluded", None)
        if concluded == "0":
            queryset = queryset.distinct().filter(
                notice_events__concluded=False
            )
        elif concluded == "1":
            queryset = queryset.distinct().filter(
                notice_events__concluded=True
            )

        unfinished = self.request.query_params.get("unfinished", None)
        if unfinished:
            queryset = queryset.distinct().filter(
                notice_events__concluded=False
            )

        incompatible = self.request.query_params.get("incompatible", None)
        if incompatible:
            queryset = queryset.distinct().filter(Q(imovel_id=None))

        return queryset

    def create(self, request, *args, **kwargs):
        owner_user = User.objects.get(id=request.data["owner"])
        if (
            owner_user and
            owner_user.profile.has_my_permission(request.user) and
            not owner_user.profile.is_assistente()
        ):
            if "imovel_id" not in request.data.keys():
                request.data["imovel_id"] = 0
            request.data["last_user_to_update"] = request.user.id
            return super(UserNoticeViewSet, self).create(request, *args, **kwargs)
        return Response({"detail": "Não Autorizado"}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        owner_user = User.objects.get(id=request.data["owner"])
        if (
            owner_user and
            owner_user.profile.has_my_permission(request.user) and
            not owner_user.profile.is_assistente()
        ):
            if "imovel_id" not in request.data.keys():
                request.data["imovel_id"] = 0
            request.data["last_user_to_update"] = request.user.id
            return super(UserNoticeViewSet, self).update(request, *args, **kwargs)
        return Response({"detail": "Não Autorizado"}, status=status.HTTP_403_FORBIDDEN)


class UserSurveyEventViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    serializer_class = SurveyEventSerializer

    def get_queryset(self):

        start_date = getDateFromString(
            self.request.query_params.get("start_date", None)
        )
        end_date = getDateFromString(
            self.request.query_params.get("end_date", None)
        )

        if (
            not self.request.user.is_staff
            and self.request.user.profile.is_particular()
        ):
            queryset = SurveyEvent.objects.filter(owner=self.request.user)
        else:
            user_id = self.request.query_params.get("user_id", None)
            if user_id:
                queryset = SurveyEvent.objects.filter(owner=user_id)
            else:
                queryset = SurveyEvent.objects

        if start_date and end_date:
            query_survey = Q(date__range=[start_date, end_date])
            queryset = queryset.distinct().filter(query_survey)
        elif start_date:
            query_survey = Q(date__gte=start_date)
            queryset = queryset.distinct().filter(query_survey)
        elif end_date:
            query_survey = Q(date__lte=end_date)
            queryset = queryset.distinct().filter(query_survey)

        imovel_id = self.request.query_params.get("imovel_id", None)
        if imovel_id:
            queryset = queryset.filter(imovel_id=imovel_id)

        identification = self.request.query_params.get("identification", None)
        if identification:
            queryset = queryset.filter(
                identification__unaccent__icontains=identification
            )

        document = self.request.query_params.get("document", None)
        if document:
            queryset = queryset.filter(document__unaccent__icontains=document)

        concluded = self.request.query_params.get("concluded", None)
        if concluded == "0":
            queryset = queryset.filter(concluded=False)
        elif concluded == "1":
            queryset = queryset.filter(concluded=True)

        unfinished = self.request.query_params.get("unfinished", None)
        if unfinished:
            queryset = queryset.distinct().filter(concluded=False)

        incompatible = self.request.query_params.get("incompatible", None)
        if incompatible:
            queryset = queryset.distinct().filter(Q(imovel_id=None))

        return queryset

    def create(self, request, *args, **kwargs):
        owner_user = User.objects.get(id=request.data["owner"])
        if (
            owner_user and
            owner_user.profile.has_my_permission(request.user) and
            not owner_user.profile.is_assistente()
        ):
            if "imovel_id" not in request.data.keys():
                request.data["imovel_id"] = 0
            request.data["last_user_to_update"] = request.user.id
            return super(UserSurveyEventViewSet, self).create(
                request, *args, **kwargs
            )
        return Response({"detail": "Não Autorizado"}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        owner_user = User.objects.get(id=request.data["owner"])
        if (
            owner_user and
            owner_user.profile.has_my_permission(request.user) and
            not owner_user.profile.is_assistente()
        ):
            if "imovel_id" not in request.data.keys():
                request.data["imovel_id"] = 0
            request.data["last_user_to_update"] = request.user.id
            return super(UserSurveyEventViewSet, self).update(
                request, *args, **kwargs
            )
        return Response({"detail": "Não Autorizado"}, status=status.HTTP_403_FORBIDDEN)


class UserReportEventViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    serializer_class = ReportEventSerializer

    def get_queryset(self):

        start_date = getDateFromString(
            self.request.query_params.get("start_date", None)
        )
        end_date = getDateFromString(
            self.request.query_params.get("end_date", None)
        )

        if (
            not self.request.user.is_staff
            and self.request.user.profile.is_particular()
        ):
            queryset = ReportEvent.objects.filter(owner=self.request.user)
        else:
            user_id = self.request.query_params.get("user_id", None)
            if user_id:
                queryset = ReportEvent.objects.filter(owner=user_id)
            else:
                queryset = ReportEvent.objects

        if start_date and end_date:
            query_report = Q(date__range=[start_date, end_date])
            queryset = queryset.distinct().filter(query_report)
        elif start_date:
            query_report = Q(date__gte=start_date)
            queryset = queryset.distinct().filter(query_report)
        elif end_date:
            query_report = Q(date__lte=end_date)
            queryset = queryset.distinct().filter(query_report)

        imovel_id = self.request.query_params.get("imovel_id", None)
        if imovel_id:
            queryset = queryset.filter(imovel_id=imovel_id)

        identification = self.request.query_params.get("identification", None)
        if identification:
            queryset = queryset.filter(
                identification__unaccent__icontains=identification
            )

        document = self.request.query_params.get("document", None)
        if document:
            queryset = queryset.filter(document__unaccent__icontains=document)

        concluded = self.request.query_params.get("concluded", None)
        if concluded == "0":
            queryset = queryset.filter(concluded=False)
        elif concluded == "1":
            queryset = queryset.filter(concluded=True)

        unfinished = self.request.query_params.get("unfinished", None)
        if unfinished:
            queryset = queryset.distinct().filter(concluded=False)

        incompatible = self.request.query_params.get("incompatible", None)
        if incompatible:
            queryset = queryset.distinct().filter(Q(imovel_id=None))

        return queryset

    def create(self, request, *args, **kwargs):
        owner_user = User.objects.get(id=request.data["owner"])
        if owner_user and owner_user.profile.has_my_permission(request.user):
            if "imovel_id" not in request.data.keys():
                request.data["imovel_id"] = 0
            request.data["last_user_to_update"] = request.user.id
            return super(UserReportEventViewSet, self).create(
                request, *args, **kwargs
            )
        return Response({"detail": "Não Autorizado"}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        owner_user = User.objects.get(id=request.data["owner"])
        if owner_user and owner_user.profile.has_my_permission(request.user):
            if "imovel_id" not in request.data.keys():
                request.data["imovel_id"] = 0
            request.data["last_user_to_update"] = request.user.id
            return super(UserReportEventViewSet, self).update(
                request, *args, **kwargs
            )
        return Response({"detail": "Não Autorizado"}, status=status.HTTP_403_FORBIDDEN)


class UserActivityViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    serializer_class = ActivitySerializer

    def get_queryset(self):
        start_date = getDateFromString(
            self.request.query_params.get("start_date", None)
        )
        end_date = getDateFromString(
            self.request.query_params.get("end_date", None)
        )

        if (
            not self.request.user.is_staff
            and self.request.user.profile.is_particular()
        ):
            queryset = Activity.objects.filter(owner=self.request.user)
        else:
            user_id = self.request.query_params.get("user_id", None)
            if user_id:
                queryset = Activity.objects.filter(owner=user_id)
            else:
                queryset = Activity.objects

        if start_date and end_date:
            query_activity = Q(date__range=[start_date, end_date])
            queryset = queryset.distinct().filter(query_activity)
        elif start_date:
            query_activity = Q(date__gte=start_date)
            queryset = queryset.distinct().filter(query_activity)
        elif end_date:
            query_activity = Q(date__lte=end_date)
            queryset = queryset.distinct().filter(query_activity)
        else:
            queryset = queryset
        return queryset

    def create(self, request, *args, **kwargs):
        owner_user = User.objects.get(id=request.data["owner"])
        if owner_user and owner_user.profile.has_my_permission(request.user):
            request.data["last_user_to_update"] = request.user.id
            return super(UserActivityViewSet, self).create(
                request, *args, **kwargs
            )
        return Response({"detail": "Não Autorizado"}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        owner_user = User.objects.get(id=request.data["owner"])
        if owner_user and owner_user.profile.has_my_permission(request.user):
            request.data["last_user_to_update"] = request.user.id
            return super(UserActivityViewSet, self).update(
                request, *args, **kwargs
            )
        return Response({"detail": "Não Autorizado"}, status=status.HTTP_403_FORBIDDEN)
