#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Orquestração e Carga em Lote: Migração Live das 45 Chamadas com Retenção
(scripts/batch_runner_live.py)

Executa sequencialmente as 4 etapas (Processo -> Empenho -> OLP -> OP Bancária)
para todas as 45 chamadas que possuem retenção tributária (INSS, ISSQN, INSS + ISSQN),
gerando payloads simplificados na Etapa 4 (sem retencaoList e sem valorTotalRetencoes),
validando retornos reais da PRODEMGE (41040 / 51424) e atualizando data/chamadas_database.json.
"""

import os
import sys
import json
import time
import shutil
import argparse
from datetime import datetime

# Ajuste de encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Adiciona o diretório raiz ao PYTHONPATH
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.config import DATABASE_JSON_PATH, OUTPUT_HTML_PATH, OUTPUT_MARKDOWN_PATH
from core.scenarios import default_scenarios
from core.runner import default_runner
from core.compiler import compile_html_app
from core.markdown_generator import save_markdown_manual

# As 45 chamadas mapeadas ordenadas numericamente para simplificação da Etapa 4
SCENARIOS_45 = sorted([
    # INSS (15 chamadas)
    "Chamada-02", "Chamada-06", "Chamada-14", "Chamada-18", "Chamada-22",
    "Chamada-26", "Chamada-30", "Chamada-34", "Chamada-38", "Chamada-42",
    "Chamada-46", "Chamada-50", "Chamada-54", "Chamada-58", "Chamada-62",
    
    # ISSQN (15 chamadas)
    "Chamada-03", "Chamada-07", "Chamada-15", "Chamada-19", "Chamada-23",
    "Chamada-27", "Chamada-31", "Chamada-35", "Chamada-39", "Chamada-43",
    "Chamada-47", "Chamada-51", "Chamada-55", "Chamada-59", "Chamada-63",
    
    # INSS + ISSQN (15 chamadas)
    "Chamada-04", "Chamada-08", "Chamada-16", "Chamada-20", "Chamada-24",
    "Chamada-28", "Chamada-32", "Chamada-36", "Chamada-40", "Chamada-44",
    "Chamada-48", "Chamada-52", "Chamada-56", "Chamada-60", "Chamada-64"
], key=lambda x: int(x.split('-')[1]))


def create_backup(db_path: str):
    """Cria backup preventivo do banco de dados antes da carga."""
    bak_path = db_path + ".bak"
    if not os.path.exists(bak_path):
        shutil.copy2(db_path, bak_path)
        print(f"📦 Backup inicial criado: {bak_path}")
    else:
        print(f"📦 Backup existente verificado: {bak_path}")


def save_database(db_path: str, data: list):
    """Salva a base atualizada em formato JSON indentado."""
    temp_path = db_path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, db_path)


def extract_authentic_params(sc_obj: dict) -> dict:
    """Extrai os dados fiscais, bancários e orçamentários homologados do cenário a partir do XML original."""
    import re
    overrides = {}
    xml_data = sc_obj.get("xml_data", {})
    st1_req = xml_data.get("stage1", {}).get("req", "")
    st2_req = xml_data.get("stage2", {}).get("req", "")
    st4_req = xml_data.get("stage4", {}).get("req", "")
    
    # Processo
    m_proc = re.search(r'<codigoProcessoDeNegocio>(.*?)</codigoProcessoDeNegocio>', st1_req)
    if m_proc:
        try:
            overrides["codigo_processo"] = int(m_proc.group(1).strip())
        except ValueError:
            pass

    # Orçamento e Credor da Etapa 2 (Empenho)
    tag_map_st2 = {
        "codigoUnidadeOrcamentaria": "uo",
        "codigoOrgaoExecutor": "orgao_executor",
        "codigoUnidadeAdministrativa": "ua",
        "cpfOrdenadorDespesa": "cpf_ordenador",
        "cpfOperador": "cpf_operador",
        "tipoEmpenhoComum": "tipo_empenho",
        "cpfCnpjCredor": "credor_cpf_cnpj",
        "classificacaoCredor": "credor_classificacao",
        "codigoFuncao": "funcao",
        "codigoSubfuncao": "subfuncao",
        "codigoPrograma": "programa",
        "codigoProjetoAtividade": "projeto_atividade",
        "codigoSubprojetoSubatividade": "subprojeto",
        "codigoCategoriaEconomica": "categoria_eco",
        "codigoGrupoDespesa": "grupo_despesa",
        "codigoModalidadeDespesa": "modalidade",
        "codigoElementoDespesa": "elemento_grp",
        "codigoItem": "item_grp",
        "codigoIag": "iag",
        "codigoGrupoFonte": "grupo_fonte",
        "codigoFonteRecurso": "fonte_recurso",
        "codigoIpu": "ipu",
        "codigoCc": "cc"
    }
    for tag, key in tag_map_st2.items():
        m = re.search(f"<{tag}>(.*?)</{tag}>", st2_req)
        if m and m.group(1).strip():
            overrides[key] = m.group(1).strip()
            
    # Dados Bancários da Etapa 4 (OP)
    tag_map_st4 = {
        "tipoContaADebitar": "tipo_conta_a_debitar",
        "codigoBancoADebitar": "op_cod_banco_deb",
        "codigoAgenciaADebitar": "op_ag_deb",
        "dvAgenciaADebitar": "op_dv_ag_deb",
        "codigoContaADebitar": "op_conta_deb",
        "dvContaADebitar": "op_dv_conta_deb",
        "tipoContaACreditar": "tipo_conta_a_creditar",
        "codigoBancoACreditar": "op_cod_banco_cred",
        "codigoAgenciaACreditar": "op_ag_cred",
        "dvAgenciaACreditar": "op_dv_ag_cred",
        "codigoContaACreditar": "op_conta_cred",
        "dvContaACreditar": "op_dv_conta_cred",
        "codigoFormaPagamento": "codigo_forma_pagamento",
        "finalidadePagamento": "finalidade_pagamento"
    }
    for tag, key in tag_map_st4.items():
        m = re.search(f"<{tag}>(.*?)</{tag}>", st4_req)
        if m and m.group(1).strip():
            val = m.group(1).strip()
            if key in ("tipo_conta_a_debitar", "tipo_conta_a_creditar"):
                try:
                    val = int(val)
                except ValueError:
                    pass
            overrides[key] = val

    # Regionalização e Justificativa da Etapa 3 (OLP) e Etapa 2 (Empenho)
    st3_req = xml_data.get("stage3", {}).get("req", "")
    if "regionalizacaoDespesaOlpRequestList" in st3_req or "<codigoMunicipio>" in st3_req:
        overrides["exige_regionalizacao"] = True
        m_mun = re.search(r'<codigoMunicipio>(.*?)</codigoMunicipio>', st3_req)
        if m_mun:
            overrides["codigo_municipio"] = m_mun.group(1).strip()
    else:
        overrides["exige_regionalizacao"] = False

    m_just = re.search(r'<justificativa>(.*?)</justificativa>', st2_req)
    if m_just and m_just.group(1).strip():
        overrides["justificativa"] = m_just.group(1).strip()
            
    return overrides


def run_batch(scenario_ids: list = None, retry_limit: int = 2, delay_between: float = 1.0):
    """Executa a esteira em lote para a lista de cenários especificada."""
    print("=" * 80)
    print("🚀 INICIANDO EXECUÇÃO EM LOTE LIVE: PRODEMGE SOAP WEBSERVICES")
    print(f"📋 Total de Cenários a Processar: {len(scenario_ids)}")
    print(f"📄 Banco Alvo: {DATABASE_JSON_PATH}")
    print("=" * 80)

    create_backup(DATABASE_JSON_PATH)

    with open(DATABASE_JSON_PATH, "r", encoding="utf-8") as f:
        database = json.load(f)

    # Carrega dados do backup para herdar parâmetros fiscais e bancários autênticos
    bak_path = DATABASE_JSON_PATH + ".bak"
    bak_db = database
    if os.path.exists(bak_path):
        try:
            with open(bak_path, "r", encoding="utf-8") as f_bak:
                bak_db = json.load(f_bak)
        except Exception:
            pass
    bak_db_by_id = {c["id"]: c for c in bak_db}

    db_by_id = {c["id"]: c for c in database}

    sucessos = []
    falhas = []
    inicio_total = time.time()

    for idx, s_id in enumerate(scenario_ids, 1):
        sc_obj = db_by_id.get(s_id)
        if not sc_obj:
            print(f"⚠️ Cenário {s_id} não encontrado no banco. Pulando...")
            continue

        ret_tipo = sc_obj.get("retencao", "N/A")
        print(f"\n[{idx:02d}/{len(scenario_ids):02d}] ⚙️ Executando {s_id} | Retenção: {ret_tipo} | Cliente: {sc_obj.get('cliente')}...")

        # Extrai parâmetros autênticos do cenário homologado
        sc_original = bak_db_by_id.get(s_id, sc_obj)
        auth_overrides = extract_authentic_params(sc_original)

        tentativa = 0
        sucesso_cenario = False
        resultado = None

        while tentativa <= retry_limit and not sucesso_cenario:
            tentativa += 1
            if tentativa > 1:
                print(f"   🔄 Tentativa {tentativa}/{retry_limit + 1} para {s_id} após pausa...")
                time.sleep(2.0)

            t0 = time.time()
            try:
                # Executa cadeia completa ao vivo com overrides autênticos
                resultado = default_runner.run_scenario(s_id, overrides=auth_overrides, live=True)
                t_duracao = time.time() - t0

                if resultado.get("sucesso"):
                    sucesso_cenario = True
                else:
                    etapa_falha = resultado.get("etapa_falha", "desconhecida")
                    erro_msg = resultado.get("erro", "Erro sem descrição")
                    print(f"   ❌ Falha na etapa '{etapa_falha}': {erro_msg}")
            except Exception as e:
                print(f"   💥 Exceção inesperada na tentativa {tentativa}: {str(e)}")

        if sucesso_cenario:
            docs = resultado.get("documentos", {})
            p_res = resultado["resultados_etapas"]["processo"]
            e_res = resultado["resultados_etapas"]["empenho"]
            o_res = resultado["resultados_etapas"]["olp"]
            op_res = resultado["resultados_etapas"]["op"]

            # Verificação de segurança: a OP não pode conter tags de retenção
            op_req_xml = op_res["request_xml"]
            assert "<retencaoList>" not in op_req_xml, f"ERRO: <retencaoList> detectada no envio da OP em {s_id}!"
            assert "<valorTotalRetencoes>" not in op_req_xml, f"ERRO: <valorTotalRetencoes> detectada no envio da OP em {s_id}!"

            # Atualização atômica do registro no banco
            sc_obj["xml_etapas"] = {
                "stage1_processo": p_res["request_xml"],
                "stage2_empenho": e_res["request_xml"],
                "stage3_olp": o_res["request_xml"],
                "stage4_op": op_req_xml
            }
            sc_obj["xml_data"] = {
                "stage1": {"req": p_res["request_xml"], "res": p_res["response_xml"]},
                "stage2": {"req": e_res["request_xml"], "res": e_res["response_xml"]},
                "stage3": {"req": o_res["request_xml"], "res": o_res["response_xml"]},
                "stage4": {"req": op_req_xml, "res": op_res["response_xml"]}
            }
            sc_obj["etapa1_envio_xml"] = p_res["request_xml"]
            sc_obj["etapa1_retorno_xml"] = p_res["response_xml"]
            sc_obj["etapa2_envio_xml"] = e_res["request_xml"]
            sc_obj["etapa2_retorno_xml"] = e_res["response_xml"]
            sc_obj["etapa3_envio_xml"] = o_res["request_xml"]
            sc_obj["etapa3_retorno_xml"] = o_res["response_xml"]
            sc_obj["etapa4_envio_xml"] = op_req_xml
            sc_obj["etapa4_retorno_xml"] = op_res["response_xml"]

            # Salva o banco atualizado imediatamente
            save_database(DATABASE_JSON_PATH, database)

            sucessos.append({
                "id": s_id,
                "processo": docs.get("processo"),
                "empenho": docs.get("empenho"),
                "olp": docs.get("olp"),
                "op": docs.get("op"),
                "solicitacao_op": docs.get("solicitacao_op"),
                "tempo_s": round(t_duracao, 1)
            })

            op_doc = docs.get('op') or docs.get('solicitacao_op')
            print(f"   ✅ SUCESSO ({t_duracao:.1f}s) | Processo: {docs.get('processo')} | Emp: {docs.get('empenho')} | OLP: {docs.get('olp')} | OP: {op_doc}")
        else:
            falhas.append({
                "id": s_id,
                "etapa": resultado.get("etapa_falha") if resultado else "execucao",
                "erro": resultado.get("erro") if resultado else "Falha geral"
            })
            print(f"   ⛔ CENÁRIO {s_id} NÃO PÔDE SER CONCLUÍDO APÓS TENTATIVAS.")

        if delay_between > 0:
            time.sleep(delay_between)

    # Relatório Final
    tempo_total = time.time() - inicio_total
    print("\n" + "=" * 80)
    print("📊 RELATÓRIO FINAL DA CARGA EM LOTE LIVE")
    print("=" * 80)
    print(f"⏱️ Tempo total de execução: {tempo_total / 60:.1f} minutos ({tempo_total:.1f}s)")
    print(f"✅ Total com Sucesso: {len(sucessos)} / {len(scenario_ids)}")
    print(f"❌ Total com Falhas:  {len(falhas)} / {len(scenario_ids)}")

    if falhas:
        print("\nLista de cenários com falha:")
        for f in falhas:
            print(f"   • {f['id']} - Etapa: {f['etapa']} - Erro: {f['erro']}")

    # Se todos foram executados ou houve sucessos, recompila a aplicação
    if sucessos:
        print("\n🔨 Recompilando Árvore Interativa e Manual...")
        compile_html_app(OUTPUT_HTML_PATH)
        save_markdown_manual(OUTPUT_MARKDOWN_PATH)
        print("✨ Aplicação recompilada com os novos payloads!")


def main():
    parser = argparse.ArgumentParser(description="Batch Runner Live para as 45 chamadas com retenção.")
    parser.add_argument("--scenario", "-s", type=str, help="Executa apenas um cenário específico (ex: Chamada-02)")
    parser.add_argument("--from-id", type=str, help="Inicia a execução a partir de um cenário (ex: Chamada-14)")
    parser.add_argument("--to-id", type=str, help="Termina a execução no cenário informado (inclusive)")
    parser.add_argument("--limit", "-n", type=int, help="Número máximo de cenários a executar")
    parser.add_argument("--delay", type=float, default=1.0, help="Pausa em segundos entre cada cenário (padrão: 1.0s)")
    parser.add_argument("--retry", type=int, default=2, help="Número de tentativas por cenário (padrão: 2)")

    args = parser.parse_args()

    if args.scenario:
        scenarios = [args.scenario]
    else:
        scenarios = list(SCENARIOS_45)
        if args.from_id:
            if args.from_id in scenarios:
                idx = scenarios.index(args.from_id)
                scenarios = scenarios[idx:]
            else:
                print(f"❌ Cenário inicial {args.from_id} não encontrado na lista das 45 chamadas.")
                sys.exit(1)
        if args.to_id:
            if args.to_id in scenarios:
                idx_to = scenarios.index(args.to_id)
                scenarios = scenarios[:idx_to + 1]
            else:
                print(f"❌ Cenário final {args.to_id} não encontrado na lista das 45 chamadas.")
                sys.exit(1)
        if args.limit:
            scenarios = scenarios[:args.limit]

    run_batch(scenarios, retry_limit=args.retry, delay_between=args.delay)


if __name__ == "__main__":
    main()
