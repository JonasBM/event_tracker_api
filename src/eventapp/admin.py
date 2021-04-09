from django.contrib import admin
from eventapp.models import (
    Profile,
    ImovelUpdateLog,
    Imovel,
    Notice,
    NoticeEvent,
    NoticeEventType,
    NoticeEventTypeFile,
    NoticeColor,
    NoticeFine,
    NoticeAppeal,
    SurveyEvent,
    SurveyEventType,
    ReportEvent,
    ReportEventType,
    Activity,
)

admin.site.register(Profile)
admin.site.register(Imovel)
admin.site.register(ImovelUpdateLog)


class NoticeAdmin(admin.ModelAdmin):
    raw_id_fields = ("imovel",)


admin.site.register(Notice, NoticeAdmin)
admin.site.register(NoticeEvent)
admin.site.register(NoticeEventType)
admin.site.register(NoticeEventTypeFile)
admin.site.register(NoticeColor)
admin.site.register(NoticeFine)
admin.site.register(NoticeAppeal)


class SurveyEventAdmin(admin.ModelAdmin):
    raw_id_fields = ("imovel",)


admin.site.register(SurveyEvent, SurveyEventAdmin)
admin.site.register(SurveyEventType)


class ReportEventAdmin(admin.ModelAdmin):
    raw_id_fields = ("imovel",)


admin.site.register(ReportEvent, ReportEventAdmin)
admin.site.register(ReportEventType)

admin.site.register(Activity)
