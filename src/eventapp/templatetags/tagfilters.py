from django import template

register = template.Library()


@register.filter
def filter_report_event_type(objetos, report_event_type):
    return objetos.filter(report_event_type=report_event_type).all()


@register.filter
def count_report_event_type(objetos, report_event_type):
    return objetos.filter(report_event_type=report_event_type).count()


@register.filter
def filter_survey_event_type(objetos, survey_event_type):
    return objetos.filter(survey_event_type=survey_event_type).all()


@register.filter
def count_survey_event_type(objetos, survey_event_type):
    return objetos.filter(survey_event_type=survey_event_type).count()


@register.filter
def filter_notice_event_type(objetos, notice_event_type):
    return objetos.filter(notice_event_type=notice_event_type).all()


@register.filter
def count_notice_event_type(objetos, notice_event_type):
    return objetos.filter(notice_event_type=notice_event_type).count()
