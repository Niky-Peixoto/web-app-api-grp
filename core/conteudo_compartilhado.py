# -*- coding: utf-8 -*-
"""
Conteúdo compartilhado da documentação (core.conteudo_compartilhado)

Os dois documentos da API andam juntos e não podem se contradizer:
- manual_api_grp_llm.md (gerado por core.markdown_generator);
- docs/DOCUMENTACAO_API_GRP_TESTES_PRIORIDADE_ALTA.md (escrito à mão).

Os trechos comuns aos dois ficam aqui, uma vez só. O manual os insere ao ser gerado; na DOCUMENTACAO eles ficam entre
os marcadores <!-- BLOCO:nome:INICIO --> e <!-- BLOCO:nome:FIM -->, reescritos por `atualizar_documentacao()` a cada
`python cli.py build`. Para mudar um desses trechos, mude aqui, nunca direto num dos documentos.
"""

import os
import re

from core.config import (
    BASE_DIR,
    VERSAO_DOCUMENTACAO,
    DATA_VERSAO_DOCUMENTACAO,
    URL_GERAR_PROCESSO,
    URL_EMPENHO,
    URL_OLP,
    URL_OP_BANCARIA,
    URL_REFORCO_EMPENHO,
    URL_ANULACAO_EMPENHO,
    URL_ANULACAO_OLP,
    URL_CANCELAMENTO_OP,
)
from core.sanitizer import sanitize_xml_text

DOCUMENTACAO_PATH = os.path.join(BASE_DIR, "docs", "DOCUMENTACAO_API_GRP_TESTES_PRIORIDADE_ALTA.md")


# =============================================================================
# Versão e histórico
# =============================================================================

def bloco_versao() -> str:
    return (f"> **Versão {VERSAO_DOCUMENTACAO} — {DATA_VERSAO_DOCUMENTACAO}.** Este documento e o seu par "
            "(`manual_api_grp_llm.md` / `docs/DOCUMENTACAO_API_GRP_TESTES_PRIORIDADE_ALTA.md`) têm a mesma versão e "
            "não se contradizem: os trechos comuns são gerados de uma fonte só. O histórico de versões está no fim.")


HISTORICO = [
    ("2.1", "26/10/2026", [
        "Árvore interativa refeita: monta cada chamada com os dados de quem usa, confere as regras aprendidas nos testes "
        "reais (as mesmas do Assistente GRP), envia ao GRP pela própria página ou por comando pronto e explica a "
        "resposta. Os 64 cenários de 23/09/2026 deixam de ser a base da árvore e ficam como histórico.",
        "Nova seção *Como reproduzir os testes* nos dois documentos.",
        "Divergência D3 resolvida: o `37144` também aparece com *saldo contábil insuficiente* (caso real de 08/10/2026).",
        "`numeroRequisicao` montado com data e hora (AAMMDDhhmmss) + dígitos sorteados: 15 dígitos na OP (aceito em "
        "27/10/2026) e 13 nos demais serviços; 17 a 18 dígitos recusados. Barra (`/`) na justificativa da OP quebra a "
        "chamada.",
        "Textos de rede valem para todos os órgãos: rede do Governo ou VPN.",
        "Auditoria de 26/10/2026: exemplos de envio no formato do contrato atual (os enviados em formato antigo "
        "foram ajustados, com os mesmos valores); dicionário com o tipo de cada tag lido do contrato, por serviço; campos fora do "
        "contrato separados; orientação do credor não cadastrado corrigida; `numeroRequisicao` sem "
        "repetição e resultado indeterminado no tempo esgotado; CPFs e contas reais retirados das fontes.",
        "Ciclo da despesa: não é preciso fazer todas as etapas pela API; documentos registrados pela tela do GRP "
        "podem continuar pela API (exceto os do Portal de Compras).",
        "Árvore: pré-requisitos e operações de manutenção com explicação completa (*Leia mais*).",
    ]),
    ("2.0", "26/10/2026", [
        "Retenção de Imposto de Renda (IRRF) na OP bancária: formato aceito na produção desde 19/10/2026, com o envio e a resposta reais (solicitação 130905).",
        "INSS e ISSQN só na OLP; a `retencaoList` da OP saiu do contrato novo.",
        "Matriz com os 8 serviços (incluídos anulação de valores na OLP e cancelamento de OP no manual), endereços "
        "com `www` e o script `scripts/baixar_contratos_wsdl.py` para baixar e conferir os contratos.",
        "Regra do sistema de origem (mesmo sistema em todas as etapas; Portal de Compras não paga pela API).",
        "Tabela única de erros e tratamentos, com as mensagens observadas em chamadas reais.",
        "Exemplos de envio e resposta por cenário.",
        "Correções: ISSQN na OLP é o tipo `13`; `codigoFormaPagamento` `002` é código de barras; "
        "`finalidadePagamento` aceita texto e só é exigida com conta específica ou código de barras; zeros à "
        "esquerda são opcionais nos códigos numéricos da dotação.",
        "Dicionário de tags: 15 tags novas (IRRF, código de barras, anulação de valores na OLP e cancelamento de OP), "
        "passando de 123 para 138; textos corrigidos de forma de pagamento, finalidade, retenções e zeros à esquerda.",
        "Contratos WSDL da produção e do desenvolvimento baixados em 26/10/2026 (idênticos; o `?wsdl` da produção voltou a responder): estrutura do reforço e da anulação de empenho confirmada (divergências D1 e D2 resolvidas; modelos `manut_*.xml.j2` corrigidos).",
        "Lista de divergências ainda em verificação.",
    ]),
    ("1.x", "06/2026 a 09/2026", [
        "DOCUMENTACAO: 8 serviços validados com o sistema 51 (casos de 28/05 a 16/06/2026).",
        "Manual: 6 serviços e matriz de 64 cenários homologados (base de 23/09/2026).",
    ]),
]


def bloco_historico() -> str:
    linhas = ["| Versão | Data | Mudanças |", "| :--- | :--- | :--- |"]
    for versao, data, itens in HISTORICO:
        linhas.append(f"| {versao} | {data} | " + "<br>".join(f"• {i}" for i in itens) + " |")
    return "\n".join(linhas)


# =============================================================================
# Endpoints
# =============================================================================

SERVICOS = [
    ("Abertura de processo", "GerarNumeroProcessoGrpWS", "gerarNumeroProcessoGrp", "—", URL_GERAR_PROCESSO,
     "Validado"),
    ("Empenho", "SolicitacaoEmpenhoWS", "gerarSolicitacaoEmpenho", "EMPOLP1.1", URL_EMPENHO, "Validado"),
    ("Reforço de empenho", "SolicitacaoReforcoDeEmpenhoWS", "gerarSolicitacaoReforcoEmpenho", "EMPOLP1.2",
     URL_REFORCO_EMPENHO, "Validado em 16/06/2026; estrutura confirmada pelo contrato de 26/10/2026"),
    ("Anulação de empenho", "SolicitacaoAnulacaoEmpenhoWS", "gerarSolicitacaoAnulacaoSaldoEmpenho", "EMPOLP1.3",
     URL_ANULACAO_EMPENHO, "Validado em 15/06/2026; estrutura confirmada pelo contrato de 26/10/2026"),
    ("Liquidação (OLP)", "SolicitacaoOlpWS", "solicitarOLP", "EMPOLP2.1", URL_OLP, "Validado"),
    ("Anulação de valores na OLP", "SolicitacaoAnulacaoValoresNaOlpWS", "solicitarAnulacaoValoresNaOLP", "EMPOLP2.2",
     URL_ANULACAO_OLP, "Validado em 15/06/2026"),
    ("OP bancária", "SolicOrdemPagamentoBancariaWS", "gerarSolicOrdemPagamentoBancaria", "PGBANESC1.1.1",
     URL_OP_BANCARIA, "Validado; contrato novo (IRRF no item) na produção desde 19/10/2026"),
    ("Cancelamento de OP bancária", "CancelamentoOrdemPagamentoBancariaWS", "cancelarOrdemPagamentoBancaria",
     "PGBANESC1.2.1", URL_CANCELAMENTO_OP, "Validado em 15/06 e 13/10/2026"),
]


def bloco_endpoints() -> str:
    linhas = ["| Etapa / Operação | Serviço | Operação SOAP | `identificadorProcessoExecucao` | Endpoint (produção) | Situação |",
              "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for nome, servico, operacao, ident, url, situacao in SERVICOS:
        ident_md = f"`{ident}`" if ident != "—" else ident
        linhas.append(f"| {nome} | `{servico}` | `{operacao}` | {ident_md} | `{url}` | {situacao} |")
    linhas += [
        "",
        "* **Produção:** `https://www.grp.servicos.mg.gov.br/serviceBus/...`. Sem o `www`, o servidor responde "
        "`301` para o endereço com `www`; se o cliente seguir o redirecionamento sozinho, o `POST` vira `GET` e o "
        "conteúdo se perde. Use o endereço com `www` ou reenvie o `POST` ao endereço do `Location`.",
        "* **Desenvolvimento (PRODEMGE):** `https://desenvolvimento.grp.servicos.mg.gov.br/serviceBus/...`. Publica os "
        "contratos (`?wsdl`) e recebe primeiro as mudanças de contrato (o IRRF no item apareceu lá em 14/10/2026). "
        "Não use para gerar documentos sem autorização da PRODEMGE: os dados são outros.",
        "* **Contratos WSDL:** conferidos em 26/10/2026 — produção e desenvolvimento publicam o contrato dos 8 serviços "
        "(HTTP 200), com os mesmos campos nos dois ambientes; cada contrato declara o próprio endereço (`www` na produção). "
        "Resumos em `contratos/producao/2026-10-26/RESUMO.md` e `contratos/desenvolvimento/2026-10-26/RESUMO.md`. Até "
        "16/10/2026 o `?wsdl` da produção redirecionava para `indisponivel.mg.gov.br`. Para baixar de novo e conferir os 8 endereços, rode na rede do Governo ou na VPN "
        "`python scripts/baixar_contratos_wsdl.py`: ele só faz `GET`, salva os arquivos em "
        "`contratos/<ambiente>/<data>/` e gera um `RESUMO.md` com a situação de cada endpoint e os campos de cada tipo.",
        "* **Rede:** o GRP só responde de dentro da rede do Governo de Minas ou pela VPN. Em algumas máquinas, a borda da PRODEMGE devolve a "
        "página de indisponibilidade para o TLS do Python (OpenSSL) e aceita o `curl.exe` do Windows; nesses casos, use "
        "o `curl.exe` como transporte (sem imitar navegador).",
        "* **Ambiente atual:** segundo a SEF (15/10/2026), a instalação do GRP em `www.grp.servicos` é de teste: as "
        "OPs geradas lá não seguem para os bancos.",
        "* **Fora da API para o sistema 51:** a consulta IS47588 (recuperar dados da execução da despesa) não aceita "
        "`codigoSistemaSolicitante` 51. Conferir OPs só pela tela de consulta do GRP, pelo Nº da solicitação.",
    ]
    return "\n".join(linhas)


# =============================================================================
# Regra do sistema de origem
# =============================================================================

def bloco_sistema_origem() -> str:
    return "\n".join([
        "* **Mesmo sistema em toda a cadeia:** processo, empenho, OLP, OP e as operações de manutenção de uma mesma "
        "execução devem usar o mesmo `codigoSistemaOrigem` (no processo, `codigoSistemaSolicitante`). Só o próprio "
        "GRP, pela interface web, opera documentos de qualquer origem.",
        "* **Documentos registrados pela tela do GRP** podem continuar pela API: não é preciso fazer todas as etapas "
        "pela API. Exemplo testado: OP enviada pela API sobre uma OLP registrada na tela do GRP.",
        "* **Evidência (15/10/2026):** uma OP enviada com sistema `2` (Portal de Compras) sobre uma OLP criada pelo "
        "sistema `51` voltou `62229` — *\"Documento não permitido, a solicitação deve ser registrada via NOTA MINEIRA\"*.",
        "* **Portal de Compras (sistema `2`):** é um sistema que só empenha e liquida. A OP de documentos do Portal de "
        "Compras é feita pela interface do GRP, inclusive quando a execução inteira começou do zero com o sistema `2`.",
        "* **Não troque de sistema por conta própria:** usar o código de outro sistema exige autorização da "
        "PRODEMGE/STE. O sistema `51` é a Nota Fiscal Mineira.",
    ])


# =============================================================================
# IRRF na OP bancária
# =============================================================================

EXEMPLO_OP_IRRF = """
<?xml version="1.0" encoding="UTF-8"?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/"
                   xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicOrdemPagamentoBancaria>
      <solicitacaoOrdemPagamentoBancaria>
        <numeroRequisicao>1324125311</numeroRequisicao>
        <identificadorProcessoExecucao>PGBANESC1.1.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <numeroArquivo>1</numeroArquivo>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080010</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <cpfCnpjCredor>02038232000164</cpfCnpjCredor>
        <classificacaoCredor>INSTITUIÇÃO FINANCEIRA</classificacaoCredor>
        <origemPagamento>OLP Diversos</origemPagamento>
        <cpfCnpjCredorOP>02038232000164</cpfCnpjCredorOP>
        <classificacaoCredorDaOP>INSTITUIÇÃO FINANCEIRA</classificacaoCredorDaOP>
        <tipoContaADebitar>1</tipoContaADebitar>
        <finalidadePagamento>Não se aplica</finalidadePagamento>
        <codigoFormaPagamento>001</codigoFormaPagamento>
        <tipoContaACreditar>1</tipoContaACreditar>
        <codigoBancoACreditar>756</codigoBancoACreditar>
        <codigoAgenciaACreditar>1</codigoAgenciaACreditar>
        <dvAgenciaACreditar></dvAgenciaACreditar>
        <codigoContaACreditar>90023</codigoContaACreditar>
        <dvContaACreditar>3</dvContaACreditar>
        <valorTotalAPagarDaOP>2.00</valorTotalAPagarDaOP>
        <valorTotalRetencoes>1.00</valorTotalRetencoes>
        <valorLiquidoPagamento>1.00</valorLiquidoPagamento>
        <dataProgramadaPagamento>2026-10-19T00:00:00</dataProgramadaPagamento>
        <justificativa>PAGAMENTO VIA API GRP - PARCELA 2725 DA OLP 57490</justificativa>
        <itemDePagamentoList>
          <ItemDePagamento>
            <itemDePagamento>1</itemDePagamento>
            <anoNumeroDaOlpEEmpenho>2026/57490</anoNumeroDaOlpEEmpenho>
            <valorAPagar>2.00</valorAPagar>
            <valorTotalAPagar>2.00</valorTotalAPagar>
            <valorLiquido>1.00</valorLiquido>
            <retencao>
              <tipoRetencao>10</tipoRetencao>
              <valorRetencao>1.00</valorRetencao>
              <codigoReceita>090140</codigoReceita>
              <cpfCnpjCredorRetencao>18715615000160</cpfCnpjCredorRetencao>
            </retencao>
          </ItemDePagamento>
        </itemDePagamentoList>
      </solicitacaoOrdemPagamentoBancaria>
    </grp:gerarSolicOrdemPagamentoBancaria>
  </soap-env:Body>
</soap-env:Envelope>
"""

RESPOSTA_OP_IRRF = """
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:gerarSolicOrdemPagamentoBancariaResponse xmlns:ns2="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1324125311</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacao>130905</numeroSolicitacao>
        <situacaoSolicitacao>Concluída</situacaoSolicitacao>
        <numeroDocumento>117423</numeroDocumento>
        <situacaoDocumento>REGISTRADO_PENDENTE_ASSINATURA</situacaoDocumento>
        <urlDocumento>https://apigw.mgapi.prodemge.gov.br/t/grp-portal.mg.gov.br/empolp-rest-visualizardocumento/v1/documento/MASCARADO/00000000-0000-0000-0000-000000000000</urlDocumento>
        <dataSolicitacao>2026-10-19T10:17:11.379-03:00</dataSolicitacao>
        <mensagens>
          <mensagem>
            <codigo>51424</codigo>
            <descricao>Solicitação de ordem de pagamento Bancária gerada com sucesso!</descricao>
          </mensagem>
        </mensagens>
      </return>
    </ns2:gerarSolicOrdemPagamentoBancariaResponse>
  </soap:Body>
</soap:Envelope>
"""


def bloco_irrf() -> str:
    return "\n".join([
        "> **Situação (26/10/2026):** formato **aceito na produção** (`www.grp.servicos.mg.gov.br`) desde **19/10/2026**, "
        "quando a PRODEMGE publicou o contrato novo da OP. Primeira OP com IRRF aceita: solicitação `130905`, documento "
        "`117423`, mensagem `51424`. Antes dessa data, a produção recusava o bloco `<retencao>` (erro `Unmarshalling "
        "Error` na tabela de erros).",
        "",
        "* **INSS e ISSQN não vão na OP:** essas retenções são feitas só na OLP. A OP sem IRRF não leva `<retencaoList>` "
        "nem `<valorTotalRetencoes>` e informa o líquido em `<valorTotalAPagarDaOP>`, `<valorLiquidoPagamento>` e nos "
        "valores do item. A `<retencaoList>` no nível da OP nunca descontou nada (o GRP a ignorava) e saiu do contrato "
        "novo.",
        "* **Onde vai o IRRF:** um bloco `<retencao>` **dentro** do `<ItemDePagamento>`, logo depois de `<valorLiquido>`.",
        "* **Campos do bloco `<retencao>`** (nesta ordem):",
        "  - `<tipoRetencao>`: `10` (IRRF). Os códigos de retenção da OP não são os mesmos da OLP.",
        "  - `<valorRetencao>`: valor do IRRF, com ponto decimal e 2 casas (ex.: `1.00`). O GRP não calcula a alíquota: "
        "o integrador informa o valor.",
        "  - `<codigoReceita>`: `090140` no exemplo da PRODEMGE.",
        "  - `<cpfCnpjCredorRetencao>`: `18715615000160` no exemplo da PRODEMGE (credor da retenção), só dígitos.",
        "* **Regra dos valores (diferente da OP sem IRRF):** o total da OP e o valor a pagar do item vão **antes** do "
        "IRRF; o líquido vai **sem** o IRRF.",
        "",
        "| Tag | Valor | Exemplo (valor antes do IRRF 2,00; IRRF 1,00) |",
        "| :--- | :--- | :--- |",
        "| `<valorTotalAPagarDaOP>` | valor antes do IRRF | `2.00` |",
        "| `<valorTotalRetencoes>` | valor do IRRF (logo após `<valorTotalAPagarDaOP>`) | `1.00` |",
        "| `<valorLiquidoPagamento>` | valor antes do IRRF − IRRF | `1.00` |",
        "| `<valorAPagar>` e `<valorTotalAPagar>` (item) | valor antes do IRRF | `2.00` |",
        "| `<valorLiquido>` (item) | valor antes do IRRF − IRRF | `1.00` |",
        "| `<valorRetencao>` (dentro de `<retencao>`) | valor do IRRF | `1.00` |",
        "",
        "* **Saldo da OLP:** o que sai do saldo é o valor antes do IRRF (o INSS e o ISSQN já ficaram retidos na OLP). "
        "Ou seja: `valor antes do IRRF = valor bruto − INSS − ISSQN`.",
        "* **Formatos que não funcionam:** IRRF na `<retencaoList>` com todos os valores líquidos → aceito, mas nada é "
        "retido; IRRF na `<retencaoList>` com valores antes do IRRF → erro `123`.",
        "* **Pontos ainda em aberto com a PRODEMGE:**",
        "  - O código de receita `090140` é o do exemplo da PRODEMGE, feito com credor **pessoa física**. Falta "
        "confirmar o código para credor **pessoa jurídica**.",
        "  - Falta conferir no documento gerado no GRP se a retenção ficou inscrita como esperado (a OP foi aceita, mas a "
        "inscrição ainda não foi verificada na tela).",
        "* **Contrato novo da OP** (visto no desenvolvimento em 14/10/2026; confirmado no contrato da produção em "
        "26/10/2026): além de `<retencao>`, o item "
        "passa a ter `<valorDesconto>`, `<encargoFinanceiro>` e `<compensacao>`; a guia GPS saiu (ficaram `darf` e "
        "`guiaPrevidenciaEstadualGpe`). Segundo a PRODEMGE, inscrição de retenção, desconto e encargos devem ficar "
        "dentro do item. Só o IRRF foi testado na produção até agora.",
        "",
        "**Caso real: OP com IRRF aceita em 19/10/2026** (solicitação `130905`, OLP `2026/57490`). CPFs e o "
        "identificador do documento na URL mascarados; demais dados como foram enviados.",
        "",
        "Envio:",
        "",
        "```xml",
        EXEMPLO_OP_IRRF.strip(),
        "```",
        "",
        "Resposta (quebras de linha acrescentadas para leitura):",
        "",
        "```xml",
        RESPOSTA_OP_IRRF.strip(),
        "```",
        "",
        "* **Observações do caso real:** a `finalidadePagamento` foi enviada (`Não se aplica`) mesmo com Conta Única e "
        "forma 001, e foi aceita; o banco `756` não tem DV de agência e a tag `<dvAgenciaACreditar>` foi vazia; a "
        "`urlDocumento` agora vem pelo gateway `apigw.mgapi.prodemge.gov.br` e traz o CPF do operador codificado "
        "(Base64) no caminho — mascare antes de publicar.",
    ])


# =============================================================================
# Contrato atual (RESUMO.md baixado em 26/10/2026, ambiente de desenvolvimento)
# =============================================================================

def bloco_contratos() -> str:
    return "\n".join([
        "Fonte: contratos WSDL da **produção** e do desenvolvimento baixados em 26/10/2026 com "
        "`scripts/baixar_contratos_wsdl.py` — os dois são idênticos (resumos completos em `contratos/producao/2026-10-26/` e "
        "`contratos/desenvolvimento/2026-10-26/`). O contrato diz o que o servidor aceita ler; regras de negócio (o que o "
        "GRP valida depois) só aparecem em chamada real.",
        "",
        "* **Os 8 serviços** responderam com contrato (HTTP 200) e as operações documentadas.",
        "* **OP bancária — item de pagamento (`itemDePagamentoSolicOrdemRequest`):** `itemDePagamento`, `valorAPagar`, "
        "`valorTotalAPagar` e `valorLiquido` obrigatórios; `retencao`, `encargoFinanceiro` e `compensacao` aparecem **no "
        "máximo uma vez** por item; também `valorDesconto`, `codigoReceita`, `anoNumeroDaOp`, `anoNumeroDoEmpenho`, "
        "`notaFiscal`, `tipoDiaria` e `tipoDepositoVinculado`.",
        "* **OP bancária — bloco `retencao` (`retencaoOrdemPagamentoRequest`):** `tipoRetencao` (int), `valorRetencao`, "
        "`codigoReceita`, `cpfCnpjCredorRetencao` e cinco campos opcionais ainda não testados, ligados ao IR: "
        "`valorRendimentoTributavel`, `valorContribuicaoPrevidenciaSocial`, `valorTituloPensaoAlimenticia`, "
        "`qtdDependentesIR` e `valorRendimentosIsentos`.",
        "* **OP bancária — nível da OP:** não há `retencaoList` nem `guiaPrevidenciaSocialGps`; há `valorTotalRetencoes`, "
        "`valorDesconto`, `darf`, `guiaPrevidenciaEstadualGpe`, `codigoBarras`, `finalidadePagamento`, os campos da OP de "
        "retenção (`tipoDeRetencao`, `contribuinte`, `mesAnoDeCompetencia`, `codigoDeReceita`) e os de instrumento jurídico "
        "(`instrumentoJuridico`, `numeroInstrumentoJuridicoEntrada` e variantes financiado/financiador).",
        "* **OLP — retenção (`retencaoOlpRequest`):** `tipoRetencao` (int), `valorRetencao`, `cpfCapfCredorRetencao`, "
        "`cnpJCredorRetencao`, competência, `dataPagamentoRetencao`, `codigoReceita` e `codigoUoBeneficiariaRetencao`. A "
        "resposta da OLP devolve, por retenção, `numeroUnicoRetencao` e `cpfCnpjContribuinte`.",
        "* **Empenho:** além dos instrumentos de entrada, financiado, financiador e **saída** (número, tipo e ano), "
        "aparecem `indicadorAntecipacaoPagamento` e `transferenciaVoluntaria`.",
        "* **Tipos numéricos:** a maior parte dos códigos da dotação é `xs:long` (por isso os zeros à esquerda são "
        "opcionais); `codigoElementoDespesa`, `codigoItem` e `codigoUnidadeOrcamentaria` são texto e mantêm os zeros.",
    ])


# =============================================================================
# Casos reais de anulação de valores na OLP e de cancelamento de OP (DOCUMENTACAO, seções 12 e 13). Os retornos foram
# registrados só com os campos do <return>, por isso aparecem em JSON.
ANULACAO_OLP_REQ = """
<?xml version="1.0" encoding="UTF-8"?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/"
                   xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:solicitarAnulacaoValoresNaOLP>
      <solicitarAnulacaoValoresNaOLP>
        <numeroRequisicao>1511184693</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP2.2</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroOlp>22606</numeroOlp>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <valorLiquidoAnulado>500.00</valorLiquidoAnulado>
        <valorTotalAnulado>500.00</valorTotalAnulado>
        <justificativa>TESTE ANULACAO OLP 22606</justificativa>
      </solicitarAnulacaoValoresNaOLP>
    </grp:solicitarAnulacaoValoresNaOLP>
  </soap-env:Body>
</soap-env:Envelope>
"""

ANULACAO_OLP_RES = """
{
  "numeroRequisicao": "1511184693",
  "codigoSistemaOrigem": "51",
  "anoExercicioFinanceiro": "2026",
  "numeroSolicitacao": "122",
  "situacaoSolicitacao": "Encaminhada para análise",
  "numeroDocumento": null,
  "situacaoDocumento": null,
  "dataSolicitacao": "2026-06-15T11:18:52.771-03:00",
  "mensagens": [{"codigo": "41040", "descricao": "Solicitação 122 gerado com sucesso!"}]
}
"""

CANCELAMENTO_OP_REQ = """
<?xml version="1.0" encoding="UTF-8"?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/"
                   xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:cancelarOrdemPagamentoBancaria>
      <cancelamentoOrdemPagamentoBancaria>
        <numeroRequisicao>1602370114</numeroRequisicao>
        <exercicioFinanceiro>2026</exercicioFinanceiro>
        <identificadorProcessoExecucao>PGBANESC1.2.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <numeroDocumentoOrdemDePagamento>38536</numeroDocumentoOrdemDePagamento>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <justificativa>TESTE CANCELAMENTO OP 38536</justificativa>
      </cancelamentoOrdemPagamentoBancaria>
    </grp:cancelarOrdemPagamentoBancaria>
  </soap-env:Body>
</soap-env:Envelope>
"""

CANCELAMENTO_OP_RES = """
{
  "numeroRequisicao": "1602370114",
  "codigoSistemaOrigem": "51",
  "anoExercicioFinanceiro": "2026",
  "numeroSolicitacaoDeCancelamentoOP": "53",
  "situacaoSolicitacao": "Concluída",
  "dataHora": "2026-06-15T16:02:42.063-03:00",
  "mensagens": [{"codigo": "54533", "descricao": "Solicitação de cancelamento gerada com sucesso"}]
}
"""


# =============================================================================
# Erros e tratamentos
# =============================================================================

ERROS = [
    ("`41040`", "Empenho, OLP, manutenções", "Solicitação ... gerado(a) com sucesso!",
     "Sucesso. Nas manutenções a situação vem *Encaminhada para análise*, sem `numeroDocumento`.",
     "Guardar `numeroSolicitacao` e `numeroDocumento`; acompanhar a tramitação das manutenções."),
    ("`51424`", "OP bancária", "Solicitação de ordem de pagamento Bancária gerada com sucesso!",
     "Sucesso.", "Guardar `numeroSolicitacao` (é o número pesquisável na consulta de OPs) e `numeroDocumento` (usado no cancelamento)."),
    ("`54533`", "Cancelamento de OP", "Solicitação de cancelamento gerada com sucesso",
     "Sucesso.", "Guardar `numeroSolicitacaoDeCancelamentoOP`."),
    ("`30782`", "Empenho, OLP", "Requisição em formato inválido",
     "XML inválido, wrapper ou nome de tag errado.", "Conferir envelope, operação, wrappers e `CamelCase` das tags."),
    ("`44448`", "OP bancária", "Requisição em formato inválido",
     "Estrutura incompatível; visto com `origemPagamento` errado.", "Usar `OLP Diversos` e conferir a estrutura do item."),
    ("`25081`", "Empenho, OLP", "Campo obrigatório ausente",
     "Campo exigido pela parametrização. Ex. (15/10/2026): empenho pedindo `numeroInstrumentoJuridicoEntrada` e "
     "procedimento de contratação numa combinação grupo/fonte/IPU nunca usada pela UO.",
     "Conferir a parametrização do elemento-item e a combinação de dotação."),
    ("`38727`", "OP bancária", "O campo finalidadePagamento é de preenchimento obrigatório",
     "`finalidadePagamento` ausente com conta específica (`tipoContaADebitar` 2) ou código de barras (forma 002).",
     "Enviar a tag (o GRP aceitou qualquer texto, ex.: `Não se aplica`)."),
    ("`39148`", "OLP", "Divergência de valores de retenção",
     "`valorBrutoOlp − valorRetencaoOlp ≠ valorLiquido`.", "Fechar a conta com 2 casas decimais."),
    ("`49762`", "OLP", "Município de regionalização obrigatório",
     "Item exige regionalização.", "Enviar `regionalizacaoDespesaOlpRequestList` com `codigoMunicipio` IBGE de 7 dígitos."),
    ("`40515`", "OP bancária", "DV de agência inválido",
     "DV enviado para banco sem DV de agência.", "Omitir `dvAgenciaACreditar` (Inter `077`, Nubank `260`, C6 `336`)."),
    ("`85910`", "Empenho, OP", "... não cadastrado no GRP",
     "Valor que não existe no cadastro: credor sem cadastro, classificação sem acento na OP, número de instrumento "
     "jurídico inexistente.", "Usar a classificação exatamente como no cadastro (com acento) e números que existam no GRP."),
    ("`37144`", "OP bancária", "Varia: leia a `descricao`",
     "Código genérico. Mensagens observadas: (a) *Erro inesperado... getExigeInstrumentoJuridico() is null* — toda OLP "
     "de exercício anterior (restos a pagar) pela API; (b) *Não existe parametrização para o segmento 3 e empresa 138 "
     "para a classificação ...* — código de barras de arrecadação incompatível com o credor; (c) *Ocorreu um erro ao "
     "contabilizar bloqueio de saldo. Causa: O saldo atual da Conta contábil ... é insuficiente* — a OLP não tem saldo "
     "contábil para o valor da OP (caso real de 08/10/2026).",
     "(a) Pagar pela tela do GRP; caso aberto com a PRODEMGE. (b) Conferir o código de barras e o credor. "
     "(c) Conferir o saldo da OLP no GRP."),
    ("`45769`", "OP bancária", "O Banco não aceita transmissão para pagamento por código de Barras",
     "O banco do boleto não aceita (visto com boleto do banco `756`; banco `001` aceito).", "Pagar por outra forma."),
    ("`62229`", "OP bancária", "Documento não permitido, a solicitação deve ser registrada via NOTA MINEIRA",
     "Sistema de origem diferente do sistema que criou a OLP.", "Usar o mesmo sistema de origem da cadeia (ver regra do sistema de origem)."),
    ("`123`", "OP bancária", "O valor líquido informado (x) é menor que o valor calculado (y)",
     "OP com valores antes do IRRF, mas com o IRRF na `retencaoList` em vez do item.", "Usar o formato do IRRF no item."),
    ("`93285`", "OP bancária", "Valor líquido não pode ser negativo", "Cálculo do líquido errado.", "Recalcular `valorLiquidoPagamento`."),
    ("`48860`", "OP bancária", "Usuário não possui acesso a Unidade Administrativa ...",
     "Operador/ordenador sem acesso à UA informada.", "Conferir UA e perfis no GRP."),
    ("`0`", "Vários", "Erro inesperado. Causa: ...",
     "Regra de negócio. Ex.: *Ordenador de despesa não está autorizado para UO ..., UA ...* (ordenador sem "
     "autorização naquele exercício); *Tipo de Empenho não permite reforço* (reforço em empenho `ORDINARIO`).",
     "Ler a causa; conferir ordenador, exercício e tipo do empenho."),
    ("`HTTP 500` Unmarshalling", "OP bancária", "elemento inesperado (uri:\"\", local:\"retencao\")",
     "Servidor com o contrato antigo da OP (era a resposta da produção até 19/10/2026).", "Conferir o endereço (use `www`)."),
    ("`HTTP 500` Unmarshalling", "Vários", "For input string: \"\"",
     "Tag numérica enviada vazia ou com texto (ex.: `numeroInstrumentoJuridicoEntrada`).", "Omitir a tag ou enviar número."),
    ("Erro interno", "OP de retenção", "NullPointerException em `getContribuinte()`; `Parameter value [4] did not match "
     "expected type [java.lang.Integer]`; `Parametro de pesquisa 'numeroUnicoOlp' não encontrado`",
     "OP com `origemPagamento` *Retenção* (pagar INSS/ISSQN ao arrecadador): defeito do GRP no campo `tipoDeRetencao`.",
     "Ainda não é possível pela API (14/10/2026). Caso aberto com a PRODEMGE."),
    ("Erro contábil", "Empenho, OLP, OP", "Natureza item da despesa não possui parametrização contábil",
     "Elemento/item sem amarração contábil no exercício.", "Acionar a STE/SEF."),
    ("Bloqueio", "Vários", "... janela de cópia dos dados do armazém ...",
     "Bloqueio temporário de processamento (visto uma vez entre 23h55 e 0h30).", "Aguardar e repetir a mesma chamada."),
    ("`HTTP 301`", "Todos", "Moved Permanently", "Endereço sem `www`.", "Usar `www` ou reenviar o `POST` ao `Location`."),
]


def bloco_erros() -> str:
    linhas = ["| Código | Etapa | Mensagem do GRP | Causa | Tratamento |", "| :--- | :--- | :--- | :--- | :--- |"]
    for codigo, etapa, mensagem, causa, tratamento in ERROS:
        linhas.append(f"| {codigo} | {etapa} | *{mensagem}* | {causa} | {tratamento} |")
    linhas += ["", "> Uma resposta de sucesso não basta: confira também `situacaoSolicitacao`, `numeroDocumento` e "
                   "`situacaoDocumento`. Quando a chamada fica sem resposta (tempo esgotado), consulte o GRP pelo Nº da "
                   "solicitação antes de reenviar, para não gerar documento em dobro."]
    return "\n".join(linhas)


# =============================================================================
# Divergências em verificação
# =============================================================================

def bloco_divergencias() -> str:
    return "\n".join([
        "Pontos em que as versões anteriores dos dois documentos diziam coisas diferentes e que dependem de teste real. "
        "Esta lista vale para os dois documentos.",
        "",
        "| # | Assunto | Versão A | Versão B | Como verificar |",
        "| :--- | :--- | :--- | :--- | :--- |",
        "| D4 | Tipo de empenho no reforço | Só `ESTIMATIVO` testado; `ORDINARIO` recusado (DOCUMENTACAO). | `ESTIMATIVO` "
        "ou `GLOBAL` (manual v1, sem teste com `GLOBAL`). | Reforço num empenho `GLOBAL`. |",
        "",
        "**Resolvidas em 26/10/2026:**",
        "",
        "* **D3 — significado do `37144`:** as duas versões estavam certas. O `37144` é um código genérico (*Solicitação "
        "não registrada... Causa: ...*), e saldo contábil insuficiente é uma das causas: caso real de 08/10/2026, "
        "*O saldo atual da Conta contábil ... é insuficiente para o lançamento*. Leia sempre a causa (tabela de erros).",
        "* **D1 — reforço de empenho** (pelos contratos da produção e do desenvolvimento): os campos vão direto em `<solicitacaoReforcoEmpenho>` (`numeroEmpenho`, UO, órgão, "
        "UA, ordenador, operador, `valorReforco`, justificativa). O bloco `<reforcoDeEmpenhoComum>` da versão 1 do manual "
        "não existe no contrato.",
        "* **D2 — anulação de empenho** (pelos mesmos contratos): o elemento interno é `<gerarSolicitacaoAnulacaoSaldoEmpenho>`, com os campos "
        "direto. `<solicitacaoAnulacaoSaldoEmpenho>` e `<anulacaoSaldoEmpenhoComum>` não existem no contrato.",
    ])


# =============================================================================
# Como reproduzir os testes (árvore interativa)
# =============================================================================

def bloco_arvore() -> str:
    return "\n".join([
        "A **Árvore Interativa da API do GRP** (`arvore_interativa_grp.html`, um arquivo só, que abre em qualquer "
        "navegador e funciona sem internet) é a forma recomendada de reproduzir os testes descritos aqui. Para "
        "baixá-la: no GitHub, abra o arquivo `arvore_interativa_grp.html` e clique em *Download raw file*.",
        "",
        "* **Montar e testar:** a cadeia Processo → Empenho → OLP → OP (com IRRF) e as manutenções (cancelar OP, anular "
        "valores na OLP, reforçar e anular empenho). Os dados da execução são informados uma vez; cada etapa leva o "
        "número gerado para a seguinte. Os dados ficam só no navegador de quem usa.",
        "* **Conferência antes de enviar:** a página confere as regras desta documentação e os catálogos do GRP "
        "embutidos (elemento-item e sistema dono, centros de custo da UA, classificação orçamentária, combinações "
        "grupo/fonte/IPU). Os catálogos foram coletados nas datas indicadas e podem estar desatualizados: em caso de "
        "divergência, vale o cadastro do GRP, que pode ser consultado nas telas do sistema.",
        "* **Envio:** pela própria página, com um *ajudante de envio* que roda no computador de quem usa (PowerShell "
        "com o `curl.exe` do Windows; só aceita a página que o gerou e só fala com o GRP), ou por comandos prontos "
        "para PowerShell, curl, Python e Postman/SoapUI. O XML gerado é igual, byte a byte, ao do Assistente GRP "
        "(GRP-Tool), que gerou os casos reais.",
        "* **Resposta:** a página lê a resposta do GRP (XML ou JSON), diz se deu certo, o que fazer em caso de erro e "
        "mostra o caso real parecido.",
        "* **Casos reais, códigos de resposta, contrato e dicionário:** as mesmas informações desta documentação, "
        "com o envio e a resposta de cada caso (CPFs mascarados).",
        "",
        "Antes do primeiro envio: rede do Governo ou VPN, sistema de origem autorizado, ordenador com exceção de "
        "assinatura e autorizado na UO/UA, programação orçamentária e financeira, credor cadastrado e elemento-item "
        "liberado para o sistema (ver pré-requisitos).",
    ])


def bloco_regras_envio() -> str:
    return "\n".join([
        "* **`numeroRequisicao`:** um número novo por chamada, nunca reaproveitado (nem depois de uma falha). Formato "
        "recomendado: data e hora até os segundos (`AAMMDDhhmmss`) seguidas de dígitos sorteados. Na OP, 3 dígitos, "
        "15 no total (ex.: `261027113130482`): aceito em OP em 27/10/2026. Nos demais serviços, 1 dígito, 13 no total "
        "(ex.: `2610271131304`), até o teste com 15. Também foram aceitos números de 10 dígitos e de 13 dígitos no "
        "formato ano + UO + sequencial (26/10/2026). Números de 17 a 18 dígitos fizeram o GRP recusar todas as OPs "
        "(*DataException*, 14/09/2026).",
        "* **Por que data e hora:** o número muda a cada segundo, não se esgota e não exige combinar faixas entre "
        "executores. Dois envios só coincidem se saírem no mesmo segundo e sortearem os mesmos dígitos; se acontecer, o "
        "GRP recusa o segundo e basta reenviar com outro número. A árvore interativa monta o número assim e, no mesmo "
        "navegador, nunca repete um número (cliques no mesmo segundo seguem em sequência).",
        "* **Justificativa sem barra:** uma barra (`/`) na justificativa da OP fez o GRP responder "
        "*ArrayIndexOutOfBoundsException* em todas as chamadas (14/09/2026). Troque por hífen (`-`).",
        "* **Sem resposta, o resultado é indeterminado:** quando a chamada termina sem resposta (tempo esgotado ou conexão "
        "cortada), a solicitação pode ter sido gravada. Consulte o GRP antes de reenviar, para não gerar documento em "
        "dobro; se reenviar, use um número de requisição novo. A árvore mostra esses casos como *resultado indeterminado* "
        "e só libera novo envio depois que a pessoa confirma que conferiu no GRP.",
    ])


# =============================================================================
# Exemplos por cenário (base homologada)
# =============================================================================

# (título, id do cenário, etapa, o que muda em relação ao exemplo principal)
EXEMPLOS_CENARIO = [
    ("Empenho com credor CNPJ", "Chamada-33", "stage2", "credor pessoa jurídica"),
    ("OLP sem retenção", "Chamada-01", "stage3", "sem `retencaoOlpRequestList`; `valorLiquido` = bruto"),
    ("OLP com INSS", "Chamada-02", "stage3", "uma retenção, tipo `14`"),
    ("OLP com ISSQN", "Chamada-03", "stage3", "uma retenção, tipo `13`"),
    ("OLP com regionalização", "Chamada-17", "stage3", "`regionalizacaoDespesaOlpRequestList` com município IBGE"),
    ("OP com crédito em poupança", "Chamada-05", "stage4", "`tipoContaACreditar` `2`"),
    ("OP com débito em conta específica", "Chamada-09", "stage4", "`tipoContaADebitar` `2` com banco/agência/conta a debitar"),
    ("OP com conta específica e poupança", "Chamada-13", "stage4", "`tipoContaADebitar` `2` e `tipoContaACreditar` `2`"),
]

ROTULO_ETAPA = {"stage2": "Empenho", "stage3": "OLP", "stage4": "OP bancária"}


def bloco_exemplos_cenarios(scenarios, nivel_titulo: str = "####") -> str:
    """Envio e resposta reais (CPFs mascarados) da etapa que muda em cada variação da matriz."""
    por_id = {s["id"]: s for s in scenarios}
    md = ["As etapas que não aparecem num exemplo são iguais às do exemplo principal (`Chamada-04`: credor CPF, sem "
          "regionalização, Conta Única, conta corrente, INSS + ISSQN). Os 64 cenários são de 23/09/2026: são chamadas reais, "
          "mas anteriores ao IRRF e a várias regras aprendidas depois. A matriz completa fica em "
          "`data/chamadas_database.json`; para montar uma chamada atual, use a árvore interativa."]
    for titulo, sid, etapa, muda in EXEMPLOS_CENARIO:
        s = por_id[sid]
        md += ["", f"{nivel_titulo} {titulo} (`{sid}`, etapa {ROTULO_ETAPA[etapa]})", "", f"O que muda: {muda}.", ""]
        md += envio_xml(s["xml_data"][etapa]["req"]) + ["",
               "Resposta:", "", "```xml", s["xml_data"][etapa]["res"].strip(), "```"]
    return "\n".join(md)


# =============================================================================
# Exemplos de envio conferidos com o contrato atual
# =============================================================================

def envio_xml(xml: str, rotulo: str = "Envio:") -> list:
    """Linhas de Markdown de um exemplo de envio, sempre no formato do contrato atual. Um envio antigo (campo que saiu
    do contrato, ordem diferente) é atualizado sem mexer nos valores, com uma nota do que mudou."""
    from core.contrato import atualizar, contrato
    xml = xml.strip()
    if not contrato().validar(xml):
        return [rotulo, "", "```xml", xml, "```"]
    novo, mudancas = atualizar(xml)
    return [rotulo, "", "```xml", novo, "```", "",
            "> **XML no formato atual.** O envio original, aceito pelo GRP na época, foi ajustado ao contrato da "
            f"produção de 26/10/2026, sem mudar os valores: {'; '.join(mudancas)}."]


# =============================================================================
# Sincronização com a DOCUMENTACAO
# =============================================================================

def blocos(scenarios) -> dict:
    return {
        "versao": bloco_versao(),
        "historico": bloco_historico(),
        "endpoints": bloco_endpoints(),
        "sistema_origem": bloco_sistema_origem(),
        "irrf": bloco_irrf(),
        "erros": bloco_erros(),
        "divergencias": bloco_divergencias(),
        "arvore": bloco_arvore(),
        "regras_envio": bloco_regras_envio(),
        "contratos": bloco_contratos(),
        "exemplos_cenarios": bloco_exemplos_cenarios(scenarios, nivel_titulo="####"),
    }


_MARCADOR = re.compile(r"(<!-- BLOCO:(\w+):INICIO -->\n).*?(\n<!-- BLOCO:\2:FIM -->)", re.DOTALL)


def aplicar_blocos(texto: str, conteudo: dict) -> str:
    """Reescreve o conteúdo entre cada par de marcadores. Marcador desconhecido é erro (evita bloco órfão)."""
    def troca(m):
        nome = m.group(2)
        if nome not in conteudo:
            raise KeyError(f"Bloco desconhecido na DOCUMENTACAO: {nome}")
        return m.group(1) + conteudo[nome] + m.group(3)
    return sanitize_xml_text(_MARCADOR.sub(troca, texto))


def atualizar_documentacao(scenarios, path: str = DOCUMENTACAO_PATH) -> str:
    with open(path, encoding="utf-8") as f:
        atual = f.read()
    novo = aplicar_blocos(atual, blocos(scenarios))
    if novo != atual:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(novo)
    return path
