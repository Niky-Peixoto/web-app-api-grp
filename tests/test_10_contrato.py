# -*- coding: utf-8 -*-
"""
BATERIA 10: Conformidade com o contrato atual (core.contrato)
- Os XMLs que a árvore monta seguem a ordem, a obrigatoriedade e os tipos do contrato da produção.
- Todo exemplo de envio do manual e da DOCUMENTACAO, e todo caso real da árvore, aparece no formato do contrato atual
  (os mesmos dados, na ordem do contrato), que tem de passar.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

from core.config import BASE_DIR
from core.contrato import atualizar, contrato

DOCUMENTOS = ["manual_api_grp_llm.md", os.path.join("docs", "DOCUMENTACAO_API_GRP_TESTES_PRIORIDADE_ALTA.md")]
_BLOCO = re.compile(r"```xml\n(.*?)```", re.DOTALL)


def envios(texto):
    """(posição, xml) dos blocos XML que são envios de uma operação do contrato."""
    c = contrato()
    for m in _BLOCO.finditer(texto):
        xml = m.group(1)
        op = re.search(r"Body>\s*<(?:[\w.-]+:)?(\w+)", xml)
        if op and op.group(1) in c.tipos and not op.group(1).endswith("Response"):
            yield m.start(), m.end(), xml


class TestContrato(unittest.TestCase):

    def test_validador_acusa_ordem_obrigatorio_e_tipo(self):
        xml = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:grp="urn:x">
<soapenv:Body><grp:gerarSolicitacaoCancelamentoOrdemPagamentoBancaria><x/></grp:gerarSolicitacaoCancelamentoOrdemPagamentoBancaria></soapenv:Body></soapenv:Envelope>"""
        self.assertTrue(contrato().validar(xml))
        with open(os.path.join(BASE_DIR, "tests", "fixtures", "grp_tool", "07_op_conta_unica.xml"), encoding="utf-8") as f:
            op = f.read()
        self.assertEqual(contrato().validar(op), [])
        fora = op.replace("<justificativa>", "<finalidadePagamento>X</finalidadePagamento>\n        <justificativa>", 1)
        self.assertTrue(any("finalidadePagamento" in p and "ordem" in p for p in contrato().validar(fora)))
        atualizado, mudancas = atualizar(fora)
        self.assertEqual(contrato().validar(atualizado), [])
        self.assertTrue(any("finalidadePagamento" in m for m in mudancas))
        self.assertEqual(atualizado.count("\n"), fora.count("\n"))  # só muda a posição da linha
        sem_valor = re.sub(r"<valorLiquidoPagamento>[^<]*</valorLiquidoPagamento>", "", op)
        self.assertTrue(any("valorLiquidoPagamento" in p and "obrigatório" in p for p in contrato().validar(sem_valor)))
        texto = op.replace("<codigoSistemaOrigem>51<", "<codigoSistemaOrigem>cinquenta<", 1)
        self.assertTrue(any("xs:int" in p for p in contrato().validar(texto)))

    def test_exemplos_dos_documentos_seguem_o_contrato(self):
        """Todo exemplo de envio do manual e da DOCUMENTACAO está no formato do contrato atual."""
        for nome in DOCUMENTOS:
            with open(os.path.join(BASE_DIR, nome), encoding="utf-8") as f:
                texto = f.read()
            blocos = list(envios(texto))
            self.assertGreater(len(blocos), 5, nome)
            for _, _, xml in blocos:
                self.assertEqual(contrato().validar(xml), [], f"{nome}: exemplo de envio fora do contrato atual")

    def test_casos_reais_mostram_o_formato_atual(self):
        """Os casos reais da árvore mostram o envio no formato atual; o original fica só para consulta."""
        from core.arvore import carregar_casos
        ajustados = 0
        for caso in carregar_casos():
            self.assertEqual(contrato().validar(caso["envio"]), [], caso["id"])
            if caso["ajustes"]:
                ajustados += 1
                self.assertTrue(caso["envio_original"], caso["id"])
                # mesmos valores: o atualizado só tem linhas que já estavam no original
                self.assertTrue(set(caso["envio"].splitlines()) <= set(caso["envio_original"].splitlines()), caso["id"])
        self.assertGreater(ajustados, 0)

    def test_dicionario_tira_o_tipo_do_contrato(self):
        """O tipo vem só do contrato (coluna calculada); o texto de regra não afirma tipos xs:."""
        from core.registry import default_registry
        from core.contrato import resumo_tag
        for t in default_registry.get_all_tags():
            self.assertNotIn("xs:", t["regra"], t["name"])
            self.assertTrue(resumo_tag(t["name"]), t["name"])
        self.assertRegex(resumo_tag("codigoSistemaOrigem"), r"Envio — [^|]*\bOP\b[^:|]*: xs:int, obrigatório")
        self.assertIn("xs:long", resumo_tag("codigoOrgaoExecutor"))
        self.assertIn("xs:dateTime", resumo_tag("dataProgramadaPagamento"))
        self.assertIn("Não está no contrato atual", resumo_tag("guiaPrevidenciaSocialGps"))

    def test_documentacao_lista_campos_do_contrato_atual(self):
        """Apêndice 20 (tipo e obrigatoriedade) e campos condicionais da OP (9.5) iguais ao contrato atual."""
        c = contrato()
        with open(os.path.join(BASE_DIR, DOCUMENTOS[1]), encoding="utf-8") as f:
            doc = f.read()
        servicos = {"Empenho": "SolicitacaoEmpenhoWS", "OLP": "SolicitacaoOlpWS", "OP Bancária": "SolicOrdemPagamentoBancariaWS"}
        apendice = doc[doc.index("## 20. Apêndice de campos"):doc.index("## 21.")]
        linhas = 0
        for linha in apendice.splitlines():
            cols = [x.strip() for x in linha.strip().strip("|").split("|")]
            if len(cols) < 6 or cols[0] not in servicos:
                continue
            linhas += 1
            tag, tipo, obrigatorio = cols[2].strip("`"), cols[4].strip("`"), cols[5]
            reais = [(campo[1], campo[2]) for nome, (servico, campos) in c.tipos.items()
                     if servico == servicos[cols[0]] and "Response" not in nome for campo in campos if campo[0] == tag]
            self.assertTrue(reais, f"apêndice 20: {tag} não está no contrato atual")
            if tipo != "Complexo":
                self.assertIn(tipo, {r[0] for r in reais}, f"apêndice 20: tipo de {tag}")
            self.assertEqual(obrigatorio == "Sim", any(r[1] != "0" for r in reais), f"apêndice 20: obrigatoriedade de {tag}")
        self.assertGreater(linhas, 50)
        secao = doc[doc.index("### 9.5. Campos condicionais"):doc.index("Fora do contrato atual (não usar")]
        campos_op = {campo[0] for nome, (servico, campos) in c.tipos.items()
                     if servico == "SolicOrdemPagamentoBancariaWS" for campo in campos}
        for nome in re.findall(r"^- `(\w+)`", secao, re.MULTILINE):
            self.assertIn(nome, campos_op, f"9.5: {nome} não está no contrato atual")

    @unittest.skipUnless(shutil.which("node"), "Node.js não instalado")
    def test_xml_da_arvore_segue_o_contrato(self):
        script = """
const G = require(process.argv[1]);
const casos = require(process.argv[2]);
const saida = casos.map((c) => [c.nome, G[c.funcao](c.dados)]);
saida.push(["reforco", G.xmlReforco({ numeroRequisicao: "2026101910001", ano: "2026", sistema: "51", orgao: "10190",
  uo: "10191", ua: "1019080124", cpfOrdenador: "00000000191", cpfOperador: "00000000272", empenho: "41998",
  valor: 5000, justificativa: "REFORCO" })]);
console.log(JSON.stringify(saida));
"""
        r = subprocess.run(["node", "-e", script, os.path.join(BASE_DIR, "web", "grp_xml.js"),
                            os.path.join(BASE_DIR, "tests", "fixtures", "grp_tool", "casos.json")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        for nome, xml in json.loads(r.stdout):
            self.assertEqual(contrato().validar(xml), [], f"árvore, {nome}")


if __name__ == "__main__":
    unittest.main()
