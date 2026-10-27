# -*- coding: utf-8 -*-
"""
Módulo Gerador de Manual Consolidado em Markdown para LLMs (core.markdown_generator)
Compila todas as regras, contratos SOAP, herança de dados, matriz combinatória dos 64 cenários,
dicionário das 138 tags XML e guia de resolução de erros em um arquivo Markdown semântico puro.
"""

import os
from core.config import (
    OUTPUT_MARKDOWN_PATH,
    URL_GERAR_PROCESSO,
    URL_EMPENHO,
    URL_OLP,
    URL_OP_BANCARIA,
    URL_REFORCO_EMPENHO,
    URL_ANULACAO_EMPENHO,
    URL_ANULACAO_OLP,
    URL_CANCELAMENTO_OP
)
from core.registry import default_registry
from core.scenarios import default_scenarios
from core.sanitizer import sanitize_xml_text
from core import conteudo_compartilhado as cc
from core.contrato import resumo_tag



def generate_markdown_manual() -> str:
    """Gera a especificação técnica integral em Markdown otimizado para LLMs."""
    tags = default_registry.get_all_tags()
    scenarios = default_scenarios.get_all_scenarios()
    manut = default_scenarios.get_manutencao()

    # Cenário de referência canônico para exemplos da cadeia regular (Chamada-04: INSS + ISSQN)
    sample_scenario = scenarios[3] if len(scenarios) >= 4 else scenarios[0]

    md = []

    # =========================================================================
    # CABEÇALHO & CONTEXTO PARA LLMs
    # =========================================================================
    md.append("# 📘 Manual Oficial de Integração SOAP da API do GRP-Minas (SEF-MG / PRODEMGE)")
    md.append("")
    md.append("> **📌 Contexto do Sistema para Modelos de Linguagem (LLMs / Agentes de IA):**")
    md.append("> Este manual é a especificação técnica consolidada dos Web Services SOAP do **Sistema Integrado de Gestão Pública (GRP)** do **Governo do Estado de Minas Gerais (PRODEMGE / SEF-MG)**.")
    md.append("> Ele documenta a arquitetura de execução da despesa pública estadual, os contratos WSDL/XSD, as regras fiscobancárias, a cadeia sequencial de herança de dados entre etapas, a retenção de IRRF na OP, exemplos reais de envio e resposta, a matriz histórica de 64 cenários (23/09/2026), o dicionário de 138 tags XML e o guia de diagnóstico de erros.")
    md.append("> Utilize este contexto para gerar código de integração robusto (Python, Java, Node, C#, etc.), validar envelopes XML e auxiliar equipes de desenvolvimento em auditorias fiscais.")
    md.append("")
    md.append(cc.bloco_versao())
    md.append("")
    md.append("---")
    md.append("")

    # =========================================================================
    # SEÇÃO 1: ARQUITETURA GERAL & ENDPOINTS OFICIAIS
    # =========================================================================
    md.append("## 1. 🌐 Arquitetura Geral & Endpoints Oficiais")
    md.append("")
    md.append("* **Protocolo:** SOAP 1.1 / 1.2 sobre HTTP/HTTPS")
    md.append("* **Método HTTP:** `POST`")
    md.append("* **Header Obrigatório:** `Content-Type: text/xml; charset=utf-8`")
    md.append("* **Formato do Body:** XML estruturado no envelope SOAP padrão (`<soapenv:Envelope>`)")
    md.append("* **Aviso Crítico de URL:** Utilize sempre o subdomínio oficial com `www` (`https://www.grp.servicos.mg.gov.br/...`). Requisições sem `www` recebem redirecionamento `HTTP 301 Moved Permanently`, descartando o payload `POST`.")
    md.append("")
    md.append("### Tabela de Endpoints dos Web Services:")
    md.append("")
    md.append(cc.bloco_endpoints())
    md.append("")
    md.append("### 1.1. Como Reproduzir os Testes (Árvore Interativa)")
    md.append("")
    md.append(cc.bloco_arvore())
    md.append("")
    md.append("---")
    md.append("")

    # =========================================================================
    # SEÇÃO 2: O CICLO DA DESPESA EM CADEIA & REGRA DE OURO
    # =========================================================================
    md.append("## 2. 🔄 O Ciclo da Despesa em Cadeia (A Regra de Ouro da Herança de Dados)")
    md.append("")
    md.append("A execução regular de despesa pública no GRP é **sequencial e encadeada**: cada etapa usa o número do documento gerado na etapa anterior. Esse documento pode ter sido gerado pela API ou registrado pela tela do GRP, então não é preciso fazer todas as etapas pela API (ex.: uma OP pela API sobre uma OLP registrada na tela). A exceção são os documentos do Portal de Compras (sistema `2`), cuja OP é feita pela tela do GRP (seção 2.1).")
    md.append("")
    md.append("### Fluxo Sequencial de Execução:")
    md.append("```text")
    md.append("  [ 1. ABERTURA DE PROCESSO ] (GerarNumeroProcessoGrpWS)")
    md.append("              │")
    md.append("              ▼ (Retorna: <numeroProcesso> com 21 dígitos)")
    md.append("  [ 2. RESERVA E EMPENHO ]    (SolicitacaoEmpenhoWS)")
    md.append("              │")
    md.append("              ▼ (Recebe: <numeroProcessoGeral> | Retorna: <numeroDocumento> do Empenho)")
    md.append("  [ 3. LIQUIDAÇÃO / OLP ]     (SolicitacaoOlpWS)")
    md.append("              │")
    md.append("              ▼ (Recebe: <numeroDocumentoEmpenho> | Retorna: <numeroDocumento> da OLP)")
    md.append("  [ 4. PAGAMENTO / OBM ]      (SolicOrdemPagamentoBancariaWS)")
    md.append("                (Recebe: <anoNumeroDaOlpEEmpenho> como 'AAAA/Nº OLP' | Gera Ordem Bancária)")
    md.append("```")
    md.append("")
    md.append("> **💡 A Regra de Ouro:** O número de documento (`<numeroDocumento>`) gerado com sucesso em uma fase é a chave de entrada da chamada seguinte. O integrador deve guardar o retorno de cada etapa para alimentar a próxima.")
    md.append("")
    md.append("### 2.1. Regra do Sistema de Origem")
    md.append("")
    md.append(cc.bloco_sistema_origem())
    md.append("")
    md.append("---")
    md.append("")

    # =========================================================================
    # SEÇÃO 3: OPERAÇÕES DE MANUTENÇÃO DE EMPENHO
    # =========================================================================
    md.append("## 3. 🔧 Operações de Manutenção (Fora da Cadeia Linear)")
    md.append("")
    md.append("Quando um empenho, uma OLP ou uma OP já foi emitido e precisa de ajuste ou cancelamento sem reprocessar toda a cadeia, utilizam-se os serviços de manutenção:")
    md.append("")
    md.append("### 3.1. Solicitação de Reforço de Empenho (`SolicitacaoReforcoDeEmpenhoWS`)")
    md.append("* **Objetivo:** Acréscimo de saldo orçamentário em empenhos vigentes. Validado com empenho `ESTIMATIVO`; `ORDINARIO` é recusado (*Tipo de Empenho não permite reforço*); `GLOBAL` ainda não testado (divergência D4).")
    md.append("* **Campos:** `<numeroEmpenho>`, UO, órgão, UA, ordenador, operador, `<valorReforco>` e justificativa, todos direto em `<solicitacaoReforcoEmpenho>`. O GRP herda credor, dotações e contas do empenho.")
    md.append("")
    md.append("### 3.2. Solicitação de Anulação de Saldo de Empenho (`SolicitacaoAnulacaoEmpenhoWS`)")
    md.append("* **Objetivo:** Cancelamento parcial ou total de saldo orçamentário não liquidado em OLP, liberando o recurso orçamentário.")
    md.append("* **Campos:** `<numeroEmpenho>`, UO, órgão, UA, ordenador, operador, `<valorAnulacaoEmpenho>` e justificativa, dentro de um elemento interno com o mesmo nome da operação (`<gerarSolicitacaoAnulacaoSaldoEmpenho>`). Atua sobre o saldo remanescente do empenho.")
    md.append("")
    md.append("### 3.3. Solicitação de Anulação de Valores na OLP (`SolicitacaoAnulacaoValoresNaOlpWS`)")
    md.append("* **Objetivo:** Anular valores de uma OLP já gerada.")
    md.append("* **Mínimo aceito:** `<numeroOlp>`, UO, órgão, UA, ordenador, `<valorLiquidoAnulado>`, `<valorTotalAnulado>` e justificativa. O sucesso vem como *Encaminhada para análise*, sem `numeroDocumento`.")
    md.append("")
    md.append("### 3.4. Cancelamento de Ordem de Pagamento Bancária (`CancelamentoOrdemPagamentoBancariaWS`)")
    md.append("* **Objetivo:** Cancelar uma OP bancária já gerada (enquanto pendente).")
    md.append("* **Chave:** `<numeroDocumentoOrdemDePagamento>` é o **número do documento** da OP (`numeroDocumento` da resposta), não o número da solicitação. Um número errado cancela **outra** OP.")
    md.append("* **Identificador:** só `PGBANESC1.2.1` funcionou (`PGBANESC1.1.x`, `1.2.2` e `1.2.3` falharam). O sucesso vem como *Concluída* (`54533`).")
    md.append("")
    md.append("---")
    md.append("")

    # =========================================================================
    # SEÇÃO 4: PRÉ-REQUISITOS & CADASTROS PRÉVIOS NO GRP
    # =========================================================================
    md.append("## 4. ⚙️ Pré-requisitos & Cadastros Prévios no Sistema GRP")
    md.append("")
    md.append("Antes de disparar chamadas de API, o ambiente administrativo do GRP deve atender às seguintes condições:")
    md.append("")
    md.append("1. **✍️ Exceção de Assinatura do Ordenador de Despesa:**")
    md.append("   - O CPF informado como `<cpfOrdenadorDespesa>` deve estar cadastrado no GRP com **perfil de exceção de assinatura** para todas as fases (Empenho, OLP e OP) na Unidade Administrativa (UA) executora.")
    md.append("   - *Finalidade:* Permite que o GRP registre e auto-aprove o documento imediatamente na resposta síncrona SOAP. Sem isso, as etapas ficam retidas aguardando assinatura manual no portal web, interrompendo a cadeia via API.")
    md.append("")
    md.append("2. **💰 Programação Orçamentária e Financeira:**")
    md.append("   - A UA deve possuir cotas ativas de Programação Orçamentária (saldo de dotação) e de Programação Financeira (recurso financeiro descentralizado) aprovadas no GRP para evitar rejeição por saldo insuficiente.")
    md.append("")
    md.append("3. **👥 Cadastro Prévio de Favorecidos / Credores:**")
    md.append("   - O credor (CPF ou CNPJ) deve estar cadastrado no GRP antes da chamada. Confira o cadastro e use em `<classificacaoCredor>` a classificação efetiva do credor, escrita exatamente como no cadastro, com acento (ex.: `BENEFICIÁRIOS DIVERSOS`, `PRESTADOR DE SERVIÇOS`, `SERVIDOR PÚBLICO ESTADUAL`).")
    md.append("   - Trocar a classificação não substitui o cadastro: se o favorecido ainda não existe no GRP, ou se a classificação enviada não é a dele, o GRP responde **Erro 85910** (*valor não cadastrado*). Nesse caso, cadastre o credor no GRP ou corrija a classificação, e envie de novo.")
    md.append("")
    md.append("4. **📊 Parametrização Contábil da Natureza do Item:**")
    md.append("   - A combinação Órgão + Elemento de Despesa + Item de Despesa (ex.: `031` / `005`) deve possuir amarração contábil ativa no plano de contas da **Subsecretaria do Tesouro Estadual (STE/SEF)** para o exercício financeiro.")
    md.append("")
    md.append("5. **👤 Ordenador Autorizado na UO/UA no Exercício:**")
    md.append("   - Sem essa autorização, o GRP responde `0` — *Ordenador de despesa não está autorizado para UO ..., UA ...*.")
    md.append("")
    md.append("6. **📦 Elemento-Item Liberado para o Sistema de Origem:**")
    md.append("   - Cada elemento-item tem um sistema dono no GRP. Com outro sistema, o GRP responde `0` — *Sistema ... diferente do sistema do elemento-item*.")
    md.append("")
    md.append("### 4.1. Regras Práticas de Envio")
    md.append("")
    md.append(cc.bloco_regras_envio())
    md.append("")
    md.append("---")
    md.append("")

    # =========================================================================
    # SEÇÃO 5: ESPECIFICAÇÃO DOS 6 CONTRATOS SOAP & EXEMPLOS REAIS DE XML
    # =========================================================================
    md.append("## 5. 📄 Especificação dos 8 Contratos SOAP & Exemplos Autênticos de XML")
    md.append("")

    # Etapa 1
    md.append("### 5.1. Etapa 1: Abertura do Processo Eletrônico (`GerarNumeroProcessoGrpWS`)")
    md.append(f"* **Endpoint:** `{URL_GERAR_PROCESSO}`")
    md.append("* **Operação SOAP:** `gerarNumeroProcessoGrp`")
    md.append("* **Parâmetros-Chave:** `<anoExercicio>`, `<codigoOrgao>`, `<codigoProcessoDeNegocio>` (`18` para despesas comuns), `<codigoUnidadeAdministrativa>`, `<codigoUnidadeOrcamentaria>`, `<codigoSistemaSolicitante>` (`51`).")
    md.append("* **Saída Esperada:** Número do Processo GRP com 21 dígitos (ex.: `101901800000398202611`).")
    md.append("")
    md.extend(cc.envio_xml(sample_scenario["xml_data"]["stage1"]["req"], "#### Payload de Envio (Request):"))
    md.append("")
    md.append("#### Payload de Retorno (Response):")
    md.append("```xml")
    md.append(sample_scenario["xml_data"]["stage1"]["res"].strip())
    md.append("```")
    md.append("")

    # Etapa 2
    md.append("### 5.2. Etapa 2: Reserva Orçamentária e Empenho (`SolicitacaoEmpenhoWS`)")
    md.append(f"* **Endpoint:** `{URL_EMPENHO}`")
    md.append("* **Operação SOAP:** `gerarSolicitacaoEmpenho`")
    md.append("* **Entrada Obrigatória:** `<numeroProcessoGeral>` (recebe os 21 dígitos da Etapa 1).")
    md.append("* **Parâmetros-Chave:** `<tipoEmpenhoComum>` (`ORDINARIO`, `ESTIMATIVO`, `GLOBAL`), dotação orçamentária completa, dados do favorecido e `<classificacaoCredor>`.")
    md.append("* **Saída Esperada:** Mensagem `41040` e `<numeroDocumento>` (Nº do Empenho gerado).")
    md.append("")
    md.extend(cc.envio_xml(sample_scenario["xml_data"]["stage2"]["req"], "#### Payload de Envio (Request):"))
    md.append("")
    md.append("#### Payload de Retorno (Response):")
    md.append("```xml")
    md.append(sample_scenario["xml_data"]["stage2"]["res"].strip())
    md.append("```")
    md.append("")

    # Etapa 3
    md.append("### 5.3. Etapa 3: Liquidação da Despesa / OLP (`SolicitacaoOlpWS`)")
    md.append(f"* **Endpoint:** `{URL_OLP}`")
    md.append("* **Operação SOAP:** `solicitarOLP`")
    md.append("* **Entrada Obrigatória:** `<numeroDocumentoEmpenho>` (recebe o Nº do Empenho da Etapa 2).")
    md.append("* **Regras Fiscais:**")
    md.append("  - **Retenções Tributárias (Erro `39148`):** O valor líquido deve fechar matematicamente: `<valorBrutoOlp> - <valorRetencaoOlp> = <valorLiquido>`. Retenções típicas: INSS (tipo `14`, aceito com credor CPF e CNPJ; o tipo `4` também foi aceito com credor CPF) e ISSQN (tipo `13`). O credor da retenção vai em `<cpfCapfCredorRetencao>`.")
    md.append("  - **IRRF não é retido na OLP:** a lista de tipos de retenção da OLP não tem o IRRF. Ele é inscrito na Etapa 4, dentro do item da OP (ver seção 5.4.1).")
    md.append("  - **Regionalização da Despesa (Erro `49762`):** Quando exigida, o bloco `<regionalizacaoDespesaOlpRequestList>` com `<codigoMunicipio>` de 7 dígitos (padrão IBGE) é obrigatório; nas demais, deve ser omitido.")
    md.append("* **Saída Esperada:** Mensagem `41040` e `<numeroDocumento>` (Nº da OLP gerada).")
    md.append("")
    md.extend(cc.envio_xml(sample_scenario["xml_data"]["stage3"]["req"], "#### Payload de Envio (Request):"))
    md.append("")
    md.append("#### Payload de Retorno (Response):")
    md.append("```xml")
    md.append(sample_scenario["xml_data"]["stage3"]["res"].strip())
    md.append("```")
    md.append("")

    # Etapa 4
    md.append("### 5.4. Etapa 4: Autorização Bancária de Pagamento / OBM (`SolicOrdemPagamentoBancariaWS`)")
    md.append(f"* **Endpoint:** `{URL_OP_BANCARIA}`")
    md.append("* **Operação SOAP:** `gerarSolicOrdemPagamentoBancaria`")
    md.append("* **Entrada Obrigatória:** `<anoNumeroDaOlpEEmpenho>` (no formato `AAAA/Nº da OLP`, ex.: `2026/49995`).")
    md.append("* **Regras Bancárias:**")
    md.append("  - `<tipoContaADebitar>`: `1` para Conta Única (Tesouro Estadual, dispensa dados bancários a debitar) ou `2` para Conta Específica (convênios/projetos com banco/agência/conta preenchidos).")
    md.append("  - **Dígito Verificador da Agência (Erro `40515`):** Bancos digitais sem DV de agência (Inter `077`, Nubank `260`, C6 `336`) exigem a **omissão completa** da tag `<dvAgenciaACreditar>`.")
    md.append("  - **Dígito Verificador da Conta:** Contas bancárias sem DV exigem obrigatoriamente `<dvContaACreditar>0</dvContaACreditar>`.")
    md.append("  - **Conta Específica (`tipoContaADebitar` 2):** exige banco, agência, DV, conta e DV a debitar e `<finalidadePagamento>` (sem ela, erro `38727`).")
    md.append("  - **Código de barras (`codigoFormaPagamento` 002):** exige `<codigoBarras>` e `<finalidadePagamento>`, sem conta a creditar. Funciona também em OLP registrada como crédito em conta (aceito em 15/10/2026, solicitação `130321`); alguns bancos recusam o boleto (erro `45769`).")
    md.append("  - **`<finalidadePagamento>`:** com Conta Única e forma 001 pode ser omitida. Quando exigida, o GRP aceitou qualquer texto (ex.: `01`, `Não se aplica`).")
    md.append("  - **INSS e ISSQN não vão na OP:** essas retenções são formalizadas e retidas exclusivamente na Etapa 3 (`SolicitacaoOlpWS`). Na Etapa 4 (`SolicOrdemPagamentoBancariaWS`), **não se inclui** `<retencaoList>` nem `<valorTotalRetencoes>`; informa-se diretamente o valor líquido já descontado em `<valorTotalAPagarDaOP>`, `<valorLiquidoPagamento>` e nos campos do item de pagamento.")
    md.append("  - **Exceção: IRRF.** O Imposto de Renda Retido na Fonte é inscrito **na própria OP**, num bloco `<retencao>` dentro do `<ItemDePagamento>`, e muda a regra dos valores. Ver seção 5.4.1.")
    md.append("  - **OLP de exercício anterior (restos a pagar):** toda OLP de exercício anterior testada voltou `37144` (*getExigeInstrumentoJuridico() is null*) pela API, com qualquer valor de instrumento jurídico e de exercício; pela tela do GRP o pagamento funciona. Caso aberto com a PRODEMGE.")
    md.append("  - **Número da solicitação × número do documento:** a consulta de OPs do GRP pesquisa pelo `numeroSolicitacao`; o cancelamento usa o `numeroDocumento`. Os dois andam juntos, mas não são iguais.")
    md.append("* **Saída Esperada:** Mensagem `51424` e emissão da Ordem de Pagamento Bancária (OBM).")
    md.append("")
    md.extend(cc.envio_xml(sample_scenario["xml_data"]["stage4"]["req"], "#### Payload de Envio (Request):"))
    md.append("")
    md.append("#### Payload de Retorno (Response):")
    md.append("```xml")
    md.append(sample_scenario["xml_data"]["stage4"]["res"].strip())
    md.append("```")
    md.append("")

    # Etapa 4: IRRF inscrito na OP
    md.append("### 5.4.1. OP com Retenção de Imposto de Renda (IRRF)")
    md.append("")
    md.append(cc.bloco_irrf())
    md.append("")

    # Manutenção: Reforço
    md.append("### 5.5. Manutenção: Solicitação de Reforço de Empenho (`SolicitacaoReforcoDeEmpenhoWS`)")
    md.append(f"* **Endpoint:** `{URL_REFORCO_EMPENHO}`")
    md.append("* **Operação SOAP:** `gerarSolicitacaoReforcoEmpenho`")
    md.append("* **Parâmetros:** `<numeroEmpenho>`, `<codigoUnidadeOrcamentaria>`, `<codigoOrgaoExecutor>`, `<codigoUnidadeAdministrativa>`, `<cpfOrdenadorDespesa>`, `<cpfOperador>`, `<valorReforco>`, `<justificativa>`.")
    md.append("* **Estrutura confirmada** pelo contrato de 26/10/2026 e pelo caso real abaixo (solicitação `27`, 16/06/2026). O retorno foi registrado só com os campos do `<return>`, por isso aparece em JSON.")
    md.append("")
    md.extend(cc.envio_xml(manut["reforco"]["req"], "#### Payload de Envio (Request):"))
    md.append("")
    md.append("#### Retorno (campos do `<return>`, registrados em JSON):")
    md.append("```json")
    md.append(manut["reforco"]["res"].strip())
    md.append("```")
    md.append("")

    # Manutenção: Anulação
    md.append("### 5.6. Manutenção: Solicitação de Anulação de Saldo de Empenho (`SolicitacaoAnulacaoEmpenhoWS`)")
    md.append(f"* **Endpoint:** `{URL_ANULACAO_EMPENHO}`")
    md.append("* **Operação SOAP:** `gerarSolicitacaoAnulacaoSaldoEmpenho`")
    md.append("* **Parâmetros:** `<numeroEmpenho>`, `<codigoUnidadeOrcamentaria>`, `<codigoOrgaoExecutor>`, `<codigoUnidadeAdministrativa>`, `<cpfOrdenadorDespesa>`, `<cpfOperador>`, `<valorAnulacaoEmpenho>`, `<justificativa>`.")
    md.append("* **Estrutura confirmada** pelo contrato de 26/10/2026 e pelo caso real abaixo (solicitação `98`, 15/06/2026). O retorno foi registrado só com os campos do `<return>`, por isso aparece em JSON.")
    md.append("")
    md.extend(cc.envio_xml(manut["anulacao"]["req"], "#### Payload de Envio (Request):"))
    md.append("")
    md.append("#### Retorno (campos do `<return>`, registrados em JSON):")
    md.append("```json")
    md.append(manut["anulacao"]["res"].strip())
    md.append("```")
    md.append("")
    md.append("### 5.7. Manutenção: Anulação de Valores na OLP (`SolicitacaoAnulacaoValoresNaOlpWS`)")
    md.append(f"* **Endpoint:** `{URL_ANULACAO_OLP}`")
    md.append("* **Operação SOAP:** `solicitarAnulacaoValoresNaOLP` (o elemento interno tem o mesmo nome da operação).")
    md.append("* **Identificador:** `EMPOLP2.2`.")
    md.append("")
    md.extend(cc.envio_xml(cc.ANULACAO_OLP_REQ, "#### Payload de Envio (Request) — caso real de 15/06/2026:"))
    md.append("")
    md.append("#### Retorno (campos do `<return>`, registrados em JSON):")
    md.append("```json")
    md.append(cc.ANULACAO_OLP_RES.strip())
    md.append("```")
    md.append("")
    md.append("### 5.8. Cancelamento de Ordem de Pagamento Bancária (`CancelamentoOrdemPagamentoBancariaWS`)")
    md.append(f"* **Endpoint:** `{URL_CANCELAMENTO_OP}`")
    md.append("* **Operação SOAP:** `cancelarOrdemPagamentoBancaria`.")
    md.append("* **Identificador:** `PGBANESC1.2.1`. Chave: `numeroDocumentoOrdemDePagamento` = número do **documento** da OP.")
    md.append("")
    md.extend(cc.envio_xml(cc.CANCELAMENTO_OP_REQ, "#### Payload de Envio (Request) — caso real de 15/06/2026 (confirmado de novo em 13/10/2026):"))
    md.append("")
    md.append("#### Retorno (campos do `<return>`, registrados em JSON):")
    md.append("```json")
    md.append(cc.CANCELAMENTO_OP_RES.strip())
    md.append("```")
    md.append("")
    md.append("### 5.9. Contratos WSDL Atuais (o que mudou)")
    md.append("")
    md.append(cc.bloco_contratos())
    md.append("")
    md.append("---")
    md.append("")

    # =========================================================================
    # SEÇÃO 6: MATRIZ COMBINATÓRIA DOS 64 CENÁRIOS HOMOLOGADOS
    # =========================================================================
    md.append("## 6. 📊 Matriz Combinatória dos 64 Cenários Homologados")
    md.append("")
    md.append("> **Base histórica (23/09/2026):** chamadas reais, mas anteriores ao IRRF e a várias regras aprendidas depois. Para montar uma chamada atual, use a árvore interativa (seção 1.1).")
    md.append("")
    md.append("A matriz completa de testes cobre **64 combinações ortogonais** derivadas de 5 variáveis fiscobancárias ($2 \\times 2 \\times 2 \\times 2 \\times 4 = 64$):")
    md.append("")
    md.append("1. **Tipo de Credor / Favorecido (2 variações):**")
    md.append("   - `CPF`: Pessoa Física (11 dígitos).")
    md.append("   - `CNPJ`: Pessoa Jurídica (14 dígitos).")
    md.append("2. **Regionalização na OLP (2 variações):**")
    md.append("   - `Sem Regionalização`: Despesas administrativas comuns.")
    md.append("   - `Com Regionalização`: Despesas com preenchimento obrigatório de `<codigoMunicipio>` de 7 dígitos (IBGE).")
    md.append("3. **Tipo de Conta a Debitar (2 variações):**")
    md.append("   - `1 - Conta Única (Tesouro)`: Débito automático na Conta Única do Estado.")
    md.append("   - `2 - Conta Específica`: Débito em conta bancária vinculada a convênios ou fundos.")
    md.append("4. **Tipo de Conta a Creditar (2 variações):**")
    md.append("   - `1 - Conta Corrente`: Crédito em conta corrente do favorecido.")
    md.append("   - `2 - Poupança`: Crédito em caderneta de poupança (exige mesmo banco da conta debitada).")
    md.append("5. **Perfil de Retenção Tributária (4 variações):**")
    md.append("   - `Sem Retenção`: Pagamento bruto integral.")
    md.append("   - `INSS`: Retenção previdenciária (tipo 14).")
    md.append("   - `ISSQN`: Retenção de imposto municipal (tipo 13).")
    md.append("   - `INSS + ISSQN`: Dupla retenção com cálculo líquido estrito.")
    md.append("")
    md.append("> **IRRF fora da matriz:** a retenção de Imposto de Renda é feita na Etapa 4 (OP), não na OLP, e não faz parte destes 64 cenários. Ver seção 5.4.1.")
    md.append("")
    md.append("### 6.1. Exemplos de Envio e Resposta por Cenário")
    md.append("")
    md.append(cc.bloco_exemplos_cenarios(scenarios, nivel_titulo="####"))
    md.append("")
    md.append("---")
    md.append("")

    # =========================================================================
    # SEÇÃO 7: DICIONÁRIO CONSOLIDADO DAS 138 TAGS XML
    # =========================================================================
    md.append("## 7. 🏷️ Dicionário Consolidado das 138 Tags XML")
    md.append("")
    md.append("As 138 tags da planilha `dic-tags-api.xlsx`. As colunas separam três coisas diferentes:")
    md.append("")
    md.append("* **Contrato atual:** tipo estrutural e obrigatoriedade, lidos do contrato WSDL da produção de 26/10/2026, por serviço, separando envio e resposta. Quando a mesma tag tem tipos diferentes em serviços diferentes, cada um aparece.")
    md.append("* **Formatação e regra:** como preencher (formatação recomendada) e as regras de negócio observadas em chamadas reais, que vão além do contrato.")
    md.append("* Tags marcadas *Não está no contrato atual* aparecem em casos históricos e não devem ser usadas em implementações novas.")
    md.append("")
    md.append("| Tag XML | Conceito | Contrato atual (tipo e obrigatoriedade) | Formatação e regra |")
    md.append("| :--- | :--- | :--- | :--- |")

    for t in tags:
        clean_tag = t["name"].replace("|", "\\|")
        conceito = t["conceito"].replace("\n", " ").replace("|", "\\|")
        regra = t["regra"].replace("\n", " ").replace("|", "\\|")
        md.append(f"| `{clean_tag}` | {conceito} | {resumo_tag(t['name'])} | {regra} |")

    md.append("")
    md.append("---")
    md.append("")

    # =========================================================================
    # SEÇÃO 8: TABELA DE DIAGNÓSTICO & RESOLUÇÃO DE ERROS
    # =========================================================================
    md.append("## 8. 🔍 Tabela de Diagnóstico & Resolução de Erros SOAP do GRP")
    md.append("")
    md.append(cc.bloco_erros())
    md.append("")
    md.append("---")
    md.append("")

    # =========================================================================
    # SEÇÃO 9: SCRIPT MODELO PRONTO EM PYTHON
    # =========================================================================
    md.append("## 9. 🐍 Template de Código Pronto em Python (`requests`)")
    md.append("")
    md.append("Snippet didático e funcional para disparo da primeira etapa (`GerarNumeroProcessoGrpWS`) com tratamento de proxy e SSL corporativo:")
    md.append("")
    md.append("```python")
    md.append("import requests")
    md.append("import warnings")
    md.append("from urllib3.exceptions import InsecureRequestWarning")
    md.append("warnings.simplefilter('ignore', InsecureRequestWarning)")
    md.append("")
    md.append("# 1. Configuração do Endpoint e Headers SOAP")
    md.append('url = "https://www.grp.servicos.mg.gov.br/serviceBus/institucional/GerarNumeroProcessoGrpWS"')
    md.append('headers = {"Content-Type": "text/xml; charset=utf-8"}')
    md.append("")
    md.append("# 2. Payload XML de Envio")
    md.append("xml_payload = '''<?xml version=\"1.0\" encoding=\"utf-8\"?>")
    md.append('<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"')
    md.append('                  xmlns:grp="http://interfaces.webservices.institucional.business.grp.prodemge.gov.br/">')
    md.append('  <soapenv:Header/>')
    md.append('  <soapenv:Body>')
    md.append('    <grp:gerarNumeroProcessoGrp>')
    md.append('      <anoExercicio>2026</anoExercicio>')
    md.append('      <codigoOrgao>10190</codigoOrgao>')
    md.append('      <codigoProcessoDeNegocio>18</codigoProcessoDeNegocio>')
    md.append('      <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>')
    md.append('      <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>')
    md.append('      <codigoSistemaSolicitante>51</codigoSistemaSolicitante>')
    md.append('    </grp:gerarNumeroProcessoGrp>')
    md.append('  </soapenv:Body>')
    md.append("</soapenv:Envelope>'''")
    md.append("")
    md.append("# 3. Disparo da Requisição HTTP POST")
    md.append("session = requests.Session()")
    md.append("session.trust_env = False  # Desativa interferência de proxies locais da rede")
    md.append("response = session.post(url, data=xml_payload.encode('utf-8'), headers=headers, verify=False, timeout=30)")
    md.append("")
    md.append('print(f"Status Code: {response.status_code}")')
    md.append('print(f"XML de Retorno: {response.text}")')
    md.append("```")
    md.append("")

    md.append("---")
    md.append("")
    md.append("## 10. ⚠️ Divergências em Verificação")
    md.append("")
    md.append(cc.bloco_divergencias())
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 11. 🗂️ Histórico de Versões")
    md.append("")
    md.append(cc.bloco_historico())
    md.append("")

    return sanitize_xml_text("\n".join(md))


def save_markdown_manual(output_path: str = OUTPUT_MARKDOWN_PATH) -> str:
    """Gera e salva o manual em Markdown e reescreve os trechos comuns da DOCUMENTACAO, que andam juntos."""
    content = generate_markdown_manual()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    cc.atualizar_documentacao(default_scenarios.get_all_scenarios())
    return output_path
