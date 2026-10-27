# -*- coding: utf-8 -*-
"""
Módulo de Gestão de Cenários e Matriz Combinatória (core.scenarios)
Gerencia as 64 chamadas da Cadeia Integrada e as operações de Manutenção de Empenho.
Garante fidelidade de 100% aos dados homologados em data/chamadas_database.json.
"""

import json
import os
from core.config import DATABASE_JSON_PATH, URL_OP_BANCARIA, URL_ANULACAO_OLP, URL_CANCELAMENTO_OP
from core import conteudo_compartilhado as cc

# Definição canônica das operações de Manutenção Orçamentária (Reforço e Anulação)
MANUTENCAO_DATA = {
    "reforco": {
        "id": "Reforco-01",
        "title": "Solicitação de Reforço de Empenho",
        "service": "SolicitacaoReforcoDeEmpenhoWS",
        "operacao": "gerarSolicitacaoReforcoEmpenho",
        "identificador": "EMPOLP1.2",
        "tipo_empenho": "ESTIMATIVO",
        "empenho_vinculado": "22575",
        "uo": "10191",
        "orgao": "10190",
        "ua": "1019080124",
        "valor_reforco": "1000.00",
        "req": """<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/"
                   xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicitacaoReforcoEmpenho>
      <solicitacaoReforcoEmpenho>
        <numeroRequisicao>222</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP1.2</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroEmpenho>22575</numeroEmpenho>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <valorReforco>1000.00</valorReforco>
        <justificativa>TESTE REFORCO DE EMPENHO 22575</justificativa>
      </solicitacaoReforcoEmpenho>
    </grp:gerarSolicitacaoReforcoEmpenho>
  </soap-env:Body>
</soap-env:Envelope>""",
        "res": """{
  "numeroRequisicao": "222",
  "codigoSistemaOrigem": "51",
  "anoExercicioFinanceiro": "2026",
  "numeroSolicitacao": "27",
  "situacaoSolicitacao": "Encaminhada para análise",
  "dataSolicitacao": "2026-06-16T10:16:22.433-03:00",
  "mensagens": [{"codigo": "41040", "descricao": "Solicitação Reforço de empenho da despesa gerado com sucesso!"}]
}""",
        "guide": "<strong>Solicitação de Reforço de Empenho (SolicitacaoReforcoDeEmpenhoWS)</strong><br><h5><strong>Método:</strong> POST</h5><h5><strong>Header:</strong> Content-Type: text/xml; charset=utf-8</h5><h5 style=\"margin-bottom: 10px;\"><strong>Endpoint:</strong> <a href=\"https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoReforcoDeEmpenhoWS\" target=\"_blank\" rel=\"noopener noreferrer\" style=\"color: blue; text-decoration: underline;\">https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoReforcoDeEmpenhoWS</a></h5><p><strong>🎯 Objetivo:</strong> Acréscimo de saldo orçamentário a um empenho pré-existente no GRP.<br><strong>⚠️ Cuidados:</strong><br>• <strong>Identificador de Processo:</strong> <code>EMPOLP1.2</code>.<br>• <strong>Modalidades Permitidas:</strong> Válido exclusivamente para empenhos dos tipos <code>ESTIMATIVO</code> ou <code>GLOBAL</code> (empenhos <code>ORDINARIO</code> não admitem reforço de saldo).<br>• <strong>Herança Automática Total:</strong> Não se enviam dotações orçamentárias, dados de credor ou contas bancárias; o GRP herda automaticamente toda a estrutura a partir do <code>&lt;numeroEmpenho&gt;</code> informado.<br><strong>✅ Retorno Esperado:</strong> Mensagem <code>41040</code> e situação <em>'Encaminhada para analise'</em>.</p>"
    },
    "anulacao": {
        "id": "Anulacao-01",
        "title": "Solicitação de Anulação de Saldo de Empenho",
        "service": "SolicitacaoAnulacaoEmpenhoWS",
        "operacao": "gerarSolicitacaoAnulacaoSaldoEmpenho",
        "identificador": "EMPOLP1.3",
        "tipo_empenho": "ESTIMATIVO",
        "empenho_vinculado": "22575",
        "uo": "10191",
        "orgao": "10190",
        "ua": "1019080124",
        "valor_anulacao": "500.00",
        "req": """<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/"
                   xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicitacaoAnulacaoSaldoEmpenho>
      <gerarSolicitacaoAnulacaoSaldoEmpenho>
        <numeroRequisicao>1510363400</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP1.3</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroEmpenho>22575</numeroEmpenho>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <valorAnulacaoEmpenho>500.00</valorAnulacaoEmpenho>
        <justificativa>TESTE ANULACAO EMPENHO 22575</justificativa>
      </gerarSolicitacaoAnulacaoSaldoEmpenho>
    </grp:gerarSolicitacaoAnulacaoSaldoEmpenho>
  </soap-env:Body>
</soap-env:Envelope>""",
        "res": """{
  "numeroRequisicao": "1510363400",
  "codigoSistemaOrigem": "51",
  "anoExercicioFinanceiro": "2026",
  "numeroSolicitacao": "98",
  "situacaoSolicitacao": "Encaminhada para análise",
  "numeroDocumento": null,
  "situacaoDocumento": null,
  "dataSolicitacao": "2026-06-15T10:36:39.632-03:00",
  "mensagens": [{"codigo": "41040", "descricao": "Solicitação de anulação de empenho gerado com sucesso!"}]
}""",
        "guide": "<strong>Solicitação de Anulação de Saldo de Empenho (SolicitacaoAnulacaoEmpenhoWS)</strong><br><h5><strong>Método:</strong> POST</h5><h5><strong>Header:</strong> Content-Type: text/xml; charset=utf-8</h5><h5 style=\"margin-bottom: 10px;\"><strong>Endpoint:</strong> <a href=\"https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoAnulacaoEmpenhoWS\" target=\"_blank\" rel=\"noopener noreferrer\" style=\"color: blue; text-decoration: underline;\">https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoAnulacaoEmpenhoWS</a></h5><p><strong>🎯 Objetivo:</strong> Cancelamento parcial ou total de saldo orçamentário não liquidado de um empenho, liberando o recurso orçamentário.<br><strong>⚠️ Cuidados:</strong><br>• <strong>Identificador de Processo:</strong> <code>EMPOLP1.3</code>.<br>• <strong>Regra de Saldo:</strong> Aplicável a empenhos <code>ORDINARIO</code>, <code>ESTIMATIVO</code> ou <code>GLOBAL</code>, desde que exista saldo remanescente não liquidado em OLP.<br>• <strong>Herança Automática Total:</strong> O XML dispensa dotações e dados de credor, exigindo apenas o <code>&lt;numeroEmpenho&gt;</code> e o <code>&lt;valorAnulacaoEmpenho&gt;</code>.<br>• <code>&lt;cpfOperador&gt;</code>: Deve ser preenchido dentro do bloco <code>&lt;anulacaoSaldoEmpenhoComum&gt;</code>.<br><strong>✅ Retorno Esperado:</strong> Mensagem <code>41040</code> e situação <em>'Encaminhada para analise'</em>.</p>"
    }
}

# Operações complementares exibidas no mesmo modo da árvore (OP com IRRF, anulação de valores na OLP e cancelamento de
# OP). Os XMLs vêm de core.conteudo_compartilhado, os mesmos do manual e da DOCUMENTACAO.
MANUTENCAO_DATA["irrf"] = {
    "id": "OP-IRRF-01",
    "title": "OP Bancária com retenção de IRRF",
    "service": "SolicOrdemPagamentoBancariaWS",
    "operacao": "gerarSolicOrdemPagamentoBancaria",
    "identificador": "PGBANESC1.1.1",
    "req": cc.EXEMPLO_OP_IRRF.strip(),
    "res": cc.RESPOSTA_OP_IRRF.strip(),
    "guide": """<strong>OP Bancária com retenção de Imposto de Renda (IRRF)</strong><br><h5><strong>Método:</strong> POST</h5><h5><strong>Header:</strong> Content-Type: text/xml; charset=utf-8</h5><h5 style="margin-bottom: 10px;"><strong>Endpoint:</strong> <a href="https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/SolicOrdemPagamentoBancariaWS" target="_blank" rel="noopener noreferrer" style="color: blue; text-decoration: underline;">https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/SolicOrdemPagamentoBancariaWS</a></h5>
               <p>
                 <strong>🆕 Situação:</strong> aceito na produção desde <strong>19/10/2026</strong> (caso real acima: solicitação <code>130905</code>, documento <code>117423</code>).<br>
                 <strong>📍 Onde vai:</strong> um bloco <code>&lt;retencao&gt;</code> <strong>dentro</strong> do <code>&lt;ItemDePagamento&gt;</code>, logo depois de <code>&lt;valorLiquido&gt;</code>, com <code>&lt;tipoRetencao&gt;10&lt;/tipoRetencao&gt;</code>, <code>&lt;valorRetencao&gt;</code>, <code>&lt;codigoReceita&gt;</code> (<code>090140</code> no exemplo da PRODEMGE) e <code>&lt;cpfCnpjCredorRetencao&gt;</code>. Cada item aceita uma só retenção.<br>
                 <strong>💰 Regra dos valores:</strong> <code>&lt;valorTotalAPagarDaOP&gt;</code>, <code>&lt;valorAPagar&gt;</code> e <code>&lt;valorTotalAPagar&gt;</code> vão com o valor <strong>antes</strong> do IRRF; <code>&lt;valorTotalRetencoes&gt;</code> = IRRF; <code>&lt;valorLiquidoPagamento&gt;</code> e <code>&lt;valorLiquido&gt;</code> vão <strong>sem</strong> o IRRF. Ex.: 2,00 − 1,00 = 1,00.<br>
                 <strong>⚠️ Cuidados:</strong><br>
                 • Não use a <code>&lt;retencaoList&gt;</code> no nível da OP: ela saiu do contrato e nunca reteve nada. Com ela e valores antes do IRRF, o GRP devolve <code>123</code>.<br>
                 • INSS e ISSQN continuam só na OLP; a OP não os leva.<br>
                 • O GRP não calcula a alíquota: o valor do IRRF é informado por quem envia.<br>
                 • Em aberto com a PRODEMGE: o código de receita para credor pessoa jurídica (<code>090140</code> veio de um exemplo com pessoa física).<br>
                 <strong>✅ Retorno Esperado:</strong> Mensagem <code>51424</code>.
               </p>"""
}

MANUTENCAO_DATA["anulacao_olp"] = {
    "id": "AnulacaoOLP-01",
    "title": "Anulação de Valores na OLP",
    "service": "SolicitacaoAnulacaoValoresNaOlpWS",
    "operacao": "solicitarAnulacaoValoresNaOLP",
    "identificador": "EMPOLP2.2",
    "req": cc.ANULACAO_OLP_REQ.strip(),
    "res": cc.ANULACAO_OLP_RES.strip(),
    "guide": """<strong>Solicitação de Anulação de Valores na OLP (SolicitacaoAnulacaoValoresNaOlpWS)</strong><br><h5><strong>Método:</strong> POST</h5><h5><strong>Header:</strong> Content-Type: text/xml; charset=utf-8</h5><h5 style="margin-bottom: 10px;"><strong>Endpoint:</strong> <a href="https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoAnulacaoValoresNaOlpWS" target="_blank" rel="noopener noreferrer" style="color: blue; text-decoration: underline;">https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoAnulacaoValoresNaOlpWS</a></h5>
               <p>
                 <strong>🎯 Objetivo:</strong> anular valores de uma OLP já gerada.<br>
                 <strong>⚠️ Cuidados:</strong><br>
                 • O elemento interno tem o mesmo nome da operação: <code>&lt;solicitarAnulacaoValoresNaOLP&gt;</code>.<br>
                 • Mínimo aceito: <code>&lt;numeroOlp&gt;</code>, UO, órgão, UA, ordenador, <code>&lt;valorLiquidoAnulado&gt;</code>, <code>&lt;valorTotalAnulado&gt;</code> e justificativa.<br>
                 <strong>✅ Retorno Esperado:</strong> <code>41040</code>, situação <em>Encaminhada para análise</em>, sem <code>numeroDocumento</code>. O retorno do caso real (15/06/2026) foi registrado só com os campos do <code>&lt;return&gt;</code>, em JSON.
               </p>"""
}

MANUTENCAO_DATA["cancelamento_op"] = {
    "id": "CancelamentoOP-01",
    "title": "Cancelamento de OP Bancária",
    "service": "CancelamentoOrdemPagamentoBancariaWS",
    "operacao": "cancelarOrdemPagamentoBancaria",
    "identificador": "PGBANESC1.2.1",
    "req": cc.CANCELAMENTO_OP_REQ.strip(),
    "res": cc.CANCELAMENTO_OP_RES.strip(),
    "guide": """<strong>Cancelamento de Ordem de Pagamento Bancária (CancelamentoOrdemPagamentoBancariaWS)</strong><br><h5><strong>Método:</strong> POST</h5><h5><strong>Header:</strong> Content-Type: text/xml; charset=utf-8</h5><h5 style="margin-bottom: 10px;"><strong>Endpoint:</strong> <a href="https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/CancelamentoOrdemPagamentoBancariaWS" target="_blank" rel="noopener noreferrer" style="color: blue; text-decoration: underline;">https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/CancelamentoOrdemPagamentoBancariaWS</a></h5>
               <p>
                 <strong>🎯 Objetivo:</strong> cancelar uma OP bancária já gerada, enquanto pendente.<br>
                 <strong>⚠️ Cuidados:</strong><br>
                 • <code>&lt;numeroDocumentoOrdemDePagamento&gt;</code> é o <strong>número do documento</strong> da OP (<code>numeroDocumento</code> da resposta), não o número da solicitação. Um número errado cancela <strong>outra</strong> OP.<br>
                 • Só <code>PGBANESC1.2.1</code> funcionou como identificador.<br>
                 <strong>✅ Retorno Esperado:</strong> <code>54533</code>, situação <em>Concluída</em> (confirmado de novo em 13/10/2026). O retorno do caso real foi registrado só com os campos do <code>&lt;return&gt;</code>, em JSON.
               </p>"""
}

# Definição das diretrizes e regras técnicas das 4 etapas da Cadeia Integrada
STAGE_GUIDES = {
    "stage1": """<h4>Etapa 1: Início do Processo Eletrônico no GRP (GerarNumeroProcessoGrpWS)</h4>
                <h5><strong>Método:</strong> POST</h5>
                <h5><strong>Header:</strong> Content-Type: text/xml; charset=utf-8</h5>
                <h5 style="margin-bottom: 10px;"><strong>Endpoint:</strong> <a href="https://www.grp.servicos.mg.gov.br/serviceBus/institucional/GerarNumeroProcessoGrpWS" target="_blank" rel="noopener noreferrer" style="color: blue; text-decoration: underline;">https://www.grp.servicos.mg.gov.br/serviceBus/institucional/GerarNumeroProcessoGrpWS</a></h5>
               <p>
                 <strong>🎯 Objetivo:</strong> Criação do processo eletrônico no GRP que servirá de lastro para toda a cadeia de execução da despesa.<br>
                 <strong>⚠️ Cuidados:</strong><br>
                 • <code>&lt;codigoProcessoDeNegocio&gt;</code>: Preencher sempre com 18.<br>
                 • <code>&lt;codigoSistemaSolicitante&gt;</code>: Preencher sempre com 51.<br>
                 <strong>🔗 Herança de dados:</strong> O número do processo GRP gerado pela operação <code>GerarNumeroProcessoGrpWS</code>, composto por 21 dígitos (ex.: <code>101901800000398202611</code>), deve ser informado na tag <code>&lt;numeroProcessoGeral&gt;</code> da chamada seguinte, <code>SolicitacaoEmpenhoWS</code>.<br>
                 <strong>✅ Retorno Esperado:</strong> Número de 21 dígitos, ex.: <code>101901800000398202611</code> gerado.
               </p>""",
    "stage2": """<h4>Etapa 2: Reserva Orçamentária e Empenho (SolicitacaoEmpenhoWS)</h4>
                  <h5><strong>Método:</strong> POST</h5>
                  <h5><strong>Header:</strong> Content-Type: text/xml; charset=utf-8</h5>
                  <h5 style="margin-bottom: 10px;"><strong>Endpoint:</strong> <a href="https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoEmpenhoWS" target="_blank" rel="noopener noreferrer" style="color: blue; text-decoration: underline;">https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoEmpenhoWS</a></h5>
               <p>
                 <strong>🎯 Objetivo:</strong> Emissão da Solicitação de Empenho, vinculando a dotação orçamentária ao credor/favorecido.<br>
                 <strong>⚠️ Cuidados:</strong><br>
                 • <code>&lt;tipoEmpenhoComum&gt;</code>: 
                   - <code>ORDINARIO</code>: Despesa com montante fixo e pagamento único;<br>
                   - <code>ESTIMATIVO</code>: Despesa cujo valor total não se pode determinar previamente (serviços contínuos, utilidades, premiações), admitindo reforço e anulação;<br>
                   - <code>GLOBAL</code>: Despesa contratual parcelada ao longo do exercício.<br>
                 • <code>&lt;classificacaoCredor&gt;</code> (Erro <code>85910</code>): Para favorecidos (CPF/CNPJ) sem cadastro prévio de fornecedor no ambiente do GRP, é necessário providenciar o cadastro no sistema e preencher essa tag de acordo com a classificação que foi inserida no GRP (ex.: <code>BENEFICIÁRIOS DIVERSOS</code> ou <code>PRESTADOR DE SERVIÇOS</code>).<br>
                 • <strong>Dotação Orçamentária:</strong> Órgão, UO, Função, Subfunção, Programa, Ação, Elemento, Item e Fonte de Recurso devem estar rigorosamente ativos.<br>
                 <strong>🔗 Herança de dados:</strong> Recebe, na tag <code>&lt;numeroProcessoGeral&gt;</code>, o número do processo GRP gerado pela operação anterior, <code>GerarNumeroProcessoGrpWS</code>, e retorna, na tag <code>&lt;numeroDocumento&gt;</code>, o número do empenho que deverá ser utilizado na chamada seguinte, <code>SolicitacaoOlpWS</code>.<br>
                 <strong>✅ Retorno Esperado:</strong> Mensagem <code>41040</code> <em>'Solicitação Empenho gerado com sucesso!'</em>.
               </p>""",
    "stage3": """<h4>Etapa 3: Liquidação da Despesa (SolicitacaoOlpWS)</h4>
                  <h5><strong>Método:</strong> POST</h5>
                  <h5><strong>Header:</strong> Content-Type: text/xml; charset=utf-8</h5>
                  <h5 style="margin-bottom: 10px;"><strong>Endpoint:</strong> <a href="https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoOlpWS" target="_blank" rel="noopener noreferrer" style="color: blue; text-decoration: underline;">https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoOlpWS</a></h5>
               <p>
                 <strong>🎯 Objetivo:</strong> Emissão da Ordem de Liquidação e Pagamento (OLP), atestando o cumprimento da obrigação e calculando eventuais retenções tributárias.<br>
                 <strong>⚠️ Cuidados:</strong><br>
                 • <strong>Regionalização da Despesa (Erro <code>49762</code>):</strong> Em naturezas de despesa que exigem regionalização, o bloco <code>&lt;regionalizacaoDespesaOlpRequestList&gt;</code> com <code>&lt;codigoMunicipio&gt;</code> de 7 dígitos (padrão IBGE) é obrigatório, nas demais despesas deve ser omitido.<br>
                 • <strong>Retenções Tributárias (Erro <code>39148</code>):</strong> O valor líquido deve fechar matematicamente com rigor absoluto: <code>&lt;valorBrutoOlp&gt; - &lt;valorRetencaoOlp&gt; = &lt;valorLiquido&gt;</code> (ex.: INSS tipo <code>14</code> e ISSQN tipo <code>13</code>).<br>
                 <strong>🔗 Herança de dados:</strong> Recebe, na tag <code>&lt;numeroDocumentoEmpenho&gt;</code>, o número do empenho gerado pela operação anterior, <code>SolicitacaoEmpenhoWS</code>, e retorna, na tag <code>&lt;numeroDocumento&gt;</code>, o número da OLP que deverá ser utilizado na chamada seguinte, <code>SolicOrdemPagamentoBancariaWS</code>.<br>
                 <strong>✅ Retorno Esperado:</strong> Mensagem <code>41040</code> <em>'Solicitação de OLP gerada com sucesso!'</em>.
               </p>""",
    "stage4": """<h4>Etapa 4: Autorização Bancária de Pagamento (SolicOrdemPagamentoBancariaWS)</h4>
                  <h5><strong>Método:</strong> POST</h5>
                  <h5><strong>Header:</strong> Content-Type: text/xml; charset=utf-8</h5>
                  <h5 style="margin-bottom: 10px;"><strong>Endpoint:</strong> <a href="https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/SolicOrdemPagamentoBancariaWS" target="_blank" rel="noopener noreferrer" style="color: blue; text-decoration: underline;">https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/SolicOrdemPagamentoBancariaWS</a></h5>
               <p>
                 <strong>🎯 Objetivo:</strong> Emissão da Ordem de Pagamento Bancária (OBM) para autorização e disparo do crédito bancário ao favorecido.<br>
                 <strong>🆕 IRRF:</strong> a retenção de Imposto de Renda é inscrita na própria OP, dentro do item de pagamento, e muda a regra dos valores. Veja o exemplo real em <strong>IRRF, Manutenção e Cancelamento → OP com IRRF</strong>.<br>
                 <strong>⚠️ Cuidados:</strong><br>
                 • <strong>INSS e ISSQN não vão na OP:</strong> ficam retidos na OLP; a OP sem IRRF paga o líquido e não leva <code>&lt;retencaoList&gt;</code> nem <code>&lt;valorTotalRetencoes&gt;</code>.<br>
                 • <code>&lt;numeroArquivo&gt;1&lt;/numeroArquivo&gt;</code>: controle de remessa do arquivo bancário.<br>
                 • <code>&lt;finalidadePagamento&gt;</code>: obrigatória (erro <code>38727</code>) com Conta Específica ou código de barras (forma <code>002</code>); o GRP aceitou qualquer texto (ex.: <code>01</code>, <code>Não se aplica</code>). Com Conta Única e forma <code>001</code> pode ser omitida.<br>
                 • <strong>Dígito Verificador da Agência (Erro <code>40515</code>):</strong> Bancos digitais sem DV de agência (Inter <code>077</code>, Nubank <code>260</code>, C6 <code>336</code>) exigem a <strong>omissão completa</strong> da tag <code>&lt;dvAgenciaACreditar&gt;</code>.<br>
                 • <strong>Dígito Verificador da Conta:</strong> Contas sem DV exigem obrigatoriamente <code>&lt;dvContaACreditar&gt;0&lt;/dvContaACreditar&gt;</code> (a omissão da tag causa erro de ponteiro nulo no backend Java).<br>
                 • <strong>Conta Única (1) vs Específica (2):</strong> <code>&lt;tipoContaADebitar&gt;1&lt;/tipoContaADebitar&gt;</code> (Tesouro) dispensa dados bancários a debitar. Para convênios/projetos, use tipo <code>2</code> com banco/agência/conta a debitar e <code>&lt;finalidadePagamento&gt;</code>.<br>
                 • <strong>Conta Poupança:</strong> se o crédito for em poupança (tipo <code>2</code>), o banco de crédito deve ser o mesmo da conta de débito.<br>
                 • <strong>Sistema de origem:</strong> use o mesmo <code>&lt;codigoSistemaOrigem&gt;</code> da OLP (erro <code>62229</code>). O Portal de Compras (sistema <code>2</code>) não gera OP pela API.<br>
                 <strong>🔗 Herança de dados:</strong> Recebe, na tag <code>&lt;anoNumeroDaOlpEEmpenho&gt;</code>, o número da OLP gerado pela operação anterior, <code>SolicitacaoOlpWS</code>, no formato <code>AAAA/Número da OLP</code> (ex.: <code>2026/41998</code>).<br>
                 <strong>✅ Retorno Esperado:</strong> Mensagem <code>51424</code> <em>'Solicitação de ordem de pagamento Bancária gerada com sucesso!'</em>. Guarde o <code>numeroSolicitacao</code> (pesquisável no GRP) e o <code>numeroDocumento</code> (usado no cancelamento).
               </p>"""
}


class ScenarioManager:
    """Gerenciador do banco de dados das 64 chamadas combinatórias."""

    def __init__(self, db_path: str = DATABASE_JSON_PATH):
        self.db_path = db_path
        self._scenarios = []
        self._scenarios_by_id = {}
        self._loaded = False

    def load(self, force_reload: bool = False) -> list:
        """Carrega a base unificada de chamadas."""
        if self._loaded and not force_reload:
            return self._scenarios

        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Banco de dados de chamadas não encontrado em: {self.db_path}")

        with open(self.db_path, "r", encoding="utf-8") as f:
            scenarios = json.load(f)

        # Normalização de chaves para robustez
        for s in scenarios:
            s_id = s.get("identificador") or s.get("id")
            s["identificador"] = s_id
            s["id"] = s_id
            s["status_homologacao"] = s.get("status_homologacao") or s.get("status", "TESTADO & HOMOLOGADO")
            g_mae = str(s.get("grupo_mae", "")).replace("GRUPO MÃE ", "").replace("GRUPO MÃE", "").strip()
            s["grupo_mae"] = g_mae

        self._scenarios = scenarios
        self._scenarios_by_id = {s["identificador"]: s for s in scenarios}
        self._loaded = True
        return self._scenarios

    def get_all_scenarios(self) -> list:
        """Retorna a lista de todos os 64 cenários."""
        if not self._loaded:
            self.load()
        return self._scenarios

    def get_scenario(self, scenario_id: str) -> dict:
        """Busca um cenário pelo identificador (ex.: 'Chamada-01' ou '01')."""
        if not self._loaded:
            self.load()
        if not scenario_id.startswith("Chamada-") and scenario_id.isdigit():
            scenario_id = f"Chamada-{int(scenario_id):02d}"
        return self._scenarios_by_id.get(scenario_id)

    def find_scenario(self, cliente: str, regionalizacao: str, conta_debito: str, conta_credito: str, retencao: str) -> dict:
        """Localiza o cenário a partir das 5 variáveis combinatórias."""
        if not self._loaded:
            self.load()
        for s in self._scenarios:
            if (s.get("cliente") == cliente and
                s.get("regionalizacao") == regionalizacao and
                s.get("conta_debito") == conta_debito and
                s.get("conta_credito") == conta_credito and
                s.get("retencao") == retencao):
                return s
        return None

    def get_manutencao(self) -> dict:
        """Retorna as fixtures de manutenção."""
        return MANUTENCAO_DATA

    def get_stage_guides(self) -> dict:
        """Retorna os guias e diretrizes das 4 etapas da Cadeia Integrada."""
        return STAGE_GUIDES

    def resolve_scenario_params(self, scenario_id: str, overrides: dict = None) -> dict:
        """
        Deriva o dicionário completo de parâmetros de execução a partir do cenário
        e aplica eventuais overrides fornecidos pela linha de comando.
        """
        if not self._loaded:
            self.load()

        scenario = self.get_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Cenário '{scenario_id}' não encontrado na base de dados.")

        cliente = scenario.get("cliente", "CPF")
        regionalizacao = scenario.get("regionalizacao", "Sem Regionalização")
        conta_debito = scenario.get("conta_debito", "1 - Conta Única (Tesouro)")
        conta_credito = scenario.get("conta_credito", "1 - Conta Corrente")
        retencao = scenario.get("retencao", "Sem Retenção")

        # Dados orçamentários padrão (SEF/NFM)
        p = {
            "scenario_id": scenario.get("identificador"),
            "ano_exercicio": "2026",
            "orgao_executor": "10190",
            "uo": "10191",
            "ua": "1019080124",
            "codigo_processo": 18,
            "codigo_sistema_solicitante": 51,
            "codigo_sistema_origem": 51,
            "cpf_ordenador": "00000000191",
            "cpf_operador": "00000000191",
            "tipo_empenho": "ORDINARIO",
            "justificativa": f"EXECUCAO DO CENARIO {scenario.get('identificador')} - {retencao.upper()}",
            "funcao": "04",
            "subfuncao": "129",
            "programa": "045",
            "projeto_atividade": "4081",
            "subprojeto": "0001",
            "categoria_eco": "3",
            "grupo_despesa": "3",
            "modalidade": "90",
            "elemento_grp": "031",
            "item_grp": "005",
            "iag": "00",
            "grupo_fonte": "11",
            "fonte_recurso": "500010",
            "ipu": "01",
            "cc": "0243",
            "codigo_forma_pagamento": "001",
            "data_programada_pagamento": "2026-08-20T00:00:00",
            "finalidade_pagamento": "01"
        }

        # 1. Favorecido
        if "CNPJ" in cliente:
            p["credor_cpf_cnpj"] = "00000000000191"
            p["credor_classificacao"] = "BENEFICIÁRIOS DIVERSOS"
        else:
            p["credor_cpf_cnpj"] = "00000000272"
            p["credor_classificacao"] = "BENEFICIÁRIOS DIVERSOS"

        # 2. Regionalização
        if "Com Regionalização" in regionalizacao:
            p["exige_regionalizacao"] = True
            p["codigo_municipio"] = "3106200"
        else:
            p["exige_regionalizacao"] = False

        # 3. Conta Débito
        if "2" in conta_debito or "Específica" in conta_debito:
            p["tipo_conta_a_debitar"] = 2
            p["op_cod_banco_deb"] = "001"
            p["op_ag_deb"] = "1615"
            p["op_dv_ag_deb"] = "2"
            p["op_conta_deb"] = "90004"
            p["op_dv_conta_deb"] = "6"
        else:
            p["tipo_conta_a_debitar"] = 1

        # 4. Conta Crédito
        if "2" in conta_credito or "Poupança" in conta_credito:
            p["tipo_conta_a_creditar"] = 2
            p["op_cod_banco_cred"] = "001"
            p["op_ag_cred"] = "9012"
            p["op_dv_ag_cred"] = "6"
            p["op_conta_cred"] = "90006"
            p["op_dv_conta_cred"] = "3"
        else:
            p["tipo_conta_a_creditar"] = 1
            p["op_cod_banco_cred"] = "001"
            p["op_ag_cred"] = "9012"
            p["op_dv_ag_cred"] = "6"
            p["op_conta_cred"] = "90006"
            p["op_dv_conta_cred"] = "3"

        # 5. Retenções Tributárias
        p["valor"] = "1.00"
        if "INSS + ISSQN" in retencao:
            p["ha_retencao"] = True
            p["retencao_inss"] = "0.11"
            p["retencao_issqn"] = "0.05"
            p["valor_retido"] = "0.16"
            p["valor_liquido"] = "0.84"
            p["retencoes_list_olp"] = [
                {"codigo_tipo_retencao": "14", "valor_retencao": "0.11", "credor_retencao": "29979036000140"},
                {"codigo_tipo_retencao": "13", "valor_retencao": "0.05", "credor_retencao": "18715383000140"}
            ]
            p["retencoes_list_op"] = []
        elif "INSS" in retencao:
            p["ha_retencao"] = True
            p["retencao_inss"] = "0.11"
            p["valor_retido"] = "0.11"
            p["valor_liquido"] = "0.89"
            p["retencoes_list_olp"] = [
                {"codigo_tipo_retencao": "14", "valor_retencao": "0.11", "credor_retencao": "29979036000140"}
            ]
            p["retencoes_list_op"] = []
        elif "ISSQN" in retencao:
            p["ha_retencao"] = True
            p["retencao_issqn"] = "0.05"
            p["valor_retido"] = "0.05"
            p["valor_liquido"] = "0.95"
            p["retencoes_list_olp"] = [
                {"codigo_tipo_retencao": "13", "valor_retencao": "0.05", "credor_retencao": "18715383000140"}
            ]
            p["retencoes_list_op"] = []
        else:
            p["ha_retencao"] = False
            p["valor_retido"] = "0.00"
            p["valor_liquido"] = "1.00"
            p["retencoes_list_olp"] = []
            p["retencoes_list_op"] = []

        # 6. Aplicação de Overrides Dinâmicos
        if overrides:
            p.update(overrides)

            # Recálculo de valores fiscobancários se necessário
            if p.get("ha_retencao"):
                try:
                    v_bruto = float(p.get("valor", "1.00"))
                    v_inss = float(p.get("retencao_inss", "0.00")) if "retencao_inss" in p else (0.11 if "INSS" in retencao else 0.0)
                    v_issqn = float(p.get("retencao_issqn", "0.00")) if "retencao_issqn" in p else (0.05 if "ISSQN" in retencao else 0.0)
                    v_tot_ret = v_inss + v_issqn
                    v_liq = v_bruto - v_tot_ret
                    p["valor_retido"] = f"{v_tot_ret:.2f}"
                    p["valor_liquido"] = f"{v_liq:.2f}"

                    # Atualiza as listas com os novos valores
                    r_olp = []
                    r_op = []
                    if v_inss > 0:
                        r_olp.append({"codigo_tipo_retencao": "14", "valor_retencao": f"{v_inss:.2f}", "credor_retencao": "29979036000140"})
                    if v_issqn > 0:
                        r_olp.append({"codigo_tipo_retencao": "13", "valor_retencao": f"{v_issqn:.2f}", "credor_retencao": "18715383000140"})
                    p["retencoes_list_olp"] = r_olp
                    p["retencoes_list_op"] = r_op
                except Exception:
                    pass

        return p

    def list_summary(self) -> list:
        """Retorna sumário dos cenários para CLI."""
        if not self._loaded:
            self.load()
        return [
            {
                "id": s.get("identificador"),
                "cliente": s.get("cliente"),
                "regionalizacao": s.get("regionalizacao"),
                "conta_debito": s.get("conta_debito"),
                "conta_credito": s.get("conta_credito"),
                "retencao": s.get("retencao"),
                "grupo_mae": s.get("grupo_mae"),
                "status": s.get("status_homologacao")
            }
            for s in self._scenarios
        ]


# Instância singleton padrão
default_scenarios = ScenarioManager()
