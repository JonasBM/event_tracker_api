from django.urls import include, path
from rest_framework import routers
from eventapp.views import viewsets
from eventapp.views import generics
from eventapp.views import documents

router = routers.DefaultRouter()
router.register(r"user", viewsets.UserViewSet, "user")
router.register(r"userprofile", viewsets.UserProfileViewSet, "userprofile")
router.register(r"imovel", viewsets.ImovelViewSet, "imovel")
router.register(
    r"noticeeventtype", viewsets.NoticeEventTypeViewSet, "noticeeventtype"
)
router.register(
    r"noticeeventtypefile", viewsets.NoticeEventTypeFileViewSet, "noticeeventtypefile"
)
router.register(r"noticecolor", viewsets.NoticeColorViewSet, "noticecolor")
router.register(
    r"surveyeventtype", viewsets.SurveyEventTypeViewSet, "surveyeventtype"
)
router.register(
    r"reporteventtype", viewsets.ReportEventTypeViewSet, "reporteventtype"
)
router.register(r"notice", viewsets.UserNoticeViewSet, "notice")
router.register(r"survey", viewsets.UserSurveyEventViewSet, "survey")
router.register(r"report", viewsets.UserReportEventViewSet, "report")
router.register(r"activity", viewsets.UserActivityViewSet, "activity")

urlpatterns = [
    path(r"auth/login/", generics.LoginView.as_view(), name="knox_login"),
    path(r"auth/", include("knox.urls")),
    path(
        r"latestnotice/",
        generics.UserLatestNotice.as_view(),
        name="latestnotice",
    ),
    path(r"changepassword/", generics.ChangePasswordView.as_view()),
    path(
        r"geoitajai/",
        generics.migrate_from_geoitajai.as_view(),
        name="geoitajai",
    ),
    path(
        r"imovelupdatelog/",
        generics.ImovelUpdateLogView.as_view(),
        name="imovelupdatelog",
    ),
    path(r"buscacep/", generics.buscacep.as_view(), name="buscacep"),
    path(
        r"migrafromolddb/", generics.migra_from_old_db, name="migrafromolddb"
    ),
]

urlpatterns += [
    path(r"reportpdf/", documents.ReportPDF.as_view()),
    path(r"sheetcsv/", documents.sheetCSV.as_view()),
    path(r"noticereportdocx/", documents.NoticeReportDocx.as_view()),
    path(r"varequestdocx/", documents.VARequestDocx.as_view()),
    path(r"filevarequestdocx/", documents.FileVARequestDocx.as_view()),
    path(r"downloadnotification/", documents.downloadNotification.as_view()),
]

urlpatterns += router.urls
