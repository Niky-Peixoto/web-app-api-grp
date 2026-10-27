# -*- coding: utf-8 -*-
"""
Módulo de Sanitização e Privacidade de Dados (core.sanitizer)
Responsável por anonimizar dados sensíveis (CPFs) exclusivamente durante a
geração dos artefatos públicos (arvore_interativa_grp.html e manual_api_grp_llm.md),
substituindo-os pelo valor canônico '00000000000'.
"""

import copy
import re
from typing import Any

MASKED_CPF = "00000000000"

# Regex para tags XML contendo CPFs de 11 dígitos (inclui suporte opcional a namespaces XML)
_TAG_CPF_REGEX = re.compile(
    r"(<([a-zA-Z0-9_\-]+:)?(cpfOrdenadorDespesa|cpfOperador|cpfCnpjCredor|cpfCredorBeneficiario|cpfCnpjCredorOP)>\s*)\d{11}(\s*</\2?\3>)",
    re.IGNORECASE
)

# Regex para URLs de documentos REST com CPF do emitente
_URL_CPF_REGEX = re.compile(
    r"(/documento/)\d{11}(/)",
    re.IGNORECASE
)

# URL de documento pelo gateway (apigw.mgapi.prodemge.gov.br/.../v1/documento/<CPF em Base64>/<UUID>)
_URL_GATEWAY_REGEX = re.compile(r"(/v1/documento/)[A-Za-z0-9+/=_-]{8,}(/)")


def sanitize_xml_text(text: str) -> str:
    """
    Higieniza uma string (XML, Markdown, HTML ou texto livre),
    mascarando tags de CPF de 11 dígitos e URLs de documentos.
    As fontes do repositório já usam só CPFs fictícios; esta máscara é uma segunda proteção nos artefatos gerados.
    """
    if not isinstance(text, str):
        return text

    # 1. Substitui tags XML com CPFs de 11 dígitos
    text = _TAG_CPF_REGEX.sub(rf"\g<1>{MASKED_CPF}\4", text)

    # 2. Substitui CPFs em URLs REST de documentos
    text = _URL_CPF_REGEX.sub(rf"\g<1>{MASKED_CPF}\2", text)
    text = _URL_GATEWAY_REGEX.sub(r"\g<1>MASCARADO\2", text)

    return text


def sanitize_data_structure(data: Any) -> Any:
    """
    Percorre recursivamente dicionários, listas e strings,
    aplicando a sanitização em todos os valores textuais sem mutar o objeto original.
    """
    if isinstance(data, dict):
        return {k: sanitize_data_structure(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data_structure(item) for item in data]
    elif isinstance(data, str):
        return sanitize_xml_text(data)
    else:
        return copy.deepcopy(data)
