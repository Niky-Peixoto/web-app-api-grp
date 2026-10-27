/*
 * Montagem dos XMLs SOAP do GRP, conferências antes do envio e leitura das respostas.
 *
 * Os envelopes são cópia exata dos que o Assistente GRP (GRP-Tool, grp_tool/xml_builder.py) envia e o GRP aceitou:
 * mesma ordem de tags, mesmos espaços. tests/js/test_grp_xml.js compara byte a byte com XMLs gerados pelo GRP-Tool
 * (tests/fixtures/grp_tool/). Não mude a ordem ou o nome de uma tag sem um envio real que prove o novo formato.
 *
 * Funciona no navegador (window.GrpXml) e no Node (require), sem dependências.
 */
(function (raiz, fabrica) {
  if (typeof module === "object" && module.exports) module.exports = fabrica();
  else raiz.GrpXml = fabrica();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // ---------------------------------------------------------------------------------------------------------------
  // Endereços e namespaces
  // ---------------------------------------------------------------------------------------------------------------

  const AMBIENTES = {
    producao: "https://www.grp.servicos.mg.gov.br/serviceBus",
    desenvolvimento: "https://desenvolvimento.grp.servicos.mg.gov.br/serviceBus",
  };

  const SERVICOS = {
    processo: { caminho: "institucional/GerarNumeroProcessoGrpWS", nome: "GerarNumeroProcessoGrpWS", operacao: "gerarNumeroProcessoGrp" },
    empenho: { caminho: "empenho/SolicitacaoEmpenhoWS", nome: "SolicitacaoEmpenhoWS", operacao: "gerarSolicitacaoEmpenho", identificador: "EMPOLP1.1" },
    reforco: { caminho: "empenho/SolicitacaoReforcoDeEmpenhoWS", nome: "SolicitacaoReforcoDeEmpenhoWS", operacao: "gerarSolicitacaoReforcoEmpenho", identificador: "EMPOLP1.2" },
    anulacao_empenho: { caminho: "empenho/SolicitacaoAnulacaoEmpenhoWS", nome: "SolicitacaoAnulacaoEmpenhoWS", operacao: "gerarSolicitacaoAnulacaoSaldoEmpenho", identificador: "EMPOLP1.3" },
    olp: { caminho: "empenho/SolicitacaoOlpWS", nome: "SolicitacaoOlpWS", operacao: "solicitarOLP", identificador: "EMPOLP2.1" },
    anulacao_olp: { caminho: "empenho/SolicitacaoAnulacaoValoresNaOlpWS", nome: "SolicitacaoAnulacaoValoresNaOlpWS", operacao: "solicitarAnulacaoValoresNaOLP", identificador: "EMPOLP2.2" },
    op: { caminho: "pagBancarioEEscritural/SolicOrdemPagamentoBancariaWS", nome: "SolicOrdemPagamentoBancariaWS", operacao: "gerarSolicOrdemPagamentoBancaria", identificador: "PGBANESC1.1.1" },
    cancelamento: { caminho: "pagBancarioEEscritural/CancelamentoOrdemPagamentoBancariaWS", nome: "CancelamentoOrdemPagamentoBancariaWS", operacao: "cancelarOrdemPagamentoBancaria", identificador: "PGBANESC1.2.1" },
  };

  const NS_EMPENHO = "http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/";
  const NS_PAGAMENTO = "http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/";

  function endpoint(ambiente, servico) {
    return (AMBIENTES[ambiente] || AMBIENTES.producao) + "/" + SERVICOS[servico].caminho;
  }

  // ---------------------------------------------------------------------------------------------------------------
  // Formatos
  // ---------------------------------------------------------------------------------------------------------------

  /** Igual a xml.sax.saxutils.escape do Python: só &, < e >. */
  function esc(texto) {
    return String(texto == null ? "" : texto).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function digitos(texto) {
    return String(texto == null ? "" : texto).replace(/\D/g, "");
  }

  /** "1.234,56", "1234,56", "1234.56" ou 1234.56 -> centavos (inteiro). null se vazio ou inválido. */
  function centavos(valor) {
    if (valor == null) return null;
    if (typeof valor === "number") return Math.round(valor * 100);
    let t = String(valor).trim().replace(/^R\$\s*/i, "").replace(/\s/g, "");
    if (!t) return null;
    if (t.includes(",")) t = t.replace(/\./g, "").replace(",", ".");
    if (!/^-?\d+(\.\d{1,2})?$/.test(t)) return null;
    const [inteiro, fracao = ""] = t.replace("-", "").split(".");
    const c = parseInt(inteiro, 10) * 100 + parseInt((fracao + "00").slice(0, 2), 10);
    return t.startsWith("-") ? -c : c;
  }

  /** centavos -> "1234.56" (formato do XML). */
  function valorXml(c) {
    const negativo = c < 0;
    const abs = Math.abs(c);
    return (negativo ? "-" : "") + Math.floor(abs / 100) + "." + String(abs % 100).padStart(2, "0");
  }

  /** centavos -> "1.234,56" (para mostrar). */
  function valorBr(c) {
    if (c == null) return "";
    const [i, f] = valorXml(Math.abs(c)).split(".");
    return (c < 0 ? "-" : "") + i.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + "," + f;
  }

  /** "/" na justificativa derrubou 100% das chamadas (14/09/2026); o GRP-Tool troca por "-" e junta espaços. */
  function sanitizarJustificativa(texto) {
    return String(texto || "").replace(/[\/\\]/g, "-").split(/\s+/).filter(Boolean).join(" ");
  }

  /** dd/mm/aaaa ou aaaa-mm-dd -> aaaa-mm-ddT00:00:00 */
  function dataXml(texto) {
    const t = String(texto || "").trim();
    let m = t.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}T00:00:00`;
    m = t.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return `${m[1]}-${m[2]}-${m[3]}T00:00:00`;
    return "";
  }

  /** "2026/57490", "57490/2026", "2026 57490" -> "2026/57490"; só número -> ano informado. */
  function normalizarOlp(texto, anoPadrao) {
    const partes = String(texto || "").split(/\D+/).filter(Boolean);
    if (!partes.length) return "";
    if (partes.length === 1) return `${anoPadrao}/${partes[0]}`;
    const [a, b] = partes;
    return a.length === 4 && b.length !== 4 ? `${a}/${b}` : b.length === 4 && a.length !== 4 ? `${b}/${a}` : `${a}/${b}`;
  }

  /**
   * numeroRequisicao: data e hora AAMMDDhhmmss (12 dígitos) + sufixo de `casas` dígitos (sorteado e, no mesmo
   * segundo, seguido em sequência). OP com 3 casas = 15 dígitos (aceito em OP, 27/10/2026); os demais serviços com 1
   * casa = 13 dígitos até o teste com 15. 17-18 dígitos fizeram o GRP recusar todas as OPs (14/09/2026).
   */
  function numeroRequisicao(data, sufixo, casas) {
    if (!(casas >= 1 && casas <= 3) || !(sufixo >= 0 && sufixo < 10 ** casas)) throw new RangeError(`sufixo do numeroRequisicao inválido: ${sufixo} (${casas} casas)`);
    const p = (n) => String(n).padStart(2, "0");
    return `${p(data.getFullYear() % 100)}${p(data.getMonth() + 1)}${p(data.getDate())}${p(data.getHours())}${p(data.getMinutes())}${p(data.getSeconds())}${String(sufixo).padStart(casas, "0")}`;
  }

  // ---------------------------------------------------------------------------------------------------------------
  // Etapa 1 - número de processo
  // ---------------------------------------------------------------------------------------------------------------

  function xmlProcesso(d) {
    return `<?xml version="1.0" ?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:int="http://interfaces.webservices.institucional.business.grp.prodemge.gov.br/">
  <soapenv:Header/>
  <soapenv:Body>
    <int:gerarNumeroProcessoGrp>
      <anoExercicio>${d.ano}</anoExercicio>
      <codigoOrgao>${d.orgao}</codigoOrgao>
      <codigoProcessoDeNegocio>${d.processoDeNegocio || "18"}</codigoProcessoDeNegocio>
      <codigoUnidadeAdministrativa>${d.ua}</codigoUnidadeAdministrativa>
      <codigoUnidadeOrcamentaria>${d.uo}</codigoUnidadeOrcamentaria>
      <codigoSistemaSolicitante>${d.sistema}</codigoSistemaSolicitante>
    </int:gerarNumeroProcessoGrp>
  </soapenv:Body>
</soapenv:Envelope>`;
  }

  // ---------------------------------------------------------------------------------------------------------------
  // Etapa 2 - empenho
  // ---------------------------------------------------------------------------------------------------------------

  // Campos "obrigatórios conforme o caso", na ordem do contrato (depois de codigoCc). Vazios são omitidos.
  const CAMPOS_ADICIONAIS_EMPENHO = [
    ["codigoUfg", "Unidade financiadora (UFG)"],
    ["numeroInstrumentoJuridicoEntrada", "Instrumento jurídico de entrada — número de inscrição no GRP"],
    ["codigoTipoInstrumentoJuridicaEntrada", "Instrumento jurídico de entrada — tipo"],
    ["anoInstrumentoJuridicoEntrada", "Instrumento jurídico de entrada — ano"],
    ["numeroInstrumentoJuridicoSaida", "Instrumento jurídico de saída — número de inscrição no GRP"],
    ["codigoTipoInstrumentoJuridicoSaida", "Instrumento jurídico de saída — tipo"],
    ["anoInstrumentoJuridicoSaida", "Instrumento jurídico de saída — ano"],
    ["numeroObra", "Número da obra"],
    ["numeroProcessoCompra", "Número do processo de compra"],
    ["codigoProcedimentoContratacao", "Procedimento de contratação — código"],
    ["nomeProcedimentoContratacao", "Procedimento de contratação — nome"],
    ["numeroEspecificacaoEmpenho", "Número da especificação do empenho"],
  ];

  const CAMPOS_DOTACAO = [
    ["codigoFuncao", "funcao", "Função"], ["codigoSubfuncao", "subfuncao", "Subfunção"],
    ["codigoPrograma", "programa", "Programa"], ["codigoProjetoAtividade", "projetoAtividade", "Projeto/Atividade"],
    ["codigoSubprojetoSubatividade", "subprojeto", "Subprojeto/Subatividade"],
    ["codigoCategoriaEconomica", "categoria", "Categoria econômica"], ["codigoGrupoDespesa", "grupo", "Grupo de despesa"],
    ["codigoModalidadeDespesa", "modalidade", "Modalidade"], ["codigoElementoDespesa", "elemento", "Elemento"],
    ["codigoItem", "item", "Item"], ["codigoIag", "iag", "IAG"], ["codigoGrupoFonte", "grupoFonte", "Grupo de fonte"],
    ["codigoFonteRecurso", "fonte", "Fonte de recurso"], ["codigoIpu", "ipu", "IPU"],
  ];

  function xmlEmpenho(d) {
    const adicionais = CAMPOS_ADICIONAIS_EMPENHO
      .filter(([tag]) => String((d.adicionais || {})[tag] || "").trim())
      .map(([tag]) => `\n          <${tag}>${esc(d.adicionais[tag])}</${tag}>`).join("");
    const dot = d.dotacao || {};
    const linhasDotacao = CAMPOS_DOTACAO.map(([tag, chave]) => `          <${tag}>${dot[chave]}</${tag}>`).join("\n");
    return `<?xml version="1.0" encoding="utf-8"?>
<soap-env:Envelope xmlns:grp="${NS_EMPENHO}"
                   xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicitacaoEmpenho>
      <solicitacaoEmpenho>
        <numeroRequisicao>${d.numeroRequisicao}</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP1.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>${d.sistema}</codigoSistemaOrigem>
        <anoExercicioFinanceiro>${d.ano}</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>${d.uo}</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>${d.orgao}</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>${d.ua}</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>${d.cpfOrdenador}</cpfOrdenadorDespesa>
        <justificativa>${esc(d.justificativa)}</justificativa>
        <tipoEmpenhoComum>${d.tipoEmpenho || "ORDINARIO"}</tipoEmpenhoComum>
        <olpPendenteCreditoNaoRegularizar>
          <indicadorReconhecimentoPassivo>NAO</indicadorReconhecimentoPassivo>
          <cpfOperador>${d.cpfOperador}</cpfOperador>
          <numeroProcessoGeral>${d.numeroProcesso}</numeroProcessoGeral>
          <cpfCnpjCredor>${d.credor}</cpfCnpjCredor>
          <classificacaoCredor>${esc(d.classificacaoCredor)}</classificacaoCredor>
${linhasDotacao}
          <valorEmpenho>${d.valor}</valorEmpenho>
          <codigoCc>${d.centroCusto}</codigoCc>${adicionais}
        </olpPendenteCreditoNaoRegularizar>
      </solicitacaoEmpenho>
    </grp:gerarSolicitacaoEmpenho>
  </soap-env:Body>
</soap-env:Envelope>`;
  }

  // ---------------------------------------------------------------------------------------------------------------
  // Etapa 3 - OLP
  // ---------------------------------------------------------------------------------------------------------------

  /** INSS na OLP: 4 para credor CPF, 14 para CNPJ (o GRP-Tool usa assim; 14 também foi aceito com CPF). */
  function tipoRetencaoInssOlp(credor) {
    return digitos(credor).length === 11 ? "4" : "14";
  }
  const TIPO_RETENCAO_ISSQN_OLP = "13";

  /**
   * d.retencoes: [{tipo, valor (centavos), credor}] - retenções com valor zero NÃO entram (0.00 deu erro no GRP).
   * d.regionalizacao: [{municipio, valor (centavos)}] - formato da OLP aceita em 13/08/2026.
   */
  function xmlOlp(d) {
    const retencoes = (d.retencoes || []).filter((r) => r.valor > 0);
    let valores = `        <ValoresDaOlp>
          <valorBrutoOlp>${valorXml(d.bruto)}</valorBrutoOlp>
          <valorLiquido>${valorXml(d.liquido)}</valorLiquido>`;
    if (retencoes.length) valores += `\n          <valorRetencaoOlp>${valorXml(retencoes.reduce((s, r) => s + r.valor, 0))}</valorRetencaoOlp>`;
    valores += "\n        </ValoresDaOlp>";
    let blocoRetencoes = "";
    if (retencoes.length) {
      // Ordem do contrato (retencaoOlpRequest): o valor vem depois do credor e da competência. O GRP-Tool envia o
      // valor em segundo e o GRP aceita, mas um cliente que valide pelo XSD recusaria.
      const itens = retencoes.map((r) => `          <RetencaoOlp>
            <tipoRetencao>${r.tipo}</tipoRetencao>
            <cpfCapfCredorRetencao>${r.credor}</cpfCapfCredorRetencao>
            <mesCompetenciaRetencao>${d.mesCompetencia}</mesCompetenciaRetencao>
            <anoCompetenciaRetencao>${d.anoCompetencia}</anoCompetenciaRetencao>
            <valorRetencao>${valorXml(r.valor)}</valorRetencao>
          </RetencaoOlp>`).join("\n");
      blocoRetencoes = `\n        <retencaoOlpRequestList>\n${itens}\n        </retencaoOlpRequestList>`;
    }
    let blocoRegionalizacao = "";
    const municipios = (d.regionalizacao || []).filter((m) => digitos(m.municipio));
    if (municipios.length) {
      const itens = municipios.map((m) => `          <RegionalizacaoDespesa>
            <codigoMunicipio>${digitos(m.municipio)}</codigoMunicipio>
            <valorDistribuicao>${valorXml(m.valor)}</valorDistribuicao>
          </RegionalizacaoDespesa>`).join("\n");
      blocoRegionalizacao = `\n        <regionalizacaoDespesaOlpRequestList>\n${itens}\n        </regionalizacaoDespesaOlpRequestList>`;
    }
    return `<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="${NS_EMPENHO}" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:solicitarOLP>
      <solicitacaoOlp>
        <numeroRequisicao>${d.numeroRequisicao}</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP2.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>${d.sistema}</codigoSistemaOrigem>
        <anoExercicioFinanceiro>${d.ano}</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>${d.uo}</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>${d.orgao}</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>${d.ua}</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>${d.cpfOrdenador}</cpfOrdenadorDespesa>
        <cpfOperador>${d.cpfOperador}</cpfOperador>
        <mesCompetenciaDespesa>${d.mesCompetencia}</mesCompetenciaDespesa>
        <anoCompetenciaDespesa>${d.anoCompetencia}</anoCompetenciaDespesa>
        <justificativa>${esc(d.justificativa)}</justificativa>
        <OlpDeEmpenho>
          <numeroDocumentoEmpenho>${d.empenho}</numeroDocumentoEmpenho>
          <cpfCredorBeneficiario>${d.credor}</cpfCredorBeneficiario>
          <tipoClassificacaoCredor>${esc(d.classificacaoCredor)}</tipoClassificacaoCredor>
        </OlpDeEmpenho>
${valores}${blocoRetencoes}${blocoRegionalizacao}
      </solicitacaoOlp>
    </grp:solicitarOLP>
  </soap-env:Body>
</soap-env:Envelope>`;
  }

  // ---------------------------------------------------------------------------------------------------------------
  // Etapa 4 - OP bancária
  // ---------------------------------------------------------------------------------------------------------------

  const TIPO_RETENCAO_IRRF_OP = "10";
  const CODIGO_RECEITA_IRRF_PADRAO = "090140";
  const CREDOR_IRRF_PADRAO = "18715615000160";

  /**
   * Valores da OP a partir do que a OP paga da OLP (`aPagar`, centavos) e do IRRF (centavos).
   * INSS e ISSQN já ficaram na OLP; o IRRF é retido nesta OP: total e item vão com o valor antes do IRRF e os
   * líquidos sem ele. Sem IRRF, tudo igual.
   */
  function valoresOp(aPagar, irrf) {
    const ir = irrf > 0 ? irrf : 0;
    return { total: aPagar, retencoes: ir, liquido: aPagar - ir };
  }

  /**
   * d.debitar: {tipo "1"|"2", banco, agencia, dvAgencia, conta, dvConta}; d.creditar: {tipo "1"|"2", banco, agencia,
   * dvAgencia, conta, dvConta}; d.forma "001"|"002"; d.codigoBarras; d.finalidade; d.aPagar e d.irrf em centavos;
   * d.irrfCodigoReceita, d.irrfCredor.
   */
  function xmlOp(d) {
    const v = valoresOp(d.aPagar, d.irrf);
    const debitar = d.debitar || { tipo: "1" };
    const creditar = d.creditar || { tipo: "1" };
    const especifica = String(debitar.tipo) === "2";
    const contaDebitar = especifica && (debitar.banco || debitar.agencia || debitar.conta)
      ? `\n        <codigoBancoADebitar>${debitar.banco || ""}</codigoBancoADebitar>` +
        `\n        <codigoAgenciaADebitar>${debitar.agencia || ""}</codigoAgenciaADebitar>` +
        `\n        <dvAgenciaADebitar>${debitar.dvAgencia || ""}</dvAgenciaADebitar>` +
        `\n        <codigoContaADebitar>${debitar.conta || ""}</codigoContaADebitar>` +
        `\n        <dvContaADebitar>${debitar.dvConta || ""}</dvContaADebitar>`
      : "";
    const finalidade = String(d.finalidade || "").trim() ? `\n        <finalidadePagamento>${esc(d.finalidade)}</finalidadePagamento>` : "";
    const barras = digitos(d.codigoBarras) ? `\n        <codigoBarras>${esc(digitos(d.codigoBarras))}</codigoBarras>` : "";
    let dvContaCreditar = creditar.dvConta || "";
    if (creditar.conta && !dvContaCreditar) dvContaCreditar = "0"; // nunca omitir; "0" quando a conta não tem DV
    let totalRetencoes = "";
    let retencaoItem = "";
    if (v.retencoes > 0) {
      totalRetencoes = `\n        <valorTotalRetencoes>${valorXml(v.retencoes)}</valorTotalRetencoes>`;
      const campos = [["tipoRetencao", TIPO_RETENCAO_IRRF_OP], ["valorRetencao", valorXml(v.retencoes)],
        ["codigoReceita", d.irrfCodigoReceita || CODIGO_RECEITA_IRRF_PADRAO],
        ["cpfCnpjCredorRetencao", digitos(d.irrfCredor || CREDOR_IRRF_PADRAO)]];
      retencaoItem = "\n            <retencao>" +
        campos.filter(([, valor]) => valor).map(([tag, valor]) => `\n              <${tag}>${esc(valor)}</${tag}>`).join("") +
        "\n            </retencao>";
    }
    return `<?xml version="1.0" encoding="UTF-8"?>
<soap-env:Envelope xmlns:grp="${NS_PAGAMENTO}"
                   xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicOrdemPagamentoBancaria>
      <solicitacaoOrdemPagamentoBancaria>
        <numeroRequisicao>${d.numeroRequisicao}</numeroRequisicao>
        <identificadorProcessoExecucao>PGBANESC1.1.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>${d.sistema}</codigoSistemaOrigem>
        <numeroArquivo>${d.numeroArquivo || "1"}</numeroArquivo>
        <anoExercicioFinanceiro>${d.ano}</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>${d.uo}</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>${d.orgao}</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>${d.ua}</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>${d.cpfOrdenador}</cpfOrdenadorDespesa>
        <cpfOperador>${d.cpfOperador}</cpfOperador>
        <cpfCnpjCredor>${d.credor}</cpfCnpjCredor>
        <classificacaoCredor>${esc(d.classificacaoCredor)}</classificacaoCredor>
        <origemPagamento>OLP Diversos</origemPagamento>
        <cpfCnpjCredorOP>${d.credor}</cpfCnpjCredorOP>
        <classificacaoCredorDaOP>${esc(d.classificacaoCredor)}</classificacaoCredorDaOP>
        <tipoContaADebitar>${debitar.tipo || "1"}</tipoContaADebitar>${contaDebitar}${finalidade}
        <codigoFormaPagamento>${d.forma || "001"}</codigoFormaPagamento>
        <tipoContaACreditar>${creditar.tipo || "1"}</tipoContaACreditar>${barras}
        <codigoBancoACreditar>${creditar.banco || ""}</codigoBancoACreditar>
        <codigoAgenciaACreditar>${creditar.agencia || ""}</codigoAgenciaACreditar>
        <dvAgenciaACreditar>${creditar.dvAgencia || ""}</dvAgenciaACreditar>
        <codigoContaACreditar>${creditar.conta || ""}</codigoContaACreditar>
        <dvContaACreditar>${dvContaCreditar}</dvContaACreditar>
        <valorTotalAPagarDaOP>${valorXml(v.total)}</valorTotalAPagarDaOP>${totalRetencoes}
        <valorLiquidoPagamento>${valorXml(v.liquido)}</valorLiquidoPagamento>
        <dataProgramadaPagamento>${d.dataProgramada}</dataProgramadaPagamento>
        <justificativa>${esc(d.justificativa)}</justificativa>
        <itemDePagamentoList>
          <ItemDePagamento>
            <itemDePagamento>1</itemDePagamento>
            <anoNumeroDaOlpEEmpenho>${d.olp}</anoNumeroDaOlpEEmpenho>
            <valorAPagar>${valorXml(v.total)}</valorAPagar>
            <valorTotalAPagar>${valorXml(v.total)}</valorTotalAPagar>
            <valorLiquido>${valorXml(v.liquido)}</valorLiquido>${retencaoItem}
          </ItemDePagamento>
        </itemDePagamentoList>
      </solicitacaoOrdemPagamentoBancaria>
    </grp:gerarSolicOrdemPagamentoBancaria>
  </soap-env:Body>
</soap-env:Envelope>`;
  }

  // ---------------------------------------------------------------------------------------------------------------
  // Depois da cadeia: cancelamento de OP e manutenções
  // ---------------------------------------------------------------------------------------------------------------

  function xmlCancelamento(d) {
    return `<?xml version="1.0" encoding="UTF-8"?>
<soap-env:Envelope xmlns:grp="${NS_PAGAMENTO}"
                   xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:cancelarOrdemPagamentoBancaria>
      <cancelamentoOrdemPagamentoBancaria>
        <numeroRequisicao>${d.numeroRequisicao}</numeroRequisicao>
        <exercicioFinanceiro>${d.ano}</exercicioFinanceiro>
        <identificadorProcessoExecucao>PGBANESC1.2.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>${d.sistema}</codigoSistemaOrigem>
        <numeroDocumentoOrdemDePagamento>${d.documentoOp}</numeroDocumentoOrdemDePagamento>
        <cpfOrdenadorDespesa>${d.cpfOrdenador}</cpfOrdenadorDespesa>
        <cpfOperador>${d.cpfOperador}</cpfOperador>
        <justificativa>${esc(d.justificativa)}</justificativa>
      </cancelamentoOrdemPagamentoBancaria>
    </grp:cancelarOrdemPagamentoBancaria>
  </soap-env:Body>
</soap-env:Envelope>`;
  }

  /** Mesmo envelope do teste_servicos.py do GRP-Tool: operação e elemento interno, campos em ordem. */
  function envelope(namespace, operacao, interno, campos) {
    const linhas = campos.map(([tag, valor]) => `        <${tag}>${valor}</${tag}>`).join("\n");
    return `<?xml version="1.0" encoding="UTF-8"?>
<soap-env:Envelope xmlns:grp="${namespace}"
                   xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:${operacao}>
      <${interno}>
${linhas}
      </${interno}>
    </grp:${operacao}>
  </soap-env:Body>
</soap-env:Envelope>`;
  }

  function comuns(d) {
    return [["codigoUnidadeOrcamentaria", d.uo], ["codigoOrgaoExecutor", d.orgao], ["codigoUnidadeAdministrativa", d.ua],
      ["cpfOrdenadorDespesa", d.cpfOrdenador], ["cpfOperador", d.cpfOperador]];
  }

  function xmlAnulacaoOlp(d) {
    return envelope(NS_EMPENHO, "solicitarAnulacaoValoresNaOLP", "solicitarAnulacaoValoresNaOLP", [
      ["numeroRequisicao", d.numeroRequisicao], ["identificadorProcessoExecucao", "EMPOLP2.2"],
      ["codigoSistemaOrigem", d.sistema], ["anoExercicioFinanceiro", d.ano], ["numeroOlp", d.numeroOlp],
      ...comuns(d), ["valorLiquidoAnulado", valorXml(d.liquido)], ["valorTotalAnulado", valorXml(d.total)],
      ["justificativa", esc(d.justificativa)]]);
  }

  function xmlAnulacaoEmpenho(d) {
    return envelope(NS_EMPENHO, "gerarSolicitacaoAnulacaoSaldoEmpenho", "gerarSolicitacaoAnulacaoSaldoEmpenho", [
      ["numeroRequisicao", d.numeroRequisicao], ["identificadorProcessoExecucao", "EMPOLP1.3"],
      ["codigoSistemaOrigem", d.sistema], ["anoExercicioFinanceiro", d.ano], ["numeroEmpenho", d.empenho],
      ...comuns(d), ["valorAnulacaoEmpenho", valorXml(d.valor)], ["justificativa", esc(d.justificativa)]]);
  }

  /** Mesma estrutura do caso real de 16/06/2026 (solicitação 27) e do contrato de 26/10/2026. */
  function xmlReforco(d) {
    return envelope(NS_EMPENHO, "gerarSolicitacaoReforcoEmpenho", "solicitacaoReforcoEmpenho", [
      ["numeroRequisicao", d.numeroRequisicao], ["identificadorProcessoExecucao", "EMPOLP1.2"],
      ["codigoSistemaOrigem", d.sistema], ["anoExercicioFinanceiro", d.ano], ["numeroEmpenho", d.empenho],
      ...comuns(d), ["valorReforco", valorXml(d.valor)], ["justificativa", esc(d.justificativa)]]);
  }

  // ---------------------------------------------------------------------------------------------------------------
  // Leitura da resposta
  // ---------------------------------------------------------------------------------------------------------------

  function tag(xml, nome) {
    const m = String(xml).match(new RegExp(`<(?:\\w+:)?${nome}>([\\s\\S]*?)</(?:\\w+:)?${nome}>`));
    return m ? m[1].trim() : "";
  }

  function desescapar(t) {
    return String(t).replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, "&");
  }

  /** Lê a resposta (XML do GRP, SOAP Fault ou o JSON dos registros antigos) num objeto simples. */
  function lerResposta(texto) {
    const t = String(texto || "").trim();
    const r = { bruta: t, mensagens: [] };
    if (!t) return r;
    if (t.startsWith("{")) {
      try {
        const j = JSON.parse(t);
        Object.assign(r, { numeroSolicitacao: String(j.numeroSolicitacao || j.numeroSolicitacaoOlp || j.numeroSolicitacaoDeCancelamentoOP || ""),
          numeroDocumento: j.numeroDocumento ? String(j.numeroDocumento) : "", situacaoSolicitacao: j.situacaoSolicitacao || "",
          situacaoDocumento: j.situacaoDocumento || "" });
        r.mensagens = (j.mensagens || []).map((m) => [String(m.codigo), m.descricao || ""]);
      } catch (e) { r.invalida = true; }
      return r;
    }
    if (/<html[\s>]/i.test(t) || /indisponivel\.mg\.gov\.br/i.test(t)) { r.paginaIndisponivel = true; return r; }
    const fault = tag(t, "faultstring");
    if (fault) { r.fault = desescapar(fault); return r; }
    const ret = tag(t, "return");
    if (ret && !/</.test(ret)) { r.numeroProcesso = ret; return r; }
    for (const [campo, nomes] of [["numeroSolicitacao", ["numeroSolicitacao", "numeroSolicitacaoOlp", "numeroSolicitacaoDeCancelamentoOP"]],
      ["numeroDocumento", ["numeroDocumento"]], ["situacaoSolicitacao", ["situacaoSolicitacao"]],
      ["situacaoDocumento", ["situacaoDocumento"]], ["numeroRequisicao", ["numeroRequisicao"]]]) {
      r[campo] = nomes.map((n) => tag(ret || t, n)).find(Boolean) || "";
    }
    const re = /<(mensagem|Mensagem)>([\s\S]*?)<\/\1>/g;
    let m;
    while ((m = re.exec(ret || t))) r.mensagens.push([tag(m[2], "codigo"), desescapar(tag(m[2], "descricao"))]);
    if (!r.mensagens.length) {
      const codigo = tag(ret || t, "codigo");
      if (codigo) r.mensagens.push([codigo, desescapar(tag(ret || t, "descricao"))]);
    }
    return r;
  }

  const SUCESSO = { "41040": 1, "51424": 1, "54533": 1 };

  // Explicações dos códigos já vistos em chamadas reais (as mesmas do Assistente GRP, com o caso real de cada um).
  const CODIGOS = {
    "25081": ["Campo obrigatório para este caso", "A descrição diz qual campo falta. Os 'obrigatórios conforme o caso' dependem do elemento-item, do IPU e da fonte: confira o catálogo de elemento-item.", "12_erro_25081_campos_obrigatorios_empenho"],
    "30782": ["Requisição em formato inválido", "XML malformado, wrapper ou nome de tag errado. Compare com um caso real aceito."],
    "44448": ["Requisição em formato inválido (OP)", "Confira a origemPagamento (OLP Diversos) e a estrutura do item de pagamento."],
    "38727": ["Campo obrigatório na OP", "Visto com finalidadePagamento ausente em conta específica ou código de barras: envie a tag (o GRP aceitou qualquer texto, ex.: Não se aplica)."],
    "39148": ["Os valores de retenção não fecham", "valorBrutoOlp − valorRetencaoOlp tem de ser igual a valorLiquido, com 2 casas."],
    "40515": ["Dígito da agência inválido", "Para bancos sem DV de agência (Inter 077, Nubank 260, C6 336), não informe o DV."],
    "49762": ["Esta despesa exige regionalização", "Informe os municípios (código IBGE de 7 dígitos) e quanto do valor vai para cada um.", "23_olp_regionalizacao_aceita"],
    "85910": ["Valor não cadastrado no GRP", "A descrição diz qual campo (credor, conta governo, instrumento jurídico...). Use exatamente o que está cadastrado no GRP: a classificação do credor com acento; instrumento pelo número de inscrição.", "17_erro_85910_conta_governo"],
    "37144": ["Solicitação não registrada (erro ao salvar)", "Código genérico: a causa vem depois de 'Causa:'. Casos reais: saldo contábil insuficiente; OLP de exercício anterior (getExigeInstrumentoJuridico); código de barras incompatível com o credor (parametrização do segmento).", "11_erro_37144_saldo_contabil"],
    "45769": ["O banco do boleto não aceita pagamento por código de barras", "A recusa é do banco do boleto (3 primeiros dígitos do código): banco 756 recusado, 001 aceito. Peça outro boleto ou pague por crédito em conta.", "16_erro_62229_sistema_da_OLP"],
    "62229": ["Documento não permitido para este sistema", "A OLP foi registrada por outro sistema de origem. Use o mesmo sistema em toda a cadeia; o Portal de Compras (2) não faz OP pela API.", "16_erro_62229_sistema_da_OLP"],
    "123": ["Valor líquido divergente do calculado pelo GRP", "Na OP com IRRF, o IRRF vai em <retencao> dentro do item, com total e item antes do IRRF.", "04_op_irrf_aceita_130905"],
    "36944": ["A OLP não tem saldo a pagar", "A OLP já foi toda paga (inclusive por fora da integração).", "14_erro_36944_sem_saldo_a_pagar"],
    "45820": ["OP maior que o saldo da OLP", "O valor a pagar não pode passar do saldo da OLP no GRP.", "15_erro_45820_valor_maior_que_saldo"],
    "93285": ["Valor líquido negativo", "Recalcule o líquido."],
  };

  /** {nivel: "sucesso"|"aviso"|"erro", titulo, detalhe, dica, caso} para mostrar ao usuário. */
  function interpretar(r) {
    const todas = r.mensagens.map(([c, d]) => `${c} - ${d}`).join("\n");
    if (r.paginaIndisponivel) return { nivel: "erro", titulo: "GRP indisponível ou acesso bloqueado", detalhe: "Veio uma página de indisponibilidade da PRODEMGE, não uma resposta do GRP.", dica: "Confira se você está na rede do Governo ou na VPN. Em algumas máquinas a borda da PRODEMGE recusa o TLS do Python e aceita o curl.exe do Windows." };
    if (r.fault) {
      if (/elemento inesperado|unexpected element/i.test(r.fault)) return { nivel: "erro", titulo: "O GRP não reconheceu uma tag do XML", detalhe: r.fault, dica: "Nenhum documento foi gerado. Confira o nome e a ordem das tags no contrato (aba Contrato). Uma tag fora do contrato, como <retencaoList> na OP, dá este erro." };
      if (/For input string/i.test(r.fault)) return { nivel: "erro", titulo: "Campo numérico com texto ou vazio", detalhe: r.fault, dica: "Omita a tag ou envie só dígitos." };
      return { nivel: "erro", titulo: "O GRP recusou o XML (SOAP Fault)", detalhe: r.fault, dica: "Nenhum documento foi gerado. Confira o XML contra o contrato." };
    }
    if (r.numeroProcesso) return { nivel: "sucesso", titulo: "Processo gerado", detalhe: `Número do processo: ${r.numeroProcesso}`, dica: "Use este número em numeroProcessoGeral do empenho." };
    if (!r.mensagens.length) return { nivel: "erro", titulo: "Resposta sem mensagem", detalhe: r.bruta.slice(0, 400), dica: "Cole a resposta inteira, como veio do GRP." };
    const codigos = r.mensagens.map(([c]) => c);
    if (codigos.some((c) => SUCESSO[c])) {
      if (r.numeroDocumento) return { nivel: "sucesso", titulo: "Solicitação registrada", detalhe: todas, dica: `Solicitação ${r.numeroSolicitacao} · documento ${r.numeroDocumento} · ${r.situacaoDocumento || r.situacaoSolicitacao}. Guarde os dois números: a consulta de OPs pesquisa pela solicitação; o cancelamento usa o documento.` };
      const situacao = r.situacaoSolicitacao || "";
      // Cancelamento de OP e manutenções não devolvem número de documento: "Concluída" e "Encaminhada para análise" são o sucesso delas.
      if (/conclu/i.test(situacao)) return { nivel: "sucesso", titulo: "Solicitação concluída", detalhe: todas, dica: `Solicitação ${r.numeroSolicitacao || "?"} · ${situacao}.` };
      if (/encaminhada/i.test(situacao)) return { nivel: "sucesso", titulo: "Solicitação aceita — encaminhada para análise", detalhe: todas, dica: `Solicitação ${r.numeroSolicitacao || "?"}. É o resultado normal de reforço e anulações: a solicitação segue para análise no GRP e não tem número de documento.` };
      return { nivel: "aviso", titulo: `Solicitação aceita, sem número de documento${situacao ? " — " + situacao : ""}`, detalhe: todas, dica: `Solicitação ${r.numeroSolicitacao || "?"}. Sem número de documento, a solicitação aguarda aprovação no GRP (ordenador sem exceção de assinatura na UA).` };
    }
    const descricoes = r.mensagens.map(([, d]) => d).join(" ");
    const sistema = descricoes.match(/Sistema\s+(.+?)\s+diferente do sistema do elemento-item\s+(.+?)\.?$/i);
    if (sistema) return { nivel: "erro", titulo: `Este elemento-item só pode ser empenhado pelo sistema ${sistema[2]}`, detalhe: todas, dica: "Cada elemento-item pode ter um sistema predominante. Use um item liberado para o seu sistema (catálogo de elemento-item) ou empenhe pelo sistema dono.", caso: "19_erro_sistema_do_elemento_item" };
    if (/programa[çc][ãa]o or[çc]ament[áa]ria/i.test(descricoes)) return { nivel: "erro", titulo: "Sem saldo orçamentário para esta dotação", detalhe: todas, dica: "A UA não tem Programação Orçamentária aprovada para essa combinação de UO, classificação, fonte e IPU." };
    if (/getExigeInstrumentoJuridico/.test(descricoes)) return { nivel: "erro", titulo: "OP de OLP de exercício anterior não é aceita pela API", detalhe: todas, dica: "Aconteceu com toda OLP de ano anterior (restos a pagar). Gere esta OP pela tela do GRP. Caso aberto com a PRODEMGE.", caso: "10_erro_37144_instrumento_juridico" };
    if (/saldo atual da Conta cont[áa]bil/i.test(descricoes)) return { nivel: "erro", titulo: "Saldo contábil insuficiente", detalhe: todas, dica: "A conta contábil não tem saldo para o valor. Confira o saldo da OLP no GRP.", caso: "11_erro_37144_saldo_contabil" };
    if (/getCodigoTipoGuiaEspecifica/.test(descricoes)) return { nivel: "erro", titulo: "Esta forma de pagamento pede o tipo de guia", detalhe: todas, dica: "Use crédito em conta ou código de barras." };
    const principal = codigos.find((c) => CODIGOS[c]) || codigos[0];
    const [titulo, dica, caso] = CODIGOS[principal] || ["O GRP recusou a solicitação", "Leia a descrição da mensagem."];
    const extras = codigos.filter((c) => c !== principal && CODIGOS[c]).map((c) => `${c}: ${CODIGOS[c][0]}.`);
    return { nivel: "erro", titulo: `${principal} — ${titulo}`, detalhe: todas, dica: [dica, ...extras].join(" "), caso };
  }

  // ---------------------------------------------------------------------------------------------------------------
  // Comandos para enviar (formatos universais)
  // ---------------------------------------------------------------------------------------------------------------

  /**
   * Comandos autocontidos (o XML vai dentro): copiar, colar e rodar, sem depender de arquivo baixado.
   * Cabeçalhos iguais aos do Assistente GRP: Content-Type e "SOAPAction:" vazio (o curl não manda o cabeçalho).
   */
  function comandos(url, xml) {
    const marca = "FIM_DO_XML_GRP";
    return {
      powershell: [
        "# Cole tudo no PowerShell e tecle Enter. A resposta aparece aqui e já fica copiada para colar na árvore.",
        "[Console]::OutputEncoding = [Text.Encoding]::UTF8",
        "$xml = @'",
        xml,
        "'@",
        "$envio = Join-Path $env:TEMP 'grp_envio.xml'",
        "[IO.File]::WriteAllText($envio, $xml, (New-Object Text.UTF8Encoding $false))",
        `$resposta = curl.exe -s -S -X POST -H 'Content-Type: text/xml; charset=utf-8' -H 'SOAPAction:' --data-binary "@$envio" --max-time 90 '${url}'`,
        "$resposta",
        "($resposta -join \"`n\") | Set-Clipboard",
        "Write-Host ''",
        "Write-Host 'Resposta copiada: cole no campo \"Resposta do GRP\" da arvore.' -ForegroundColor Green",
      ].join("\n"),
      curl: `curl -s -S -X POST -H "Content-Type: text/xml; charset=utf-8" -H "SOAPAction:" --data-binary @- --max-time 90 \\\n  "${url}" <<'${marca}'\n${xml}\n${marca}`,
      python: `import requests  # pip install requests\n\nxml = """${xml.replace(/\\/g, "\\\\").replace(/"""/g, '\\"\\"\\"')}"""\n\nr = requests.post("${url}", data=xml.encode("utf-8"),\n                  headers={"Content-Type": "text/xml; charset=utf-8"},\n                  timeout=90, allow_redirects=False)  # sem www o servidor responde 301: não siga sozinho\nprint(r.status_code)\nprint(r.text)`,
      http: `Método:  POST\nURL:     ${url}\nCabeçalho: Content-Type: text/xml; charset=utf-8\nCorpo:   o XML (aba XML), como texto puro (raw / XML)`,
    };
  }

  return {
    AMBIENTES, SERVICOS, endpoint, esc, digitos, centavos, valorXml, valorBr, sanitizarJustificativa, dataXml,
    normalizarOlp, numeroRequisicao, CAMPOS_ADICIONAIS_EMPENHO, CAMPOS_DOTACAO, tipoRetencaoInssOlp,
    TIPO_RETENCAO_ISSQN_OLP, CODIGO_RECEITA_IRRF_PADRAO, CREDOR_IRRF_PADRAO, valoresOp,
    xmlProcesso, xmlEmpenho, xmlOlp, xmlOp, xmlCancelamento, xmlAnulacaoOlp, xmlAnulacaoEmpenho, xmlReforco,
    lerResposta, interpretar, CODIGOS, comandos,
  };
});
