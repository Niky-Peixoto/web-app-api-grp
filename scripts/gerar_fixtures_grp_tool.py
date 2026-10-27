# -*- coding: utf-8 -*-
"""
Gera tests/fixtures/grp_tool/: XMLs montados pelo próprio GRP-Tool (grp_tool/xml_builder.py e teste_servicos.py)
para um conjunto de casos, junto com a entrada equivalente para web/grp_xml.js. tests/js/test_grp_xml.js exige que a
árvore produza os mesmos bytes. Rode de novo quando o GRP-Tool mudar um envelope:

    python scripts/gerar_fixtures_grp_tool.py --grp-tool ../grp-tool
"""

import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(BASE_DIR, "tests", "fixtures", "grp_tool")

EXEC = dict(ano="2026", orgao="10190", uo="10191", ua="1019080124", sistema="51",
            cpfOrdenador="00000000191", cpfOperador="00000000272")
DOT = dict(funcao="04", subfuncao="129", programa="045", projetoAtividade="4081", subprojeto="0001", categoria="3",
           grupo="3", modalidade="90", elemento="031", item="005", iag="00", grupoFonte="11", fonte="500010", ipu="01")
CHAVES_PY = dict(funcao="funcao", subfuncao="subfuncao", programa="programa", projetoAtividade="projeto_atividade",
                 subprojeto="subprojeto_subatividade", categoria="categoria_economica", grupo="grupo_despesa",
                 modalidade="modalidade_despesa", elemento="elemento_despesa", item="item", iag="iag",
                 grupoFonte="grupo_fonte", fonte="fonte_recurso", ipu="ipu")
ADICIONAIS_PY = {
    "codigoUfg": "codigo_ufg", "numeroInstrumentoJuridicoEntrada": "numero_instrumento_juridico_entrada",
    "codigoTipoInstrumentoJuridicaEntrada": "codigo_tipo_instrumento_juridico_entrada",
    "anoInstrumentoJuridicoEntrada": "ano_instrumento_juridico_entrada",
    "numeroInstrumentoJuridicoSaida": "numero_instrumento_juridico_saida",
    "codigoTipoInstrumentoJuridicoSaida": "codigo_tipo_instrumento_juridico_saida",
    "anoInstrumentoJuridicoSaida": "ano_instrumento_juridico_saida", "numeroObra": "numero_obra",
    "numeroProcessoCompra": "numero_processo_compra", "codigoProcedimentoContratacao": "codigo_procedimento_contratacao",
    "nomeProcedimentoContratacao": "nome_procedimento_contratacao", "numeroEspecificacaoEmpenho": "numero_especificacao_empenho",
}


def c(valor):
    """"1.00" -> 100 (centavos, como a árvore recebe)."""
    return round(float(valor) * 100)


def casos(xb, ts):
    lista = []

    def caso(nome, funcao, dados, xml):
        lista.append({"nome": nome, "funcao": funcao, "dados": dados})
        with open(os.path.join(SAIDA, nome + ".xml"), "w", encoding="utf-8", newline="\n") as f:
            f.write(xml)

    caso("01_processo", "xmlProcesso", dict(EXEC),
         xb.montar_xml_gerar_processo(ano_exercicio="2026", codigo_orgao="10190", codigo_unidade_administrativa="1019080124",
                                      codigo_unidade_orcamentaria="10191", codigo_sistema_solicitante="51"))

    def empenho(nome, adicionais, justificativa, tipo="ORDINARIO"):
        dados = dict(EXEC, numeroRequisicao="2026101910001", justificativa=justificativa, tipoEmpenho=tipo,
                     numeroProcesso="101901800000431202611", credor="12345678000190", classificacaoCredor="FORNECEDOR",
                     dotacao=DOT, valor="1500.00", centroCusto="0243", adicionais=adicionais)
        caso(nome, "xmlEmpenho", dados, xb.montar_xml_solicitar_empenho(
            numero_requisicao="2026101910001", codigo_sistema_origem="51", ano_exercicio_financeiro="2026",
            codigo_unidade_orcamentaria="10191", codigo_orgao_executor="10190", codigo_unidade_administrativa="1019080124",
            cpf_ordenador_despesa="00000000191", justificativa=justificativa, cpf_operador="00000000272",
            numero_processo_geral="101901800000431202611", cpf_cnpj_credor="12345678000190", classificacao_credor="FORNECEDOR",
            **{f"codigo_{CHAVES_PY[k]}" if not CHAVES_PY[k].startswith("item") else "codigo_item": v for k, v in DOT.items()},
            valor_empenho="1500.00", codigo_cc="0243", tipo_empenho_comum=tipo,
            campos_adicionais={ADICIONAIS_PY[k]: v for k, v in adicionais.items()}))

    empenho("02_empenho_simples", {}, "EMPENHO DE TESTE")
    empenho("03_empenho_adicionais", {"codigoUfg": "20121", "numeroProcessoCompra": "12553020001692023",
                                      "codigoProcedimentoContratacao": "133", "nomeProcedimentoContratacao": "Bens & serviços",
                                      "numeroEspecificacaoEmpenho": "6532387"}, "AQUISICAO <URGENTE> & ESTIMATIVA", "ESTIMATIVO")

    def olp(nome, bruto, inss, issqn, credor):
        retencoes_py, retencoes_js = [], []
        liquido = round(float(bruto) - float(inss) - float(issqn), 2)
        if float(inss) > 0:
            tipo = "4" if len(credor) == 11 else "14"
            retencoes_py.append({"tipo": tipo, "valor": inss, "cnpj_arrecadador": "29979036000140"})
            retencoes_js.append({"tipo": tipo, "valor": c(inss), "credor": "29979036000140"})
        if float(issqn) > 0:
            retencoes_py.append({"tipo": "13", "valor": issqn, "cnpj_arrecadador": "18715383000140"})
            retencoes_js.append({"tipo": "13", "valor": c(issqn), "credor": "18715383000140"})
        dados = dict(EXEC, numeroRequisicao="2026101910002", mesCompetencia="10", anoCompetencia="2026",
                     justificativa="LIQUIDACAO DE TESTE", empenho="57511", credor=credor,
                     classificacaoCredor="BENEFICIÁRIOS DIVERSOS", bruto=c(bruto), liquido=c(f"{liquido:.2f}"),
                     retencoes=retencoes_js)
        caso(nome, "xmlOlp", dados, xb.montar_xml_solicitar_olp(
            numero_requisicao="2026101910002", codigo_sistema_origem="51", ano_exercicio_financeiro="2026",
            codigo_unidade_orcamentaria="10191", codigo_orgao_executor="10190", codigo_unidade_administrativa="1019080124",
            cpf_ordenador_despesa="00000000191", cpf_operador="00000000272", mes_competencia_despesa="10",
            ano_competencia_despesa="2026", justificativa="LIQUIDACAO DE TESTE", numero_documento_empenho="57511",
            cpf_credor_beneficiario=credor, tipo_classificacao_credor="BENEFICIÁRIOS DIVERSOS", valor_bruto_olp=bruto,
            valor_liquido=f"{liquido:.2f}", retencoes=retencoes_py or None))

    olp("04_olp_sem_retencao", "1.00", "0", "0", "00000000353")
    olp("05_olp_inss_issqn_cpf", "1.00", "0.11", "0.05", "00000000353")
    olp("06_olp_inss_cnpj", "100.00", "11.00", "0", "12345678000190")

    def op(nome, a_pagar, irrf=None, debitar=None, creditar=None, forma="001", barras="", finalidade=""):
        debitar = debitar or {"tipo": "1"}
        creditar = creditar or {"tipo": "1", "banco": "001", "agencia": "9012", "dvAgencia": "6", "conta": "90006", "dvConta": "3"}
        liquido = round(float(a_pagar) - float(irrf or 0), 2)
        retencao_item = None
        if irrf:
            retencao_item = {"tipo": "10", "valor": irrf, "codigo_receita": "090140", "cpf_cnpj_credor": "18715615000160"}
        especifica = debitar.get("tipo") == "2"
        dv_conta = creditar.get("dvConta", "") or ("0" if creditar.get("conta") else "")
        xml = xb.montar_xml_op_bancaria(
            numero_requisicao="2026101910003", codigo_sistema_origem="51", numero_arquivo="1", ano_exercicio_financeiro="2026",
            codigo_unidade_orcamentaria="10191", codigo_orgao_executor="10190", codigo_unidade_administrativa="1019080124",
            cpf_ordenador_despesa="00000000191", cpf_operador="00000000272", cpf_cnpj_credor="00000000353",
            classificacao_credor="BENEFICIÁRIOS DIVERSOS", tipo_conta_a_debitar=debitar["tipo"],
            codigo_banco_a_debitar=debitar.get("banco", "") if especifica else "",
            codigo_agencia_a_debitar=debitar.get("agencia", "") if especifica else "",
            dv_agencia_a_debitar=debitar.get("dvAgencia", "") if especifica else "",
            codigo_conta_a_debitar=debitar.get("conta", "") if especifica else "",
            dv_conta_a_debitar=debitar.get("dvConta", "") if especifica else "",
            codigo_forma_pagamento=forma, codigo_barras=barras, finalidade_pagamento=finalidade,
            tipo_conta_a_creditar=creditar["tipo"], codigo_banco_a_creditar=creditar.get("banco", ""),
            codigo_agencia_a_creditar=creditar.get("agencia", ""), dv_agencia_a_creditar=creditar.get("dvAgencia", ""),
            codigo_conta_a_creditar=creditar.get("conta", ""), dv_conta_a_creditar=dv_conta,
            valor_total_a_pagar_da_op=a_pagar, valor_liquido_pagamento=f"{liquido:.2f}",
            data_programada_pagamento="2026-10-26T00:00:00", justificativa="PAGAMENTO DE TESTE - PARCELA 1",
            ano_numero_da_olp_e_empenho="2026/57837", valor_a_pagar_item=a_pagar, valor_total_a_pagar_item=a_pagar,
            valor_liquido_item=f"{liquido:.2f}", retencao_item=retencao_item)
        dados = dict(EXEC, numeroRequisicao="2026101910003", credor="00000000353", classificacaoCredor="BENEFICIÁRIOS DIVERSOS",
                     debitar=debitar, creditar=creditar, forma=forma, codigoBarras=barras, finalidade=finalidade,
                     aPagar=c(a_pagar), irrf=c(irrf) if irrf else 0, dataProgramada="2026-10-26T00:00:00",
                     justificativa="PAGAMENTO DE TESTE - PARCELA 1", olp="2026/57837")
        caso(nome, "xmlOp", dados, xml)

    op("07_op_conta_unica", "0.84")
    op("08_op_conta_especifica", "1.37", debitar={"tipo": "2", "banco": "001", "agencia": "1615", "dvAgencia": "2",
                                                 "conta": "22768", "dvConta": "4"}, finalidade="Não se aplica")
    op("09_op_codigo_barras", "1.00", forma="002", finalidade="Não se aplica",
       barras="00190000090000000000000000000018816100000000100", creditar={"tipo": "1"})
    op("10_op_irrf", "2.00", irrf="1.00", finalidade="Não se aplica",
       creditar={"tipo": "1", "banco": "756", "agencia": "1", "dvAgencia": "", "conta": "90023", "dvConta": "3"})
    op("11_op_poupanca_sem_dv", "5.00", creditar={"tipo": "2", "banco": "104", "agencia": "9014", "dvAgencia": "0",
                                                  "conta": "907", "dvConta": ""})

    caso("12_cancelamento", "xmlCancelamento", dict(EXEC, numeroRequisicao="2026101910004", documentoOp="116865",
                                                     justificativa="CANCELAMENTO VIA API GRP - OP 116865"),
         xb.montar_xml_cancelamento_op(numero_requisicao="2026101910004", exercicio_financeiro="2026",
                                       codigo_sistema_origem="51", numero_documento_op="116865",
                                       cpf_ordenador_despesa="00000000191", cpf_operador="00000000272",
                                       justificativa="CANCELAMENTO VIA API GRP - OP 116865"))

    comuns = [("codigoUnidadeOrcamentaria", "10191"), ("codigoOrgaoExecutor", "10190"),
              ("codigoUnidadeAdministrativa", "1019080124"), ("cpfOrdenadorDespesa", "00000000191"),
              ("cpfOperador", "00000000272")]
    caso("13_anulacao_olp", "xmlAnulacaoOlp", dict(EXEC, numeroRequisicao="2026101910005", numeroOlp="22606",
                                                    liquido=50000, total=50000, justificativa="ANULACAO VIA API GRP - OLP 22606"),
         ts._envelope(ts.NS_EMPENHO, "solicitarAnulacaoValoresNaOLP", "solicitarAnulacaoValoresNaOLP", [
             ("numeroRequisicao", "2026101910005"), ("identificadorProcessoExecucao", "EMPOLP2.2"),
             ("codigoSistemaOrigem", "51"), ("anoExercicioFinanceiro", "2026"), ("numeroOlp", "22606"), *comuns,
             ("valorLiquidoAnulado", "500.00"), ("valorTotalAnulado", "500.00"),
             ("justificativa", "ANULACAO VIA API GRP - OLP 22606")]))
    caso("14_anulacao_empenho", "xmlAnulacaoEmpenho", dict(EXEC, numeroRequisicao="2026101910006", empenho="22575",
                                                            valor=50000, justificativa="ANULACAO VIA API GRP - EMPENHO 22575"),
         ts._envelope(ts.NS_EMPENHO, "gerarSolicitacaoAnulacaoSaldoEmpenho", "gerarSolicitacaoAnulacaoSaldoEmpenho", [
             ("numeroRequisicao", "2026101910006"), ("identificadorProcessoExecucao", "EMPOLP1.3"),
             ("codigoSistemaOrigem", "51"), ("anoExercicioFinanceiro", "2026"), ("numeroEmpenho", "22575"), *comuns,
             ("valorAnulacaoEmpenho", "500.00"), ("justificativa", "ANULACAO VIA API GRP - EMPENHO 22575")]))
    return lista


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grp-tool", required=True)
    args = ap.parse_args()
    sys.path.insert(0, os.path.abspath(args.grp_tool))
    os.chdir(os.path.abspath(args.grp_tool))
    from grp_tool import xml_builder
    import teste_servicos
    os.makedirs(SAIDA, exist_ok=True)
    lista = casos(xml_builder, teste_servicos)
    with open(os.path.join(SAIDA, "casos.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(lista, f, ensure_ascii=False, indent=1)
    print(f"{len(lista)} casos em {os.path.relpath(SAIDA, BASE_DIR)}")


if __name__ == "__main__":
    main()
