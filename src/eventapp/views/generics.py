import logging
import os
from datetime import datetime

import pandas as pd
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core import serializers
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from knox.auth import TokenAuthentication
from knox.views import LoginView as KnoxLoginView
from rest_framework import generics, permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.response import Response

from eventapp.models import Imovel, ImovelUpdateLog
from eventapp.serializers import (ChangePasswordSerializer,
                                  ImovelUpdateLogSerializer, NoticeSerializer,
                                  UserProfileSerializer)
from eventapp.utils import text_to_id

logger = logging.getLogger(__name__)


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
    logradouro = ""
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
        if logradouro.startswith("trav."):
            logradouro = logradouro.replace("trav.", "", 1).strip()
        if logradouro.endswith("rod."):
            logradouro = "".join(logradouro.rsplit("rod.", 1)).strip()
        if logradouro.endswith("bc"):
            logradouro = "".join(logradouro.rsplit("bc", 1)).strip()

    numero = ""
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
        "tipologradouro": "",
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
        r = requests.post(url_str, data=data)

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
            print(r)
    except Exception as e:
        print('CEP: ', imovel.id, str(imovel))
        print('CEP: ', "Falha request correios: " + e)
    return True


def get_dataframe_from_file(file, log: ImovelUpdateLog) -> pd.DataFrame:

    print("Preparando arquivo")
    log.state = 10
    log.status = "Preparando"
    log.response = "Preparando arquivo"
    log.save()

    columns_dict = {
        'Código imóvel': 'codigo',
        'Inscrição': 'inscricao_imobiliaria',
        'Cód. contribuinte': 'numero_contribuinte',
        'Logradouro': 'logradouro',
        'Nº imóvel': 'numero',
        'Nome do bairro': 'bairro',
        'Complemento': 'complemento',
        'Área do terreno m2': 'area_lote',
        'Razão Social': 'razao_social',
        'CNPJ CPF': 'cnpj_cpf',
    }

    dtype = {
        'Código imóvel': str,
        'Inscrição': str,
        'Cód. contribuinte': str,
        'Logradouro': str,
        'Nº imóvel': str,
        'Nome do bairro': str,
        'Complemento': str,
        'Área do terreno m2': str,
        'Razão Social': str,
        'CNPJ CPF': str,
    }

    try:
        excel = pd.read_excel(
            file,
            dtype=dtype,
            usecols=columns_dict.keys()
        )
        df = pd.DataFrame(excel).dropna(how='all')
        df = df.where(df.notnull(), None)
        df = df.rename(columns=columns_dict)

        return df

    except ValueError as e:
        raise ParseError(e)


def update_default_imovel(log: ImovelUpdateLog):
    imovel_base = [
        {
            "name": "Sem imóvel",
            "code": "000000",
        },
        {
            "name": "Pessoa Física",
            "code": "000001",
        },
        {
            "name": "Pessoa Jurídica",
            "code": "000002",
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
            "numero_contribuinte": instance["code"],
        }
        imovel = Imovel.objects.filter(inscricao_imobiliaria=instance["code"]).first()
        if not imovel:
            imovel = Imovel(**imovel_data)
            imovel.save()
    return True


def create_imovel(imovel_data: pd.Series):
    imovel = Imovel(**imovel_data)
    imovel.imported = timezone.now()
    imovel.save()
    update_cep_imovel(imovel)


def update_imovel_without_error(imovel: Imovel, imovel_data: pd.Series):
    for attr, value in imovel_data.items():
        setattr(imovel, attr, value)
    imovel.imported = timezone.now()
    imovel.save()
    update_cep_imovel(imovel)


def update_imovel_with_error(imovel,
                             imovel_data: pd.Series,
                             imovel_status,
                             imovel_per_codigo,
                             imovel_per_inscricao_imobiliaria):

    alterados = 0
    dest_folder = (settings.MEDIA_ROOT + "//temp_geoitajai")
    filename = (f'{datetime.now().strftime("%Y-%m-%d")}-ERRORS.txt')
    file_path_error = os.path.join(dest_folder, filename)
    with open(file_path_error, "a", encoding="utf8") as f:
        print(f'ERROR: {datetime.now().strftime("%d-%m-%Y")}')
        f.write("=======ERROR=====\n")
        f.write(datetime.now().strftime("%d-%m-%Y, %H:%M:%S")+"\n")
        f.write(f'Imóvel com erro ({datetime.now().strftime("%d-%m-%Y")})')
        if imovel_status == "novo_codigo":
            f.write("Trocou de CÓDIGO:\n")
            f.write("\n")
        if imovel_status == "nova_inscricao":
            f.write("Trocou de INSCRIÇÃO IMOBILIÁRIA:\n")
            f.write("\n")
        f.write("\n")
        if imovel_per_codigo:
            f.write("Dados do código:\n")
            f.write(serializers.serialize("json", [imovel_per_codigo, ],))
            f.write("\n")
            f.write("\n")
            if imovel_per_inscricao_imobiliaria:
                f.write("Dados da inscrição imobiliária:\n")
                f.write(serializers.serialize("json", [imovel_per_inscricao_imobiliaria, ],))
                f.write("\n")
                f.write("\n")
            f.write("Dados no arquivo:\n")
            f.write(str(imovel_data))
            f.write("\n")
            f.write("\n")
            f.write("Tentativa de solição:\n")
            imovel_per_codigo_check_address = False
            imovel_per_inscricao_imobiliaria_check_address = False
            if imovel_data:
                if (imovel_per_codigo.logradouro == imovel_data["logradouro"] and
                    imovel_per_codigo.numero == imovel_data["numero"] and
                    imovel_per_codigo.bairro == imovel_data["bairro"] and
                        imovel_per_codigo.complemento == imovel_data["complemento"]):
                    imovel_per_codigo_check_address = True

                if (imovel_per_inscricao_imobiliaria.logradouro == imovel_data["logradouro"] and
                    imovel_per_inscricao_imobiliaria.numero == imovel_data["numero"] and
                    imovel_per_inscricao_imobiliaria.bairro == imovel_data["bairro"] and
                        imovel_per_inscricao_imobiliaria.complemento == imovel_data["complemento"]):
                    imovel_per_inscricao_imobiliaria_check_address = True

                if (imovel_per_codigo_check_address
                        and not imovel_per_inscricao_imobiliaria_check_address):
                    # conflito: prioridade imovel_per_codigo
                    f.write("Código confere com o endereço\n")
                    with transaction.atomic():
                        imovel_per_inscricao_imobiliaria.inscricao_imobiliaria = "ERROR_CHANGE_" + \
                            str(imovel_per_inscricao_imobiliaria.id) + \
                            "_IN_FAVOR_OF_"+str(imovel_per_codigo.id)
                        imovel_per_inscricao_imobiliaria.imported = timezone.now()
                        imovel_per_inscricao_imobiliaria.save()
                        f.write("Alterada a inscrição imobiliária do imóvel " +
                                str(imovel_per_inscricao_imobiliaria.id)+"\n")
                        for attr, value in imovel_data.items():
                            setattr(imovel_per_codigo, attr, value)
                        imovel_per_codigo.imported = timezone.now()
                        imovel_per_codigo.save()
                        f.write("Mantido o imóvel "+str(imovel_per_codigo.id)+"\n")
                        alterados += 2
                    f.write("Conflito resolvido\n")
                elif (imovel_per_inscricao_imobiliaria_check_address
                      and not imovel_per_codigo_check_address):
                    # conflito: prioridade imovel_per_inscricao_imobiliaria
                    f.write("Inscrição imobiliária confere com o endereço\n")
                    with transaction.atomic():
                        imovel_per_codigo.codigo = "ERROR_CHANGE_" + \
                            str(imovel_per_codigo.id)+"_IN_FAVOR_OF_" + \
                            str(imovel_per_inscricao_imobiliaria.id)
                        imovel_per_codigo.imported = timezone.now()
                        imovel_per_codigo.save()
                        f.write("Alterado o código do imóvel "+str(imovel_per_codigo.id)+"\n")
                        for attr, value in imovel_data.items():
                            setattr(imovel_per_inscricao_imobiliaria, attr, value)
                        imovel_per_inscricao_imobiliaria.imported = timezone.now()
                        imovel_per_inscricao_imobiliaria.save()
                        f.write("Mantido o imóvel "+str(imovel_per_inscricao_imobiliaria.id)+"\n")
                        alterados += 2
                    f.write("Conflito resolvido\n")
                elif (imovel_per_codigo_check_address
                      and imovel_per_inscricao_imobiliaria_check_address):
                    # conflito: ambos com prioridade, fica imovel_per_inscricao_imobiliaria
                    f.write(
                        "Código e Inscrição imobiliária confere com o endereço, ambos com prioridade\n")
                    f.write("Por definição, fica a inscrição imobiliária\n")
                    with transaction.atomic():
                        imovel_per_codigo.codigo = "ERROR_CHANGE_" + \
                            str(imovel_per_codigo.id)+"_IN_FAVOR_OF_" + \
                            str(imovel_per_inscricao_imobiliaria.id)
                        imovel_per_codigo.imported = timezone.now()
                        imovel_per_codigo.save()
                        f.write("Alterado o código do imóvel "+str(imovel_per_codigo.id)+"\n")
                        for attr, value in imovel_data.items():
                            setattr(imovel_per_inscricao_imobiliaria, attr, value)
                        imovel_per_inscricao_imobiliaria.imported = timezone.now()
                        imovel_per_inscricao_imobiliaria.save()
                        f.write("Mantido o imóvel "+str(imovel_per_inscricao_imobiliaria.id)+"\n")
                        alterados += 2
                    f.write("Conflito resolvido com ressalvas\n")
                else:
                    # conflito: sem prioridade, fica imovel_per_inscricao_imobiliaria
                    f.write("Código e Inscrição imobiliária NÃO confere com o endereço, sem prioridade\n")
                    f.write("Por definição, fica a inscrição imobiliária\n")
                    with transaction.atomic():
                        imovel_per_codigo.codigo = "ERROR_CHANGE_" + \
                            str(imovel_per_codigo.id)+"_IN_FAVOR_OF_" + \
                            str(imovel_per_inscricao_imobiliaria.id)
                        imovel_per_codigo.imported = timezone.now()
                        imovel_per_codigo.save()
                        f.write("Alterado o código do imóvel "+str(imovel_per_codigo.id)+"\n")
                        for attr, value in imovel_data.items():
                            setattr(imovel_per_inscricao_imobiliaria, attr, value)
                        imovel_per_inscricao_imobiliaria.imported = timezone.now()
                        imovel_per_inscricao_imobiliaria.save()
                        f.write("Mantido o imóvel "+str(imovel_per_inscricao_imobiliaria.id)+"\n")
                        alterados += 2
                    f.write("Conflito resolvido com ressalvas\n")
                    f.write("Nenhum dos imóveis conferem com o endereço\n")
            else:
                f.write("Problema na leitura do arquivo")
                f.write("Sem solução")
            f.write("============\n")
            f.write("\n")
            f.write("\n")
    return alterados


def update_from_dataframe(df: pd.DataFrame, log: ImovelUpdateLog):

    print("Lendo arquivo")
    log.state = 20
    log.status = "Lendo"
    log.response = "Lendo arquivo"
    log.total = 0
    log.inalterados = 0
    log.alterados = 0
    log.novos = 0
    log.falhas = 0
    log.progresso = 0
    log.save()

    total = 0
    inalterados = 0
    alterados = 0
    novos = 0
    falhas = 0
    total_rows = len(df.index)

    for index, row in df.iterrows():
        if total % 100 == 0:
            log.state = 21
            log.total = total
            log.inalterados = inalterados
            log.alterados = alterados
            log.novos = novos
            log.falhas = falhas
            if total_rows and total_rows > 1:
                log.progresso = index / total_rows
            else:
                log.progresso = 0
            log.save()
        if total % 1000 == 0:
            print(f'''Lendo arquivo compactado:
                    Total= {str(total)}
                    Inalterados= {str(inalterados)}
                    Alterados= {str(alterados)}
                    Novos= {str(novos)}
                    Falhas= {str(falhas)}''')
        total += 1

        try:

            imovel = None
            imovel_data = row

            imovel_per_inscricao_imobiliaria = (
                Imovel.objects.filter(
                    inscricao_imobiliaria=imovel_data['inscricao_imobiliaria'],
                ).first()
            )

            imovel_per_codigo = Imovel.objects.filter(
                codigo=imovel_data["codigo"]
            ).first()

            imovel_status = "error"
            if (imovel_per_codigo and imovel_per_inscricao_imobiliaria):
                if (imovel_per_codigo.id == imovel_per_inscricao_imobiliaria.id):
                    imovel_status = "ok"
            else:
                if imovel_per_codigo:
                    imovel_status = "novo_codigo"
                if imovel_per_inscricao_imobiliaria:
                    imovel_status = "nova_inscricao"

            if (
                not imovel_per_codigo
                and not imovel_per_inscricao_imobiliaria
            ):
                # create imovel
                create_imovel(imovel_data)
                novos += 1
            else:
                if (
                    imovel_status == "ok"
                    or imovel_status == "novo_codigo"
                    or imovel_status == "nova_inscricao"
                ):
                    # update imovel, without error
                    if imovel_per_codigo:
                        imovel = imovel_per_codigo
                    elif imovel_per_inscricao_imobiliaria:
                        imovel = imovel_per_inscricao_imobiliaria
                    if imovel:
                        update_imovel_without_error(
                            imovel,
                            imovel_data
                        )
                        alterados += 1
                else:
                    # update imovel with error
                    _alterados = update_imovel_with_error(imovel,
                                                          imovel_data,
                                                          imovel_status,
                                                          imovel_per_codigo,
                                                          imovel_per_inscricao_imobiliaria)
                    if _alterados and _alterados > 0:
                        alterados += _alterados
                    else:
                        print('ERROR')
                        falhas += 1

        except Exception as ex:
            falhas += 1
            logger.error(ex)

    print(
        "total: " + str(total),
        " | inalterados: " + str(inalterados),
        " | alterados: " + str(alterados),
        " | novos: " + str(novos),
        " | falhas: " + str(falhas),
    )
    print("Done!")
    log.state = 99
    log.total = total
    log.inalterados = inalterados
    log.alterados = alterados
    log.novos = novos
    log.falhas = falhas
    log.progresso = 1
    log.status = "Finalizado"
    log.response = f'Imóveis atualizados ({str(novos)} novos e {str(alterados)} alterados)'
    log.save()
    return True


class update_imovel(generics.ListCreateAPIView):
    permission_classes = [
        permissions.IsAdminUser,
    ]

    def post(self, request, *args, **kwargs):

        file = request.FILES.get("file")
        if not file:
            raise ValidationError({'file': 'Campo obrigatório.'})

        dest_folder = settings.MEDIA_ROOT + "//temp_geoitajai"
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        filename = (
            datetime.now().strftime("%Y-%m-%d")
            + "-update_imovel_running.txt"
        )
        file_update_imovel_running = os.path.join(dest_folder, filename)

        if os.path.exists(file_update_imovel_running):
            return Response(
                {
                    "detail": (
                        "Migração de dados não pode ocorrer em paralelo"
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        else:
            pass
            # FIXME
            # with open(file_update_imovel_running, "w"):
            #     pass

        print("Iniciando update")
        log = ImovelUpdateLog(
            state=0,
            status="inicio",
            response="Iniciando update",
        )
        log.save()

        update_default_imovel(log)
        df = get_dataframe_from_file(file, log)
        update_from_dataframe(df, log)

        if os.path.exists(file_update_imovel_running):
            os.remove(file_update_imovel_running)

        return Response(
            {"detail": "Update iniciado. Por favor espere o update terminar para começar outro"},
            status=status.HTTP_200_OK,
        )


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
        if logradouro.endswith("bc."):
            logradouro = "".join(logradouro.rsplit("bc.", 1)).strip()
        if logradouro.endswith("jr"):
            logradouro = "".join(logradouro.rsplit("jr", 1)).strip()
        if logradouro.startswith("trav."):
            logradouro = logradouro.replace("trav.", "", 1).strip()
        if logradouro.endswith("rod."):
            logradouro = "".join(logradouro.rsplit("rod.", 1)).strip()
        if logradouro.endswith("bc"):
            logradouro = "".join(logradouro.rsplit("bc", 1)).strip()

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
