# -*- coding: utf-8 -*-
"""
BATERIA 9: Dados pessoais nas fontes do repositório
Os outros testes conferem os artefatos gerados (HTML e manual). Este confere TODOS os arquivos versionados: base
histórica, códigos, modelos, testes e fixtures. Qualquer número de 11 dígitos com dígito verificador de CPF válido
tem de ser um CPF fictício (000000001-91, 000000002-72, ...), em texto puro ou em base64 (links do gateway). Também
não pode haver CPF com máscara parcial (ex.: ********696), que deixa ver parte do número real.
"""

import base64
import os
import re
import subprocess
import unittest

from core.config import BASE_DIR

_ONZE_DIGITOS = re.compile(r"(?<!\d)(\d{11})(?!\d)")
_BASE64 = re.compile(r"(?<![A-Za-z0-9+/])([A-Za-z0-9+/]{15,16}={0,2})(?![A-Za-z0-9+/])")


def cpf_valido(numero: str) -> bool:
    if len(numero) != 11 or len(set(numero)) == 1:
        return False
    digitos = [int(c) for c in numero]
    for n in (9, 10):
        soma = sum(digitos[i] * (n + 1 - i) for i in range(n))
        if (soma * 10) % 11 % 10 != digitos[n]:
            return False
    return True


def cpf_ficticio(numero: str) -> bool:
    return numero.startswith("000000")


def arquivos_versionados():
    try:
        saida = subprocess.run(["git", "ls-files"], cwd=BASE_DIR, capture_output=True, text=True, check=True).stdout
        return saida.split()
    except (OSError, subprocess.CalledProcessError):
        todos = []
        for raiz, pastas, arquivos in os.walk(BASE_DIR):
            pastas[:] = [p for p in pastas if p not in (".git", "__pycache__", "output")]
            todos += [os.path.relpath(os.path.join(raiz, a), BASE_DIR) for a in arquivos]
        return todos


class TestDadosPessoais(unittest.TestCase):

    def test_nenhum_cpf_real_nas_fontes(self):
        achados = []
        for caminho in arquivos_versionados():
            if caminho.endswith((".png", ".xlsx", ".pyc")):
                continue
            try:
                with open(os.path.join(BASE_DIR, caminho), encoding="utf-8") as f:
                    texto = f.read()
            except (UnicodeDecodeError, FileNotFoundError):
                continue
            # máscara parcial (ex.: ********696) deixa ver parte do CPF real
            for parcial in re.findall(r"<cpf\w*>(\*+\d+|\d+\*+)</", texto):
                achados.append(f"{caminho}: CPF com máscara parcial ({len(parcial)} caracteres)")
            for numero in _ONZE_DIGITOS.findall(texto):
                if cpf_valido(numero) and not cpf_ficticio(numero):
                    achados.append(f"{caminho}: {numero[:3]}*****{numero[-3:]}")
            for trecho in _BASE64.findall(texto):
                try:
                    decodificado = base64.b64decode(trecho + "=" * (-len(trecho) % 4)).decode("ascii")
                except (ValueError, UnicodeDecodeError):
                    continue
                if decodificado.isdigit() and cpf_valido(decodificado) and not cpf_ficticio(decodificado):
                    achados.append(f"{caminho}: CPF em base64 {decodificado[:3]}*****{decodificado[-3:]}")
        self.assertEqual(achados, [], "CPFs que não são fictícios:\n" + "\n".join(sorted(set(achados))))


if __name__ == "__main__":
    unittest.main()
