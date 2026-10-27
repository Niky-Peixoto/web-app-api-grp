# -*- coding: utf-8 -*-
"""
BATERIA 7: Sincronia entre o manual e a DOCUMENTACAO
Os dois documentos não podem se contradizer: os trechos comuns vêm de core.conteudo_compartilhado e têm de estar
iguais nos dois arquivos versionados. Se este teste falhar, rode `python cli.py build` e confira o diff.
"""

import os
import re
import unittest

from core.config import OUTPUT_MARKDOWN_PATH, VERSAO_DOCUMENTACAO
from core import conteudo_compartilhado as cc
from core.markdown_generator import generate_markdown_manual
from core.scenarios import default_scenarios
from core.sanitizer import sanitize_xml_text


class TestSincroniaDocumentacao(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(cc.DOCUMENTACAO_PATH, encoding="utf-8") as f:
            cls.doc = f.read()
        with open(OUTPUT_MARKDOWN_PATH, encoding="utf-8") as f:
            cls.manual = f.read()
        cls.blocos = cc.blocos(default_scenarios.get_all_scenarios())

    def test_todos_os_blocos_presentes_na_documentacao(self):
        """Cada bloco compartilhado aparece uma vez na DOCUMENTACAO."""
        for nome in self.blocos:
            self.assertEqual(self.doc.count(f"<!-- BLOCO:{nome}:INICIO -->"), 1, nome)
            self.assertEqual(self.doc.count(f"<!-- BLOCO:{nome}:FIM -->"), 1, nome)

    def test_documentacao_atualizada(self):
        """A DOCUMENTACAO versionada já tem o conteúdo atual de cada bloco."""
        self.assertEqual(cc.aplicar_blocos(self.doc, self.blocos), self.doc)

    def test_manual_atualizado(self):
        """O manual versionado é o que o gerador produz hoje."""
        self.assertEqual(generate_markdown_manual(), self.manual)

    def test_blocos_iguais_nos_dois_documentos(self):
        """O texto de cada bloco aparece igual no manual e na DOCUMENTACAO."""
        for nome, texto in self.blocos.items():
            texto = sanitize_xml_text(texto)
            self.assertIn(texto, self.manual, nome)
            self.assertIn(texto, self.doc, nome)

    def test_mesma_versao(self):
        self.assertIn(f"Versão {VERSAO_DOCUMENTACAO}", self.manual)
        self.assertIn(f"Versão {VERSAO_DOCUMENTACAO}", self.doc)

    def test_sem_cpf_sem_mascara(self):
        """Nenhum CPF de 11 dígitos fora das máscaras nas tags de pessoa."""
        for texto in (self.doc, self.manual):
            achados = re.findall(r"<(cpf\w*)>(\d{11})</\1>", texto)
            self.assertTrue(all(v == "00000000000" for _, v in achados), achados[:3])


if __name__ == "__main__":
    unittest.main()
