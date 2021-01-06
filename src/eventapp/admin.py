from django.contrib import admin
from eventapp.models import (
    Profile,
    ImovelUpdateLog,
    Imovel,
    Notice,
    NoticeEvent,
    NoticeEventType,
    NoticeColor,
    NoticeFine,
    SurveyEvent,
    SurveyEventType,
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
admin.site.register(NoticeColor)
admin.site.register(NoticeFine)


class SurveyEventAdmin(admin.ModelAdmin):
    raw_id_fields = ("imovel",)


admin.site.register(SurveyEvent, SurveyEventAdmin)
admin.site.register(SurveyEventType)

admin.site.register(Activity)
