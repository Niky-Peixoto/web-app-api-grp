#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Unificado de Controle e Gestão da Codebase GRP (cli.py)
Esteira de automação para testes, auditoria de schemas, compilação e execução SOAP da API GRP.

Comandos disponíveis:
  python cli.py build           Compila a aplicação autônoma arvore_interativa_grp.html
  python cli.py validate        Executa auditoria cruzada de tags XML vs Dicionário
  python cli.py test-all        Executa a suíte unificada de testes automatizados
  python cli.py run             Executa cenários, etapas ou cadeias com suporte a zero-code overrides e persistência
  python cli.py list-scenarios  Lista todos os 64 cenários combinatórios da esteira
  python cli.py list-tags       Lista todas as 138 tags cadastradas no dicionário
"""

import argparse
import sys
import unittest

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from core.config import OUTPUT_HTML_PATH, OUTPUT_MARKDOWN_PATH, EXCEL_DICT_PATH
from core.registry import default_registry
from core.scenarios import default_scenarios
from core.renderer import default_renderer
from core.runner import default_runner
from core.arvore import gerar_arvore
from core.markdown_generator import save_markdown_manual


def cmd_build(args):
    """Compila o arquivo HTML autônomo e o manual Markdown para LLMs."""
    print("=" * 80)
    print("🔨 COMPILANDO APLICAÇÃO WEB & MANUAL MARKDOWN PARA LLMs: GRP")
    print("=" * 80)
    out_md = save_markdown_manual(OUTPUT_MARKDOWN_PATH)
    out_html = gerar_arvore(OUTPUT_HTML_PATH)
    print(f"\n✨ Compilação concluída com sucesso!")
    print(f"👉 Portal Web Interativo: {out_html}")
    print(f"👉 Manual Markdown para LLMs: {out_md}\n")


def cmd_build_manual(args):
    """Compila apenas o manual em Markdown para LLMs."""
    print("=" * 80)
    print("🤖 GERANDO MANUAL CONSOLIDADO EM MARKDOWN PARA LLMs")
    print("=" * 80)
    out_md = save_markdown_manual(OUTPUT_MARKDOWN_PATH)
    print(f"\n✨ Manual gerado com sucesso em:\n👉 {out_md}\n")


def cmd_validate(args):
    """Executa auditoria cruzada entre templates e dicionário."""
    print("=" * 80)
    print("🔍 AUDITORIA CRUZADA DE SCHEMAS E DICIONÁRIO DE TAGS XML")
    print(f"📄 Lastro Oficial: {EXCEL_DICT_PATH}")
    print("=" * 80)

    tags = default_registry.load(force_reload=True)
    print(f"✅ Total de tags cadastradas na planilha: {len(tags)}")

    params_mock = {
        "num_requisicao": "1019080124202600000000000000000000000001",
        "ano_exercicio": "2026", "orgao_executor": "10190", "uo": "10191", "ua": "1019080124",
        "cpf_ordenador": "00000000191", "cpf_operador": "00000000191", "justificativa": "Validacao",
        "credor_cpf_cnpj": "00000000191", "credor_classificacao": "BENEFICIÁRIOS DIVERSOS",
        "valor": "100.00", "valor_liquido": "89.00", "valor_retido": "11.00",
        "ha_retencao": True, "retencoes_list": [{"codigo_tipo_retencao": "14", "valor_retencao": "11.00"}],
        "exige_regionalizacao": True, "tipo_conta_a_debitar": 2, "op_cod_banco_deb": "001",
        "op_ag_deb": "1615", "op_dv_ag_deb": "2", "op_conta_deb": "90004", "op_dv_conta_deb": "6",
        "tipo_conta_a_creditar": 1, "op_cod_banco_cred": "001", "op_ag_cred": "1615",
        "op_dv_ag_cred": "2", "op_conta_cred": "90004", "op_dv_conta_cred": "0"
    }

    todos_xmls = (
        default_renderer.render_stage1(params_mock) + "\n" +
        default_renderer.render_stage2(params_mock, "2026-10190-00001") + "\n" +
        default_renderer.render_stage3(params_mock, "22575") + "\n" +
        default_renderer.render_stage4(params_mock, "30001") + "\n" +
        default_renderer.render_reforco(params_mock) + "\n" +
        default_renderer.render_anulacao(params_mock)
    )

    resultado = default_registry.audit_xml(todos_xmls)
    print(f"✅ Tags reconhecidas nos templates: {len(resultado['reconhecidas'])}")

    if resultado["nao_registradas"]:
        print(f"❌ ATENÇÃO: {len(resultado['nao_registradas'])} tags não constam no dicionário:")
        for t in resultado["nao_registradas"]:
            print(f"   • <{t}>")
        sys.exit(1)
    else:
        print("🎉 100% de conformidade: Todas as tags utilizadas nos templates constam no Dicionário Oficial!")


def cmd_test_all(args):
    """Executa a suíte unificada de testes."""
    print("=" * 80)
    print("🧪 EXECUTANDO SUÍTE UNIFICADA DE TESTES AUTOMATIZADOS (LOOP ENGINEERING)")
    print("=" * 80)

    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n" + "=" * 80)
        print("🎉 SUCESSO TOTAL: TODAS AS BATERIAS DE TESTES PASSARAM COM 100% DE CONFORMIDADE!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print(f"❌ FALHA: {len(result.failures)} falhas e {len(result.errors)} erros detectados.")
        print("=" * 80)
        sys.exit(1)


def cmd_run(args):
    """
    Executa cenários, etapas individuais ou cadeias completas com suporte a overrides dinâmicos.
    """
    print("=" * 80)
    modo_str = "🌐 MODO LIVE (SOAP REAL NO GRP PRODEMGE)" if args.live else "📦 MODO SIMULAÇÃO / VALIDAÇÃO OFFLINE"
    print(f"🚀 UNIVERSAL TEST RUNNER: {modo_str}")
    print("=" * 80)

    # 1. Coleta e consolidação de overrides
    overrides = {}

    # Overrides passados via --set chave=valor
    if args.set_params:
        for item in args.set_params:
            if "=" in item:
                k, v = item.split("=", 1)
                overrides[k.strip()] = v.strip()

    # Flags dedicadas de conveniência
    if args.valor is not None:
        overrides["valor"] = args.valor
    if args.credor is not None:
        overrides["credor_cpf_cnpj"] = args.credor
    if args.retencao_inss is not None:
        overrides["retencao_inss"] = args.retencao_inss
    if args.retencao_issqn is not None:
        overrides["retencao_issqn"] = args.retencao_issqn
    if args.justificativa is not None:
        overrides["justificativa"] = args.justificativa
    if args.processo is not None:
        overrides["numero_processo"] = args.processo
    if args.empenho is not None:
        overrides["numero_empenho"] = args.empenho
    if args.olp is not None:
        overrides["numero_olp"] = args.olp
    if args.cpf_ordenador is not None:
        overrides["cpf_ordenador"] = args.cpf_ordenador
    if args.cpf_operador is not None:
        overrides["cpf_operador"] = args.cpf_operador
    if args.banco_cred is not None:
        overrides["op_cod_banco_cred"] = args.banco_cred
    if args.ag_cred is not None:
        overrides["op_ag_cred"] = args.ag_cred
    if args.dv_ag_cred is not None:
        overrides["op_dv_ag_cred"] = args.dv_ag_cred
    if args.conta_cred is not None:
        overrides["op_conta_cred"] = args.conta_cred
    if args.dv_conta_cred is not None:
        overrides["op_dv_conta_cred"] = args.dv_conta_cred
    if args.tipo_conta_deb is not None:
        overrides["tipo_conta_a_debitar"] = args.tipo_conta_deb
    if args.tipo_conta_cred is not None:
        overrides["tipo_conta_a_creditar"] = args.tipo_conta_cred

    # 2. Roteamento de Execução
    if args.stage:
        # Execução de Etapa Avulsa
        print(f"⚙️ Executando Etapa Avulsa: '{args.stage}'")
        res = default_runner.run_stage(args.stage, params=overrides, live=args.live)
        print(f"\n• Status: {'✅ Sucesso' if res.get('sucesso') else '❌ Falha'}")
        if res.get("documento"):
            print(f"• Documento Gerado: {res.get('documento')}")
        if res.get("numero_solicitacao"):
            print(f"• Número Solicitação: {res.get('numero_solicitacao')}")

        if res.get("request_xml"):
            print("\n" + "=" * 80)
            print("📤 XML DE ENVIO (REQUEST SOAP):")
            print("=" * 80)
            print(res["request_xml"])

        if res.get("response_xml"):
            print("\n" + "=" * 80)
            print("📥 XML DE RETORNO (RESPONSE GRP):")
            print("=" * 80)
            print(res["response_xml"])

        if not res.get("sucesso") and res.get("erro"):
            print(f"\n❌ Erro: {res['erro']}")

    elif args.chain:
        # Execução de Cadeia Personalizada
        stages = [s.strip() for s in args.chain.split(",") if s.strip()]
        print(f"⚙️ Executando Cadeia Customizada: {stages}")
        res = default_runner.run_chain(stages=stages, params=overrides, live=args.live)
        print(f"\n• Status Geral: {'✅ Sucesso' if res.get('sucesso') else '❌ Falha'}")
        print(f"• Documentos: {res.get('documentos')}")
        if not res.get("sucesso"):
            print(f"• Etapa com Falha: {res.get('etapa_falha')}")
            print(f"• Erro: {res.get('erro')}")

    else:
        # Execução de Cenário Combinatório Completo (Padrão: Chamada-01 ou informado via --scenario)
        s_id = args.scenario or "Chamada-01"
        print(f"⚙️ Executando Cenário: {s_id}")
        res = default_runner.run_scenario(s_id, overrides=overrides, live=args.live)

        if args.live:
            print(f"\n• Status Geral: {'✅ Sucesso' if res.get('sucesso') else '❌ Falha'}")
            docs = res.get("documentos", {})
            print(f"1️⃣ Processo GRP: {docs.get('processo')}")
            print(f"2️⃣ Empenho: {docs.get('empenho')}")
            print(f"3️⃣ OLP (Liquidação): {docs.get('olp')}")
            print(f"4️⃣ OP Bancária: {docs.get('op')} (Solicitação: {docs.get('solicitacao_op')})")
        else:
            print(f"\n• Status: ✅ Validação de Schemas e XMLs Concluída")
            print(f"• Valores Fiscobancários:")
            params = res.get("parametros", {})
            print(f"   - Valor Bruto: R$ {params.get('valor', '1.00')}")
            print(f"   - Total Retenções: R$ {params.get('valor_retido', '0.00')}")
            print(f"   - Valor Líquido: R$ {params.get('valor_liquido', '1.00')}")

    print("\n" + "-" * 80)
    print(f"💾 Registro e XMLs salvos automaticamente em:\n👉 {res.get('saved_log_path')}")
    print("-" * 80)


def cmd_list_scenarios(args):
    """Lista todos os 64 cenários da esteira."""
    summary = default_scenarios.list_summary()
    print(f"\n{'ID':<12} | {'CLIENTE':<6} | {'REGIONALIZAÇÃO':<20} | {'CONTA DÉBITO':<28} | {'RETENÇÃO':<15} | {'GRUPO'}")
    print("-" * 105)
    for s in summary:
        print(f"{s['id']:<12} | {s['cliente']:<6} | {s['regionalizacao']:<20} | {s['conta_debito']:<28} | {s['retencao']:<15} | Grupo-{s['grupo_mae']}")
    print(f"\nTotal: {len(summary)} cenários homologados.")


def cmd_list_tags(args):
    """Lista todas as 138 tags do dicionário."""
    tags = default_registry.load()
    print(f"\n{'#':<4} | {'TAG XML':<35} | {'CONCEITO ORÇAMENTÁRIO (RESUMO)'}")
    print("-" * 100)
    for idx, t in enumerate(tags):
        conceito_resumo = (t['conceito'][:55] + '...') if len(t['conceito']) > 55 else t['conceito']
        print(f"{idx+1:<4} | {t['name']:<35} | {conceito_resumo}")
    print(f"\nTotal: {len(tags)} tags especializadas cadastradas no lastro oficial ({EXCEL_DICT_PATH}).")


def main():
    parser = argparse.ArgumentParser(
        description="CLI Unificado de Controle e Gestão da Codebase GRP",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Comando a ser executado")

    # build
    p_build = subparsers.add_parser("build", help="Compilar a aplicação arvore_interativa_grp.html e o manual Markdown para LLMs")
    p_build.set_defaults(func=cmd_build)

    # build-manual
    p_bman = subparsers.add_parser("build-manual", help="Compilar apenas o manual consolidado em Markdown para LLMs")
    p_bman.set_defaults(func=cmd_build_manual)

    # validate
    p_val = subparsers.add_parser("validate", help="Executar auditoria cruzada de tags XML vs Dicionário")
    p_val.set_defaults(func=cmd_validate)

    # test-all
    p_test_all = subparsers.add_parser("test-all", help="Executar todas as baterias de testes automatizados")
    p_test_all.set_defaults(func=cmd_test_all)

    # run (Universal Test Runner)
    p_run = subparsers.add_parser("run", help="Executar cenários, etapas ou cadeias com overrides e persistência")
    p_run.add_argument("--scenario", "-s", default=None, help="ID do cenário (ex: Chamada-01 a Chamada-64)")
    p_run.add_argument("--stage", default=None, help="Etapa avulsa (processo, empenho, olp, op, reforco, anulacao)")
    p_run.add_argument("--chain", default=None, help="Cadeia customizada separada por vírgula (ex: processo,empenho,op)")
    p_run.add_argument("--set", dest="set_params", nargs="*", default=None, help="Sobrescrever parâmetros (ex: --set valor=50.00 credor=123...)")
    p_run.add_argument("--live", "-l", action="store_true", help="Executar requisição SOAP real contra o GRP PRODEMGE")
    
    # Flags dedicadas de conveniência para override
    p_run.add_argument("--valor", "-v", default=None, help="Valor bruto da despesa (ex: 1.00 ou 50.00)")
    p_run.add_argument("--retencao-inss", default=None, help="Valor da retenção de INSS (ex: 0.11)")
    p_run.add_argument("--retencao-issqn", default=None, help="Valor da retenção de ISSQN (ex: 0.05)")
    p_run.add_argument("--credor", default=None, help="CPF ou CNPJ do credor")
    p_run.add_argument("--justificativa", "-j", default=None, help="Justificativa da despesa")
    p_run.add_argument("--processo", default=None, help="Número de processo existente")
    p_run.add_argument("--empenho", "-e", default=None, help="Número de empenho existente")
    p_run.add_argument("--olp", default=None, help="Número de OLP existente")
    p_run.add_argument("--cpf-ordenador", default=None, help="CPF do ordenador de despesa")
    p_run.add_argument("--cpf-operador", default=None, help="CPF do operador")
    p_run.add_argument("--banco-cred", default=None, help="Código do banco a creditar (ex: 001)")
    p_run.add_argument("--ag-cred", default=None, help="Agência a creditar (ex: 9012)")
    p_run.add_argument("--dv-ag-cred", default=None, help="DV da agência a creditar (ex: 6)")
    p_run.add_argument("--conta-cred", default=None, help="Conta a creditar (ex: 90006)")
    p_run.add_argument("--dv-conta-cred", default=None, help="DV da conta a creditar (ex: 3)")
    p_run.add_argument("--tipo-conta-deb", type=int, default=None, help="Tipo conta débito (1: Tesouro / 2: Específica)")
    p_run.add_argument("--tipo-conta-cred", type=int, default=None, help="Tipo conta crédito (1: Corrente / 2: Poupança)")
    p_run.set_defaults(func=cmd_run)

    # list-scenarios
    p_lsc = subparsers.add_parser("list-scenarios", help="Listar os 64 cenários combinatórios da esteira")
    p_lsc.set_defaults(func=cmd_list_scenarios)

    # list-tags
    p_ltags = subparsers.add_parser("list-tags", help="Listar as 138 tags cadastradas no dicionário")
    p_ltags.set_defaults(func=cmd_list_tags)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
