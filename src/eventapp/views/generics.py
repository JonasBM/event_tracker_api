import json
import os
from datetime import datetime
from zipfile import ZipFile

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils import timezone
from eventapp.models import Imovel, ImovelUpdateLog, Notice
from eventapp.serializers import (
    ChangePasswordSerializer,
    ImovelUpdateLogSerializer,
    NoticeSerializer,
    UserProfileSerializer,
)
from eventapp.utils import text_to_id
from knox.auth import TokenAuthentication
from knox.views import LoginView as KnoxLoginView
from rest_framework import generics, permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from django.db.models import Q


def default_imovel_geoitajai():
    imovel_base = [
        {
            "name": "Sem imóvel",
            "code": "000000",
            "filedatetime": timezone.make_aware(datetime(2000, 1, 1, 1, 1, 1)),
        },
        {
            "name": "Pessoa Física",
            "code": "000001",
            "filedatetime": timezone.make_aware(datetime(2000, 1, 1, 1, 1, 1)),
        },
        {
            "name": "Pessoa Jurídica",
            "code": "000002",
            "filedatetime": timezone.make_aware(datetime(2000, 1, 1, 1, 1, 1)),
        },
    ]

    for instance in imovel_base:
        imovel_data = {
            # common
            "codigo_lote": instance["code"],
            "logradouro": instance["name"],
            "numero": "S/N",
            # properties
            "inscricao_imobiliaria": instance["code"],
            "codigo": instance["code"],
            "matricula": instance["code"],
            "numero_contribuinte": instance["code"],
            "updated": timezone.now(),
            "filedatetime": instance["filedatetime"],
        }
        imovel = Imovel.objects.filter(
            inscricao_imobiliaria=instance["code"]
        ).first()
        if not imovel:
            imovel = Imovel(**imovel_data)
            imovel.save()
        else:
            if instance["filedatetime"] > imovel.filedatetime:
                for attr, value in imovel_data.items():
                    setattr(imovel, attr, value)
            imovel.save()
    return True


def download_from_geoitajai(log, file_path, r):
    if not os.path.exists(file_path):
        try:
            print("Salvando em", os.path.abspath(file_path))
            log.state = 11
            log.datetime = timezone.now()
            log.status = "Salvando"
            log.response = "Salvando em", os.path.abspath(file_path)
            log.save()
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 8):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
            print("Salvo em", os.path.abspath(file_path))
            log.state = 19
            log.datetime = timezone.now()
            log.status = "Salvo"
            log.response = "salvo em", os.path.abspath(file_path)
            log.save()
        except Exception as e:
            log.state = 0
            log.datetime = timezone.now()
            log.status = "Falha ao salvar"
            log.response = (
                "Falha ao salvar o arquivos em",
                os.path.abspath(file_path),
                str(e),
            )
            log.save()
            os.remove(file_path)
    else:
        print("Existe em", os.path.abspath(file_path))
        log.state = 19
        log.datetime = timezone.now()
        log.status = "Existente"
        log.response = "Existe em", os.path.abspath(file_path)
        log.save()
    return True


def read_from_geoitajai(log, file_path, r):
    try:
        print("Lendo arquivo compactado")
        log.state = 20
        log.datetime = timezone.now()
        log.status = "Lendo"
        log.response = "Lendo arquivo compactado"
        log.total = 0
        log.inalterados = 0
        log.alterados = 0
        log.novos = 0
        log.progresso = 0
        log.save()
        with ZipFile(file_path, "r") as zip:
            total = 0
            inalterados = 0
            alterados = 0
            novos = 0
            total_files = len(zip.infolist())
            count_files = 0
            for zipfileInfo in zip.infolist():
                count_files += 1
                if zipfileInfo.filename.startswith(
                    "geo-master/data/divisaolotes/exportTabela/"
                ) and zipfileInfo.filename.endswith(".geojson"):
                    filedatetime = timezone.make_aware(
                        datetime(
                            zipfileInfo.date_time[0],
                            zipfileInfo.date_time[1],
                            zipfileInfo.date_time[2],
                            zipfileInfo.date_time[3],
                            zipfileInfo.date_time[4],
                            zipfileInfo.date_time[5],
                        )
                    )
                    data = json.loads(zip.read(zipfileInfo).decode("utf8"))
                    for instance in data:
                        if total % 100 == 0:
                            log.state = 21
                            log.datetime = timezone.now()
                            log.total = total
                            log.inalterados = inalterados
                            log.alterados = alterados
                            log.novos = novos
                            log.progresso = count_files / total_files
                            log.save()
                        total += 1
                        imovel_data = {
                            # common
                            # inscrlig
                            "codigo_lote": instance["properties"]["inscrlig"],
                            # nlogrado
                            "logradouro": instance["properties"]["nlogrado"],
                            # nnumimov
                            "numero": instance["properties"]["nnumimov"],
                            # nnomebai
                            "bairro": instance["properties"]["nnomebai"],
                            # nareater
                            "area_lote": instance["properties"]["nareater"],
                            # properties
                            # ninscrao
                            "inscricao_imobiliaria": instance["properties"][
                                "ninscrao"
                            ],
                            # ncodimov
                            "codigo": instance["properties"]["ncodimov"],
                            # nmatricu
                            "matricula": instance["properties"]["nmatricu"],
                            # nrazaoso
                            "razao_social": instance["properties"]["nrazaoso"],
                            # ncomplem
                            "complemento": instance["properties"]["ncomplem"],
                            # ncodcont
                            "numero_contribuinte": instance["properties"][
                                "ncodcont"
                            ],
                            # nfracaoi
                            "fracao_ideal": instance["properties"]["nfracaoi"],
                            # zon2012predom
                            "zona": instance["properties"]["zon2012predom"],
                            # zon2012
                            "zona2012": instance["properties"]["zon2012"],
                            "updated": timezone.now(),
                            "filedatetime": filedatetime,
                        }
                        
                        imovel = Imovel.objects.filter(
                            inscricao_imobiliaria=instance["properties"][
                                "ninscrao"
                            ]
                        ).first()
                        if not imovel:
                            imovel = Imovel.objects.filter(
                                codigo=instance["properties"][
                                    "ncodimov"
                                ]
                            ).first()
                            
                        if not imovel:
                            novos += 1
                            imovel = Imovel(**imovel_data)
                            imovel.save()
                        else:
                            if filedatetime > imovel.filedatetime:
                                alterados += 1
                                for attr, value in imovel_data.items():
                                    setattr(imovel, attr, value)
                                imovel.save()
                            else:
                                inalterados += 1
                        update_cep_imovel(imovel)
    except Exception as e:
        print("Falha ao ler arquivo compactado")
        print(str(e))
        log.state = 0
        log.datetime = timezone.now()
        log.status = "Falha ao ler"
        log.response = str(e)
        log.save()

    os.remove(file_path)
    print(
        "total: " + str(total),
        "inalterados: " + str(inalterados),
        "alterados: " + str(alterados),
        "novos: " + str(novos),
    )
    print("Done!")
    log.state = 99
    log.datetime = timezone.now()
    log.total = total
    log.inalterados = inalterados
    log.alterados = alterados
    log.novos = novos
    log.status = "Finalizado"
    log.response = (
        "Imóveis atualizados ("
        + str(novos)
        + " novos e "
        + str(alterados)
        + " alterados)"
    )
    log.save()
    return True


def update_cep_imovel(imovel):

    if not imovel:
        return False

    if imovel.cep:
        if len(imovel.cep) >= 8:
            return True

    url_str = (
        "https://buscacepinter.correios.com.br"
        "/app"
        "/localidade_logradouro"
        "/carrega-localidade-logradouro.php"
    )
    logradouro = ''
    if imovel.logradouro:
        logradouro = imovel.logradouro.lower().strip()
        if logradouro.startswith("r."):
            logradouro = logradouro.replace("r.", "", 1).strip()
        if logradouro.startswith("av."):
            logradouro = logradouro.replace("av.", "", 1).strip()
        if logradouro.endswith("bc."):
            logradouro = "".join(logradouro.rsplit("bc.", 1)).strip()
        if logradouro.endswith("jr"):
            logradouro = "".join(logradouro.rsplit("jr", 1)).strip()

    numero = ''
    if imovel.numero:
        numero = imovel.numero.lower().strip()
        if numero.startswith("n"):
            numero = numero.replace("n", "", 1).strip()
        if numero == "s/n":
            numero = ""

    data = {
        "uf": "SC",
        "localidade": "Itajai",
        "logradouro": logradouro,
        "numeroLogradouro": numero,
    }

    query_logradouro = Q(logradouro=imovel.logradouro)
    query_numero = Q(numero=imovel.numero)
    query_bairro = Q(bairro=imovel.bairro)
    query_cep = Q(cep__isnull=False)
    query = Q(
        query_logradouro,
        query_numero,
        query_bairro,
        query_cep,
    )
    imovel_with_cep = Imovel.objects.filter(query).first()
    if imovel_with_cep:
        if imovel_with_cep.cep:
            if len(imovel_with_cep.cep) >= 8:
                imovel.cep = imovel_with_cep.cep
                imovel.save()
                return True

    try:
        r = requests.get(url_str, params=data)
        if r.ok:
            jsonresponse = r.json()
            if jsonresponse["total"] == 1:
                imovel.cep = jsonresponse["dados"][0]["cep"]
                imovel.save()
            else:
                ceps = []
                for cep_data in jsonresponse["dados"]:
                    if text_to_id(imovel.bairro) == text_to_id(
                        cep_data["bairro"]
                    ):
                        ceps.append(cep_data["cep"])
                if len(ceps) == 1:
                    imovel.cep = ceps[0]
                    imovel.save()
                else:
                    print(imovel.id, imovel)
        else:
            print(r)
    except Exception as e:
        print(imovel.id, imovel)
        print("Falha request correios: " + e)
    return True


def update_cep():
    url_str = (
        "https://buscacepinter.correios.com.br"
        "/app"
        "/localidade_logradouro"
        "/carrega-localidade-logradouro.php"
    )
    imoveis = Imovel.objects.all()
    total = 0
    alterados = 0
    inalterados = 0
    errors = 0

    dest_folder = settings.MEDIA_ROOT + "//temp_geoitajai"
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    filename = datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "-cep_log.txt"
    file_path = os.path.join(dest_folder, filename)
    with open(file_path, "w") as text_file:
        for imovel in imoveis:
            if total % 500 == 0:
                print(
                    "Total: " + str(total),
                    "Alterados: " + str(alterados),
                    "Inalterados: " + str(inalterados),
                    "Errors: " + str(errors),
                )
                print(
                    "Total: "
                    + str(total)
                    + " - "
                    + "Alterados: "
                    + str(alterados)
                    + " - "
                    + "Inalterados: "
                    + str(inalterados)
                    + " - "
                    + "Errors: "
                    + str(errors),
                    file=text_file,
                )
            total += 1

            if not imovel.cep:

                logradouro = imovel.logradouro.lower().strip()
                if logradouro.startswith("r."):
                    logradouro = logradouro.replace("r.", "", 1).strip()
                if logradouro.startswith("av."):
                    logradouro = logradouro.replace("av.", "", 1).strip()
                if logradouro.endswith("bc."):
                    logradouro = "".join(logradouro.rsplit("bc.", 1)).strip()
                if logradouro.endswith("jr"):
                    logradouro = "".join(logradouro.rsplit("jr", 1)).strip()

                numero = imovel.numero.lower().strip()
                if numero.startswith("n"):
                    numero = numero.replace("n", "", 1).strip()
                if numero == "s/n":
                    numero = ""

                data = {
                    "uf": "SC",
                    "localidade": "Itajai",
                    "logradouro": logradouro,
                    "numeroLogradouro": numero,
                }

                data = {
                    "uf": "SC",
                    "localidade": "Itajai",
                    "logradouro": logradouro,
                    "numeroLogradouro": numero,
                }
                try:
                    r = requests.get(url_str, params=data)
                    if r.ok:
                        jsonresponse = r.json()
                        if jsonresponse["total"] == 1:
                            imovel.cep = jsonresponse["dados"][0]["cep"]
                            imovel.save()
                            alterados += 1
                        else:
                            ceps = []
                            for cep_data in jsonresponse["dados"]:
                                if text_to_id(imovel.bairro) == text_to_id(
                                    cep_data["bairro"]
                                ):
                                    ceps.append(cep_data["cep"])
                            if len(ceps) == 1:
                                imovel.cep = ceps[0]
                                imovel.save()
                                query_logradouro = Q(
                                    logradouro=imovel.logradouro
                                )
                                query_numero = Q(numero=imovel.numero)
                                query_bairro = Q(bairro=imovel.bairro)
                                query_cep = Q(cep__isnull=True)
                                query = Q(
                                    query_logradouro,
                                    query_numero,
                                    query_bairro,
                                    query_cep,
                                )
                                count = Imovel.objects.filter(query).count()
                                if count > 0:
                                    print(ceps[0] + "-" + count)
                                    Imovel.objects.filter(query).update(
                                        cep=imovel.cep
                                    )
                                alterados += 1 + count
                            else:
                                errors += 1
                                print(
                                    "id: "
                                    + str(imovel.id)
                                    + " - imovel: "
                                    + str(imovel),
                                    file=text_file,
                                )
                                print(len(ceps), imovel)
                    else:
                        print(r)
                except Exception as e:
                    print(imovel.id, imovel)
                    print("Falha request correios: " + e)
            else:
                inalterados += 1
    return True


class migrate_from_geoitajai(generics.RetrieveAPIView):
    permission_classes = [
        permissions.IsAdminUser,
    ]

    def get(self, request, *args, **kwargs):

        authorized = False
        check = self.request.query_params.get("check", None)
        if check:
            if check == datetime.now().strftime("%Y-%m-%d"):
                authorized = True

        if not authorized:
            return Response(
                {"detail": "Não Autorizado"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        else:

            dest_folder = settings.MEDIA_ROOT + "//temp_geoitajai"
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)

            filename = (
                datetime.now().strftime("%Y-%m-%d")
                + "-migrate_from_geoitajai_running.txt"
            )
            file_path_migrate_running = os.path.join(dest_folder, filename)

            if os.path.exists(file_path_migrate_running):
                return Response(
                    {
                        "detail": (
                            "Migração de dados não pode ocorrer em paralelo"
                        )
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            else:
                with open(file_path_migrate_running, "w"):
                    pass

            # os.remove(file_path_migrate_running)
            # return Response({'detail': 'Finalizado'})
            default_imovel_geoitajai()
            print("baixando arquivo")
            log = ImovelUpdateLog(
                state=10,
                datetime_started=timezone.now(),
                datetime=timezone.now(),
                status="baixando",
                response="Baixando arquivo",
            )
            log.save()
            url = "https://github.com/geoitajai/geo/archive/master.zip"
            filename = (
                datetime.now().strftime("%Y-%m-%d") + "-geoitajai_geo.zip"
            )
            file_path = os.path.join(dest_folder, filename)
            r = requests.get(url, stream=True)
            if r.ok:
                if download_from_geoitajai(log, file_path, r):
                    if read_from_geoitajai(log, file_path, r):
                        pass
                        # update_cep(log)
            else:  # HTTP status code 4XX/5XX
                print(
                    "Download failed: status code {}\n{}".format(
                        r.status_code, r.text
                    )
                )
                log.state = 0
                log.datetime = timezone.now()
                log.total = 0
                log.inalterados = 0
                log.alterados = 0
                log.novos = 0
                log.status = "Falhou"
                log.response = "Download failed: status code {}\n{}".format(
                    r.status_code, r.text
                )
                log.save()

            os.remove(file_path_migrate_running)
            return Response(
                {"detail": "Finalizado"}, status=status.HTTP_200_OK
            )


def migra_from_old_db(request):
    # return HttpResponse("DESABILITADO")
    notices = Notice.objects.all()
    for notice in notices:
        for notice_event in notice.notice_events.all():
            notice_event.date = notice.date
            notice_event.save()
    print("migra_from_old_db")
    return HttpResponse("migra_from_old_db")


class buscacep(generics.RetrieveAPIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    def get(self, request, *args, **kwargs):
        params = request.GET.copy()
        logradouro = params["logradouro"].lower().strip()
        if logradouro.startswith("r."):
            logradouro = logradouro.replace("r.", "", 1).strip()
        if logradouro.startswith("av."):
            logradouro = logradouro.replace("av.", "", 1).strip()
        if logradouro.endswith("jr"):
            logradouro = "".join(logradouro.rsplit("jr", 1)).strip()
        params["logradouro"] = logradouro
        url_str = (
            "https://buscacepinter.correios.com.br"
            "/app"
            "/localidade_logradouro"
            "/carrega-localidade-logradouro.php"
        )
        r = requests.get(url_str, params=params)
        if r.ok:
            return Response(r.json(), status=status.HTTP_200_OK)
        return Response(status=status.HTTP_404_NOT_FOUND)


class LoginView(KnoxLoginView):
    authentication_classes = [BasicAuthentication, TokenAuthentication]

    def get(self, request, format=None):
        content = {
            "user": UserProfileSerializer(
                request.user, context=self.get_context()
            ).data
        }
        return Response(content)


class ImovelUpdateLogView(generics.RetrieveAPIView):
    permission_classes = [
        permissions.IsAdminUser,
    ]
    serializer_class = ImovelUpdateLogSerializer

    def get_object(self):
        result = ImovelUpdateLog.objects.order_by("-datetime").all().first()
        if result:
            return result
        else:
            return None


class ChangePasswordView(generics.UpdateAPIView):
    model = User
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    serializer_class = ChangePasswordSerializer

    def get_object(self, queryset=None):
        obj = self.request.user
        return obj

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            if not self.object.check_password(
                serializer.data.get("old_password")
            ):
                return Response(
                    {"old_password": ["Senha incorreta."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            response = {
                "status": "success",
                "code": status.HTTP_200_OK,
                "message": "Senha atualizada com sucesso",
                "data": [],
            }
            return Response(response)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLatestNotice(generics.RetrieveAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]
    serializer_class = NoticeSerializer

    def get_object(self):
        queryset = self.request.user.notices
        imovel_id = self.request.query_params.get("imovel_id", None)
        if imovel_id:
            queryset = queryset.filter(imovel__id=imovel_id)
        result = queryset.order_by("-notice_events__date").all().first()
        if result:
            return result
        else:
            return None
