# -*- coding: utf-8 -*-
"""
BATERIA 8: Árvore interativa (core.arvore + web/)
Gera a página, confere que os dados entraram, que não há CPF sem máscara e roda os testes de web/grp_xml.js
(XML igual ao do GRP-Tool e leitura das respostas reais) quando o Node está disponível.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

from core.arvore import gerar_html, montar_dados
from core.config import BASE_DIR


class TestArvore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = gerar_html()
        cls.dados = montar_dados()

    def test_marcadores_substituidos(self):
        self.assertNotIn("{{", self.html)

    def test_dados_embutidos_validos(self):
        bloco = re.search(r'<script id="dados" type="application/json">(.*?)</script>', self.html, re.DOTALL)
        dados = json.loads(bloco.group(1).replace("<\\/", "</"))
        self.assertEqual(set(dados["catalogos"]), {"elemento_item", "classificacao", "centros_custo", "conexoes"})
        for nome, catalogo in dados["catalogos"].items():
            self.assertRegex(catalogo["origem"], r"\d{2}/\d{2}/\d{4}|\d{4}", f"catálogo {nome} sem data")
        self.assertGreaterEqual(len(dados["casos"]), 20)
        self.assertIn("SolicOrdemPagamentoBancariaWS", dados["contrato"]["servicos"])
        self.assertEqual(len(dados["dicionario"]), 138)

    def test_ajudante_de_envio(self):
        """O ajudante só fala com o GRP, exige a chave da página e usa o curl.exe como o Assistente GRP."""
        ajudante = self.dados["ajudante"]
        self.assertIn("$chave = '__CHAVE__'", ajudante)
        self.assertIn("[System.Net.IPAddress]::Loopback", ajudante)
        self.assertIn("'www.grp.servicos.mg.gov.br', 'desenvolvimento.grp.servicos.mg.gov.br'", ajudante)
        self.assertIn("-H 'SOAPAction:'", ajudante)

    def test_logos_e_inicio(self):
        self.assertIn('class="logo-grp"', self.html)
        self.assertIn("Documentação de testes", self.html)
        self.assertIn('id="painel-inicio"', self.html)

    def test_todo_caso_tem_envio_e_resposta(self):
        for caso in self.dados["casos"]:
            self.assertTrue(caso["envio"].strip() and caso["resposta"].strip(), caso["id"])
            self.assertIn(caso["resultado"], ("aceito", "erro"))

    def test_sem_cpf_sem_mascara(self):
        for nome, valor in re.findall(r"<(cpf\w*)>([^<]*)</\1>", self.html):
            self.assertTrue(set(valor) <= set("0*") or len(re.sub(r"\D", "", valor)) != 11 or valor.startswith("*"),
                            f"{nome} com CPF aberto: {valor}")
        self.assertNotRegex(self.html, r"/v1/documento/(?!MASCARADO)[A-Za-z0-9+/=]{8,}/")

    @unittest.skipUnless(shutil.which("node"), "Node.js não instalado")
    def test_js_igual_ao_grp_tool_e_respostas_reais(self):
        r = subprocess.run(["node", os.path.join(BASE_DIR, "tests", "js", "test_grp_xml.js")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
