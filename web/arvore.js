/*
 * Árvore interativa da API do GRP: monta cada chamada com os dados do usuário (web/grp_xml.js), confere as regras
 * aprendidas nos testes reais (as mesmas do Assistente GRP) e explica a resposta do GRP.
 * Sem dependências e sem rede: tudo roda no navegador; os dados ficam só no navegador de quem usa.
 */
(function () {
  "use strict";
  const G = window.GrpXml;
  const D = JSON.parse(document.getElementById("dados").textContent);
  const CHAVE = "arvore-grp-v2";

  // =================================================================================================================
  // Utilidades
  // =================================================================================================================

  const h = (t) => String(t == null ? "" : t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const dig = G.digitos;
  const $ = (sel, raiz) => (raiz || document).querySelector(sel);
  const $$ = (sel, raiz) => Array.from((raiz || document).querySelectorAll(sel));

  function obter(caminho) { return caminho.split(".").reduce((o, k) => (o == null ? undefined : o[k]), E); }
  function definir(caminho, valor) {
    const partes = caminho.split(".");
    const ultimo = partes.pop();
    const alvo = partes.reduce((o, k) => (o[k] = o[k] || {}), E);
    alvo[ultimo] = valor;
  }

  function hoje() {
    const d = new Date();
    return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
  }

  function avisoCopiado(texto) {
    let el = $(".copiado");
    if (!el) { el = document.createElement("div"); el.className = "copiado"; document.body.appendChild(el); }
    el.textContent = texto;
    el.classList.add("visivel");
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove("visivel"), 1600);
  }

  function copiar(texto) {
    const fim = () => avisoCopiado("Copiado");
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(texto).then(fim, () => copiarAntigo(texto, fim));
    else copiarAntigo(texto, fim);
  }
  function copiarAntigo(texto, fim) {
    const ta = document.createElement("textarea");
    ta.value = texto; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); fim(); } catch (e) { avisoCopiado("Não foi possível copiar: selecione e copie à mão"); }
    ta.remove();
  }

  function baixar(nome, conteudo, tipo) {
    const url = URL.createObjectURL(new Blob([conteudo], { type: tipo || "text/xml;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url; a.download = nome; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function realcarXml(xml) {
    return h(xml)
      .replace(/(&lt;\/?)([\w:-]+)/g, '$1<span class="t">$2</span>')
      .replace(/(&gt;)([^&\n]+?)(&lt;\/)/g, '$1<span class="v">$2</span>$3');
  }

  // =================================================================================================================
  // Estado (salvo só neste navegador)
  // =================================================================================================================

  const agora = new Date();
  const PADRAO = {
    atual: "execucao",
    formatoReq: 0,   // 2 = data e hora (AAMMDDhhmmss) + sufixo; ao abrir, números de formatos anteriores são descartados
    ultimoReq: {},   // maior numeroRequisicao gerado neste navegador, por tamanho do sufixo (os próximos são maiores)
    req: {},         // número de requisição reservado para o próximo envio de cada etapa
    indeterminado: {}, // envio sem resposta (tempo esgotado): o GRP pode ter registrado
    ultimaCopia: {}, // número que foi junto na última cópia do XML ou do comando
    respostas: {},
    execucao: { ambiente: "producao", sistema: "51", ano: String(agora.getFullYear()), orgao: "", uo: "", ua: "",
      cpfOrdenador: "", cpfOperador: "", credor: "", classificacaoCredor: "" },
    processo: { processoDeNegocio: "18" },
    empenho: { numeroProcesso: "", tipoEmpenho: "ORDINARIO", justificativa: "", valor: "", centroCusto: "",
      dotacao: {}, adicionais: {} },
    olp: { empenho: "", mesCompetencia: String(agora.getMonth() + 1), anoCompetencia: String(agora.getFullYear()),
      justificativa: "", bruto: "", usarInss: false, inss: "", credorInss: "29979036000140", usarIssqn: false,
      issqn: "", credorIssqn: "", usarRegionalizacao: false, regionalizacao: [{ municipio: "", valor: "" }] },
    op: { olp: "", aPagar: "", usarIrrf: false, irrf: "", irrfCodigoReceita: G.CODIGO_RECEITA_IRRF_PADRAO,
      irrfCredor: G.CREDOR_IRRF_PADRAO, debitarTipo: "1", debitar: {}, finalidade: "", forma: "001",
      creditarTipo: "1", creditar: {}, codigoBarras: "", dataProgramada: hoje(), justificativa: "" },
    cancelamento: { documentoOp: "", justificativa: "" },
    anulacao_olp: { olp: "", liquido: "", total: "", justificativa: "" },
    reforco: { empenho: "", valor: "", justificativa: "" },
    anulacao_empenho: { empenho: "", valor: "", justificativa: "" },
  };

  function mesclar(base, salvo) {
    if (Array.isArray(base)) return Array.isArray(salvo) ? salvo : base;
    if (base && typeof base === "object") {
      const r = {};
      for (const k of new Set([...Object.keys(base), ...Object.keys(salvo || {})])) r[k] = mesclar(base[k], (salvo || {})[k]);
      return r;
    }
    return salvo === undefined ? base : salvo;
  }

  let E;
  try { E = mesclar(PADRAO, JSON.parse(localStorage.getItem(CHAVE) || "{}")); } catch (e) { E = mesclar(PADRAO, {}); }
  function salvar() { try { localStorage.setItem(CHAVE, JSON.stringify(E)); } catch (e) { /* navegador sem armazenamento */ } }

  /* numeroRequisicao: data e hora (AAMMDDhhmmss) + sufixo. OP: 3 dígitos (15 no total, aceito em OP em 27/10/2026);
   * demais serviços: 1 dígito (13 no total) até serem testados com 15.
   * - O sufixo começa sorteado (duas pessoas no mesmo segundo dificilmente coincidem) e segue em sequência.
   * - Neste navegador os números só crescem: sem repetição mesmo com cliques no mesmo segundo ou relógio que volta.
   * - O número conta como usado assim que aparece no XML; copiar ou enviar libera a etapa para o próximo. */
  const CASAS_REQUISICAO = { op: 3 };
  function casasRequisicao(etapa) { return CASAS_REQUISICAO[etapa] || 1; }
  function requisicao(etapa) {
    if (E.req[etapa]) return E.req[etapa];
    const casas = casasRequisicao(etapa), limite = 10 ** casas;
    const ultimo = String(E.ultimoReq[casas] || "");
    const agora = new Date();
    let base = G.numeroRequisicao(agora, 0, 1).slice(0, 12);
    let sufixo = Math.floor(Math.random() * limite);
    // Mesmo segundo do último número (ou relógio que voltou): continua do último, sem repetir.
    if (ultimo && base <= ultimo.slice(0, 12)) {
      base = ultimo.slice(0, 12);
      sufixo = Math.max(sufixo, Number(ultimo.slice(12)) + 1);
      if (sufixo >= limite) { // os sufixos deste segundo acabaram: usa o segundo seguinte
        const [aa, mm, dd, hh, mi, ss] = base.match(/\d\d/g).map(Number);
        base = G.numeroRequisicao(new Date(2000 + aa, mm - 1, dd, hh, mi, ss + 1), 0, 1).slice(0, 12);
        sufixo = Math.floor(Math.random() * limite);
      }
    }
    E.req[etapa] = E.ultimoReq[casas] = base + String(sufixo).padStart(casas, "0");
    salvar();
    return E.req[etapa];
  }
  function novaRequisicao(etapa) { delete E.req[etapa]; requisicao(etapa); salvar(); }
  /** O número reservado para esta etapa saiu (cópia ou envio): o próximo envio usa outro. */
  function gastarRequisicao(etapa) { const n = E.req[etapa]; delete E.req[etapa]; salvar(); return n; }
  // Estado de versões anteriores (ano + UO + sequencial): descarta os números reservados e não enviados.
  if (E.formatoReq !== 2) { E.req = {}; E.formatoReq = 2; delete E.seq; delete E.seqPor; delete E.usadosPor; delete E.execucao.faixaInicio; delete E.execucao.faixaFim; salvar(); }

  // =================================================================================================================
  // Catálogos (fotos datadas do GRP, as mesmas do Assistente GRP)
  // =================================================================================================================

  const C = D.catalogos;
  const norm = (v) => { const d = dig(v); return d ? String(parseInt(d, 10)) : ""; };
  const tres = (v) => { const d = dig(v); return d ? d.padStart(3, "0") : ""; };
  const elementoItem = {};
  for (const r of C.elemento_item.registros) elementoItem[`${r.elemento}/${r.item}`] = r;
  const ONDE = {
    elemento: "GRP Institucional › Consulta elemento-item de despesa",
    cc: "GRP Institucional › Gerir › Centro de custo › Manter centro de custo",
    classificacao: "GRP Institucional › consultas da classificação orçamentária; projetos/atividades na Programação Orçamentária",
    conexoes: "relatório de conexões de elemento-item do GRP",
  };
  const fonteCatalogo = (nome, chave) => `Catálogo: ${nome}. Confira no próprio GRP: ${ONDE[chave]}.`;

  function sistemaDoItem(r) { return r.sistema ? r.sistema.split("-")[0].trim() : ""; }

  function avaliarElementoItem(elemento, item, sistema) {
    if (tres(elemento).length !== 3 || tres(item).length !== 3) return null;
    const codigo = `${tres(elemento)}/${tres(item)}`;
    const r = elementoItem[codigo];
    const fonte = fonteCatalogo(C.elemento_item.origem, "elemento");
    if (!r) return { nivel: "aviso", titulo: `${codigo} não está no catálogo`, texto: "Pode ser item novo ou de outro exercício: não é possível conferir antes de enviar.", fonte };
    const descricao = `${r.descricao_elemento} › ${r.descricao_item}`;
    if (r.situacao && r.situacao !== "Ativo") return { nivel: "erro", titulo: `${codigo} está ${r.situacao.toLowerCase()} no GRP`, texto: descricao, fonte };
    if (r.sistema && sistemaDoItem(r) !== String(sistema)) return { nivel: "erro", titulo: `${codigo} é restrito ao sistema ${r.sistema}`, texto: `${descricao}\nO GRP recusa ("Sistema ... diferente do sistema do elemento-item"). Empenhe pelo sistema dono do item.`, fonte, caso: "19_erro_sistema_do_elemento_item" };
    const avisos = [];
    if (r.exige_procedimento) avisos.push("exige procedimento de contratação (código e nome)");
    if (r.permite_obra) avisos.push("pode pedir o número da obra");
    if (r.exige_instrumento) avisos.push("exige instrumento jurídico" + (r.tipo_instrumento ? ` (${r.tipo_instrumento})` : "") + " — de entrada ou de saída");
    if (r.sentenca_judicial) avisos.push("é execução de sentença judicial (dados do precatório)");
    if (r.exige_codigo_barra) avisos.push("a OP deste item exige código de barras" + (r.tipo_codigo_barra ? ` do tipo ${r.tipo_codigo_barra}` : ""));
    if (r.folha) avisos.push("é despesa de pessoal (folha)");
    if (!r.parametrizado) avisos.push("não tem parâmetros de execução preenchidos no GRP");
    return { nivel: avisos.length ? "aviso" : "ok", titulo: `${codigo} liberado para o sistema ${sistema}`, texto: descricao + (avisos.length ? `\nAtenção: ${avisos.join("; ")}.` : ""), fonte };
  }

  function camposExigidos(elemento, item) {
    const r = elementoItem[`${tres(elemento)}/${tres(item)}`];
    const marcas = {};
    if (!r) return marcas;
    if (r.exige_procedimento) marcas.codigoProcedimentoContratacao = marcas.nomeProcedimentoContratacao = "exigido";
    if (r.permite_obra) marcas.numeroObra = "possivel";
    if (r.exige_instrumento) for (const t of ["numeroInstrumentoJuridicoEntrada", "codigoTipoInstrumentoJuridicaEntrada", "anoInstrumentoJuridicoEntrada", "numeroInstrumentoJuridicoSaida", "codigoTipoInstrumentoJuridicoSaida", "anoInstrumentoJuridicoSaida"]) marcas[t] = "possivel";
    return marcas;
  }

  function avaliarCentroCusto(ua, cc) {
    const codigo = norm(cc);
    if (!codigo) return null;
    const dados = C.centros_custo.dados;
    const fonte = fonteCatalogo(C.centros_custo.origem, "cc");
    const u = dados.uas[dig(ua)];
    if (!u) return { nivel: "aviso", titulo: `UA ${ua || "?"} não está no catálogo de centros de custo`, texto: "Não dá para conferir o centro de custo.", fonte };
    const [indice, , nomeUa, codigos] = u;
    const doOrgao = dados.ccs[String(indice)] || {};
    if (codigos.split(" ").includes(codigo)) {
      const [descricao, situacao] = doOrgao[codigo] || ["", "Ativo"];
      if (situacao && situacao !== "Ativo") return { nivel: "erro", titulo: `Centro de custo ${codigo} está ${situacao.toLowerCase()}`, texto: descricao, fonte };
      return { nivel: "ok", titulo: `Centro de custo ${codigo} — ${descricao}`, texto: `Vinculado à UA ${nomeUa}.`, fonte };
    }
    const outro = doOrgao[codigo];
    return { nivel: "aviso", titulo: `Centro de custo ${codigo} não aparece na lista da UA ${dig(ua)}`,
      texto: outro ? `Existe no órgão (${outro[0]}), mas não está vinculado à UA.` : `Não existe no órgão ${dados.orgaos[indice]}.`, fonte };
  }

  const LISTA_DO_CAMPO = { funcao: "funcao", subfuncao: "subfuncao", categoria: "categoria_economica", grupo: "grupo_despesa",
    modalidade: "modalidade_despesa", grupoFonte: "grupo_fonte", ipu: "ipu" };

  /** [texto, ok] para mostrar embaixo de cada campo da dotação; null = nada a dizer. */
  function previaDotacao(campo, valor, uo) {
    const cl = C.classificacao.dados;
    if (!String(valor || "").trim()) return null;
    if (campo === "fonte") {
      const d = dig(valor);
      if (d.length < 4) return null;
      const stn = cl.listas.fonte_stn[norm(d.slice(0, 3))];
      const det = cl.listas.detalhe_fonte[norm(d.slice(3))];
      if (stn == null) return [`fonte da STN ${d.slice(0, 3)} não encontrada`, false];
      if (det == null) return [`${stn} · detalhe ${d.slice(3)} não encontrado`, false];
      return [`${stn} · ${det}`, true];
    }
    if (campo === "projetoAtividade") {
      const da = cl.projetos[dig(uo)];
      if (!da) return null;
      const nome = da[norm(valor)];
      return nome ? [nome, true] : [`sem programação na UO ${dig(uo)}`, false];
    }
    const lista = LISTA_DO_CAMPO[campo];
    if (!lista || !cl.listas[lista]) return null;
    const nome = cl.listas[lista][norm(valor)];
    return nome != null ? [nome, true] : ["código fora das listas ativas", false];
  }

  function conferirNatureza(dot) {
    const partes = [dot.categoria, dot.grupo, dot.modalidade, dot.elemento].map(norm);
    if (!partes.every(Boolean)) return null;
    const [cat, grp, mod, ele] = partes;
    const codigo = `${cat}${grp}${mod.padStart(2, "0")}${ele.padStart(3, "0")}`;
    const rotulo = `natureza ${cat}.${grp}.${mod.padStart(2, "0")}.${ele.padStart(3, "0")}`;
    return C.classificacao.dados.naturezas.includes(codigo) ? null
      : { nivel: "aviso", titulo: `A ${rotulo} não existe nas naturezas ativas`, texto: "Confira categoria, grupo, modalidade e elemento.", fonte: fonteCatalogo(C.classificacao.origem, "classificacao") };
  }

  function avaliarConexao(ano, uo, dot) {
    const el = tres(dot.elemento), it = tres(dot.item), uo5 = dig(uo).padStart(5, "0");
    if (!el || !it || !dig(uo)) return null;
    const uos = C.conexoes.conexoes[dig(ano)];
    if (!uos || !uos[uo5]) return null;
    const combos = uos[uo5][`${el}/${it}`] || [];
    const fonte = fonteCatalogo(C.conexoes.origem, "conexoes");
    const nomesFonte = C.classificacao.dados.listas.detalhe_fonte;
    const descrever = (c) => `grupo ${c[0]} · fonte ${c[1]}${nomesFonte[norm(c[1])] ? ` (${nomesFonte[norm(c[1])]})` : ""} · IPU ${c[2] || "?"}`;
    if (!combos.length) return { nivel: "aviso", titulo: `A UO ${uo5} não usou ${el}/${it} em ${dig(ano)}`, texto: "O relatório mostra o que foi usado, não o que é permitido. Confira se o item é desta UO.", fonte };
    const escolhido = [norm(dot.grupo), dig(dot.fonte) ? dig(dot.fonte).slice(-3).padStart(3, "0") : "", norm(dot.ipu)];
    if (!escolhido.every(Boolean)) return { nivel: "ok", titulo: `Com ${el}/${it}, a UO ${uo5} usou em ${dig(ano)}:`, texto: combos.map(descrever).join("\n"), fonte };
    if (combos.some((c) => norm(c[0]) === escolhido[0] && c[1] === escolhido[1] && norm(c[2]) === escolhido[2])) return null;
    let texto = "Usadas com este item:\n" + combos.map(descrever).join("\n");
    if (["097", "098"].includes(escolhido[1])) texto += "\nFonte de transferência especial da União: o GRP costuma pedir o instrumento jurídico de entrada.";
    return { nivel: "aviso", titulo: `A UO ${uo5} nunca usou ${el}/${it} com grupo ${escolhido[0]}, fonte ${escolhido[1]} e IPU ${escolhido[2]}`, texto, fonte, caso: "13_erro_25081_instrumento_entrada_empenho" };
  }

  // =================================================================================================================
  // Conferências comuns
  // =================================================================================================================

  function conf(nivel, titulo, texto, extra) { return Object.assign({ nivel, titulo, texto: texto || "" }, extra || {}); }

  function faltando(lista) {
    const vazios = lista.filter(([v]) => !String(v == null ? "" : v).trim()).map(([, nome]) => nome);
    return vazios.length ? [conf("erro", "Faltam campos", vazios.join(", "))] : [];
  }

  function conferirExecucao(etapa) {
    const x = E.execucao, r = [];
    if (dig(x.uo).length && dig(x.uo).length !== 5) r.push(conf("aviso", "UO costuma ter 5 dígitos", `Informado: ${x.uo}`));
    if (dig(x.ua).length && dig(x.ua).length !== 10) r.push(conf("aviso", "UA costuma ter 10 dígitos", `Informado: ${x.ua}`));
    for (const [v, nome] of [[x.cpfOrdenador, "CPF do ordenador"], [x.cpfOperador, "CPF do operador"]]) {
      if (dig(v) && dig(v).length !== 11) r.push(conf("erro", `${nome} precisa ter 11 dígitos`));
    }
    if (dig(x.credor) && ![11, 14].includes(dig(x.credor).length)) r.push(conf("erro", "Credor: CPF (11) ou CNPJ (14) dígitos"));
    if (dig(x.credor) && dig(x.credor) === dig(x.cpfOrdenador)) r.push(conf("erro", "O ordenador não pode ser o credor", "O GRP recusa quando são iguais."));
    if (x.ambiente === "desenvolvimento") r.push(conf("aviso", "Ambiente de desenvolvimento da PRODEMGE", "Use só com autorização da PRODEMGE: os dados (empenhos, OLPs, credores) são outros."));
    if (x.sistema === "2" && ["op", "cancelamento"].includes(etapa)) r.push(conf("erro", "O Portal de Compras (sistema 2) não faz OP pela API", "Ele só empenha e liquida. A OP desses documentos é feita pela tela do GRP.", { caso: "16_erro_62229_sistema_da_OLP" }));
    return r;
  }

  function conferirJustificativa(texto) {
    const r = [];
    if (/[\/\\]/.test(texto || "")) r.push(conf("aviso", "A barra na justificativa foi trocada por hífen", "\"/\" na justificativa derrubou 100% das chamadas em teste (14/09/2026). O XML já sai com \"-\"."));
    if ((texto || "").length > 255) r.push(conf("aviso", "Justificativa com mais de 255 caracteres", "O GRP aceita até 255."));
    return r;
  }

  function execXml() {
    const x = E.execucao;
    return { sistema: dig(x.sistema) || x.sistema, ano: dig(x.ano), orgao: dig(x.orgao), uo: dig(x.uo), ua: dig(x.ua),
      cpfOrdenador: dig(x.cpfOrdenador), cpfOperador: dig(x.cpfOperador) };
  }

  const cent = (v) => G.centavos(v);
  const temValor = (v) => cent(v) != null && cent(v) > 0;

  // =================================================================================================================
  // Campos de formulário
  // =================================================================================================================

  function campo(caminho, rotulo, o) {
    o = o || {};
    const valor = obter(caminho);
    const tipo = o.tipo || "text";
    const extra = `${o.inteiro ? " inteiro" : ""}${o.classe ? " " + o.classe : ""}`;
    let entrada;
    if (o.opcoes) {
      entrada = `<select data-caminho="${caminho}">${o.opcoes.map(([v, t]) => `<option value="${h(v)}"${String(valor) === String(v) ? " selected" : ""}>${h(t)}</option>`).join("")}</select>`;
    } else if (tipo === "textarea") {
      entrada = `<textarea data-caminho="${caminho}" rows="2" placeholder="${h(o.ph || "")}">${h(valor)}</textarea>`;
    } else {
      entrada = `<input data-caminho="${caminho}" value="${h(valor)}" placeholder="${h(o.ph || "")}" inputmode="${o.numerico ? "numeric" : o.dinheiro ? "decimal" : "text"}"${o.lista ? ` list="${o.lista}"` : ""} autocomplete="off" spellcheck="false">`;
    }
    return `<div class="campo${extra}" data-campo="${caminho}"><label>${h(rotulo)}${o.tag ? `<span class="tag">${h(o.tag)}</span>` : ""}</label>${entrada}${o.ajuda ? `<span class="ajuda">${o.ajuda}</span>` : ""}<span class="previa" data-previa="${caminho}"></span></div>`;
  }

  function escolha(caminho, opcoes) {
    const atual = String(obter(caminho));
    return `<div class="opcoes">${opcoes.map(([v, t, sub]) => `<button type="button" class="opcao${atual === String(v) ? " marcada" : ""}" data-escolha="${caminho}" data-valor="${h(v)}">${h(t)}${sub ? `<small>${h(sub)}</small>` : ""}</button>`).join("")}</div>`;
  }

  function liga(caminho, rotulo) {
    return `<label class="linha-opcao"><input type="checkbox" data-liga="${caminho}"${obter(caminho) ? " checked" : ""}> ${h(rotulo)}</label>`;
  }

  function secao(titulo, corpo, nota) {
    return `<section class="secao"><header><h3>${h(titulo)}</h3>${nota ? `<span class="nota">${nota}</span>` : ""}</header><div class="corpo">${corpo}</div></section>`;
  }

  const CLASSIFICACOES = ["BENEFICIÁRIOS DIVERSOS", "FORNECEDOR", "PRESTADOR DE SERVIÇOS", "SERVIDOR PÚBLICO ESTADUAL", "INSTITUIÇÃO FINANCEIRA"];

  // =================================================================================================================
  // Etapas
  // =================================================================================================================

  const ETAPAS = {};

  ETAPAS.execucao = {
    nome: "Dados da execução", numero: "◆", intro: "Informados uma vez e usados em todas as chamadas. Ficam salvos só neste navegador.",
    formulario() {
      const x = E.execucao;
      return secao("Ambiente e sistema", `
        ${escolha("execucao.ambiente", [["producao", "Produção", "www.grp.servicos.mg.gov.br"], ["desenvolvimento", "Desenvolvimento", "só com autorização da PRODEMGE"]])}
        <div class="grade" style="margin-top:12px">
          ${campo("execucao.sistema", "Sistema de origem", { tag: "codigoSistemaOrigem", numerico: true, ajuda: "51 = Nota Fiscal Mineira · 2 = Portal de Compras (só empenha e liquida). O mesmo em toda a cadeia." })}
          ${campo("execucao.ano", "Exercício", { tag: "anoExercicioFinanceiro", numerico: true })}
        </div>`) +
        secao("Unidade executora", `<div class="grade">
          ${campo("execucao.orgao", "Órgão", { tag: "codigoOrgaoExecutor", numerico: true, ph: "10190" })}
          ${campo("execucao.uo", "Unidade orçamentária (UO)", { tag: "codigoUnidadeOrcamentaria", numerico: true, ph: "10191" })}
          ${campo("execucao.ua", "Unidade administrativa (UA)", { tag: "codigoUnidadeAdministrativa", numerico: true, ph: "1019080124" })}
          ${campo("execucao.cpfOrdenador", "CPF do ordenador", { tag: "cpfOrdenadorDespesa", numerico: true, ajuda: "Precisa ter exceção de assinatura na UA para o documento sair na resposta." })}
          ${campo("execucao.cpfOperador", "CPF do operador", { tag: "cpfOperador", numerico: true })}
        </div>`, x.uo ? h(C.classificacao.dados.uos[dig(x.uo)] ? C.classificacao.dados.uos[dig(x.uo)].join(" — ") : "") : "") +
        secao("Credor", `<div class="grade larga">
          ${campo("execucao.credor", "CPF ou CNPJ do credor", { tag: "cpfCnpjCredor", numerico: true, ajuda: "Só dígitos. Precisa estar cadastrado no GRP." })}
          ${campo("execucao.classificacaoCredor", "Classificação do credor", { tag: "classificacaoCredor", lista: "lista-classificacoes", ajuda: "Exatamente como no cadastro, com acento (sem acento: 85910)." })}
        </div><datalist id="lista-classificacoes">${CLASSIFICACOES.map((c) => `<option value="${h(c)}">`).join("")}</datalist>`);
    },
    conferir() {
      const x = E.execucao;
      return faltando([[x.sistema, "sistema"], [x.ano, "exercício"], [x.orgao, "órgão"], [x.uo, "UO"], [x.ua, "UA"],
        [x.cpfOrdenador, "ordenador"], [x.cpfOperador, "operador"], [x.credor, "credor"], [x.classificacaoCredor, "classificação do credor"]])
        .concat(conferirExecucao("execucao"));
    },
  };

  ETAPAS.processo = {
    nome: "Número de processo", numero: "1", servico: "processo",
    intro: "Cria o processo eletrônico que lastreia a despesa. O número de 21 dígitos vai no empenho.",
    formulario() {
      return secao("Processo", `<div class="grade">${campo("processo.processoDeNegocio", "Processo de negócio", { tag: "codigoProcessoDeNegocio", numerico: true, ajuda: "18 para as despesas da integração." })}</div>`);
    },
    conferir() { return conferirExecucao("processo"); },
    xml() { const x = execXml(); return G.xmlProcesso({ ...x, processoDeNegocio: dig(E.processo.processoDeNegocio) || "18" }); },
    levar(r) { if (r.numeroProcesso) { E.empenho.numeroProcesso = r.numeroProcesso; return ["empenho", `Processo ${r.numeroProcesso} levado para o empenho`]; } },
    casos: ["20_processo_aceito"],
  };

  ETAPAS.empenho = {
    nome: "Empenho", numero: "2", servico: "empenho",
    intro: "Reserva a dotação para o credor. O que segue para a OLP é o número do DOCUMENTO do empenho.",
    formulario() {
      const e = E.empenho;
      const marcas = camposExigidos(e.dotacao.elemento, e.dotacao.item);
      const dotacao = G.CAMPOS_DOTACAO.map(([tag, chave, nome]) => campo(`empenho.dotacao.${chave}`, nome, { tag, numerico: true })).join("");
      const adicionais = G.CAMPOS_ADICIONAIS_EMPENHO.map(([tag, nome]) => campo(`empenho.adicionais.${tag}`, nome, { tag, classe: marcas[tag] === "exigido" ? "exigido" : marcas[tag] ? "marcado" : "" })).join("");
      const algumAdicional = Object.values(e.adicionais).some((v) => String(v || "").trim()) || Object.keys(marcas).length;
      return secao("Empenho", `<div class="grade">
          ${campo("empenho.numeroProcesso", "Número do processo", { tag: "numeroProcessoGeral", numerico: true, ajuda: "21 dígitos, da etapa 1." })}
          ${campo("empenho.tipoEmpenho", "Tipo", { tag: "tipoEmpenhoComum", opcoes: [["ORDINARIO", "Ordinário"], ["ESTIMATIVO", "Estimativo"], ["GLOBAL", "Global"]] })}
          ${campo("empenho.valor", "Valor", { tag: "valorEmpenho", dinheiro: true, ph: "1.500,00" })}
          ${campo("empenho.centroCusto", "Centro de custo", { tag: "codigoCc", numerico: true })}
          ${campo("empenho.justificativa", "Justificativa", { tag: "justificativa", tipo: "textarea", inteiro: true })}
        </div>`) +
        secao("Dotação", `<div class="grade">${dotacao}</div>`, "Os nomes aparecem conforme o catálogo de classificação") +
        `<details class="secao" ${algumAdicional ? "open" : ""}><summary style="padding:11px 16px;cursor:pointer;font-weight:600">Campos obrigatórios conforme o caso <span class="nota" style="font-weight:400;color:var(--apagado)">— dependem do elemento-item, do IPU e da fonte; vazios não vão no XML</span></summary><div class="corpo"><div class="grade larga">${adicionais}</div></div></details>`;
    },
    previas() {
      const r = {};
      for (const [, chave] of G.CAMPOS_DOTACAO) {
        const p = previaDotacao(chave, E.empenho.dotacao[chave], E.execucao.uo);
        if (p) r[`empenho.dotacao.${chave}`] = p;
      }
      return r;
    },
    conferir() {
      const e = E.empenho, d = e.dotacao, x = E.execucao;
      let r = faltando([[e.numeroProcesso, "número do processo"], [e.valor, "valor"], [e.centroCusto, "centro de custo"], [e.justificativa, "justificativa"],
        ...G.CAMPOS_DOTACAO.map(([, chave, nome]) => [d[chave], nome])]);
      r = r.concat(conferirExecucao("empenho"), conferirJustificativa(e.justificativa));
      if (dig(e.numeroProcesso) && dig(e.numeroProcesso).length !== 21) r.push(conf("aviso", "O número do processo tem 21 dígitos", `Informado: ${dig(e.numeroProcesso).length} dígitos.`));
      if (e.valor && !temValor(e.valor)) r.push(conf("erro", "Valor inválido", "Use 1.500,00 ou 1500.00."));
      const ei = avaliarElementoItem(d.elemento, d.item, dig(x.sistema));
      if (ei) r.push(ei);
      const marcas = camposExigidos(d.elemento, d.item);
      const sem = G.CAMPOS_ADICIONAIS_EMPENHO.filter(([tag]) => marcas[tag] === "exigido" && !String(e.adicionais[tag] || "").trim()).map(([, nome]) => nome);
      if (sem.length) r.push(conf("erro", "O elemento-item exige campos que estão vazios", sem.join("; "), { caso: "12_erro_25081_campos_obrigatorios_empenho" }));
      const cc = avaliarCentroCusto(x.ua, e.centroCusto);
      if (cc) r.push(cc);
      const nat = conferirNatureza(d);
      if (nat) r.push(nat);
      const previas = this.previas();
      const fora = G.CAMPOS_DOTACAO.filter(([, chave]) => previas[`empenho.dotacao.${chave}`] && !previas[`empenho.dotacao.${chave}`][1]).map(([, , nome]) => nome);
      if (fora.length) r.push(conf("aviso", "Códigos fora das listas do catálogo", fora.join(", "), { fonte: fonteCatalogo(C.classificacao.origem, "classificacao") }));
      const con = avaliarConexao(x.ano, x.uo, d);
      if (con) r.push(con);
      return r;
    },
    xml() {
      const e = E.empenho, x = execXml(), d = e.dotacao;
      const dotacao = {};
      for (const [, chave] of G.CAMPOS_DOTACAO) dotacao[chave] = dig(d[chave]);
      return G.xmlEmpenho({ ...x, numeroRequisicao: requisicao("empenho"), justificativa: G.sanitizarJustificativa(e.justificativa),
        tipoEmpenho: e.tipoEmpenho, numeroProcesso: dig(e.numeroProcesso), credor: dig(E.execucao.credor),
        classificacaoCredor: E.execucao.classificacaoCredor, dotacao, valor: cent(e.valor) != null ? G.valorXml(cent(e.valor)) : "",
        centroCusto: dig(e.centroCusto), adicionais: e.adicionais });
    },
    levar(r) {
      if (!r.numeroDocumento) return;
      E.olp.empenho = r.numeroDocumento; E.reforco.empenho = r.numeroDocumento; E.anulacao_empenho.empenho = r.numeroDocumento;
      if (!E.olp.bruto) E.olp.bruto = E.empenho.valor;
      return ["olp", `Empenho ${r.numeroDocumento} levado para a OLP (e para reforço e anulação)`];
    },
    casos: ["21_empenho_aceito", "12_erro_25081_campos_obrigatorios_empenho", "13_erro_25081_instrumento_entrada_empenho", "19_erro_sistema_do_elemento_item"],
  };

  function liquidoOlp() {
    const o = E.olp;
    const bruto = cent(o.bruto) || 0;
    const inss = o.usarInss ? cent(o.inss) || 0 : 0;
    const issqn = o.usarIssqn ? cent(o.issqn) || 0 : 0;
    return { bruto, inss, issqn, liquido: bruto - inss - issqn };
  }

  ETAPAS.olp = {
    nome: "Liquidação (OLP)", numero: "3", servico: "olp",
    intro: "Liquida o empenho. INSS e ISSQN são retidos aqui; o IRRF não (ele vai na OP).",
    formulario() {
      const o = E.olp, v = liquidoOlp();
      const tipoInss = G.tipoRetencaoInssOlp(E.execucao.credor);
      const municipios = o.regionalizacao.map((m, i) => `<div class="grade">${campo(`olp.regionalizacao.${i}.municipio`, `Município ${i + 1} (IBGE)`, { tag: "codigoMunicipio", numerico: true, ph: "3106200" })}${campo(`olp.regionalizacao.${i}.valor`, "Valor", { tag: "valorDistribuicao", dinheiro: true })}</div>`).join("");
      return secao("OLP", `<div class="grade">
          ${campo("olp.empenho", "Número do empenho", { tag: "numeroDocumentoEmpenho", numerico: true, ajuda: "O documento do empenho (etapa 2)." })}
          ${campo("olp.mesCompetencia", "Mês de competência", { tag: "mesCompetenciaDespesa", numerico: true })}
          ${campo("olp.anoCompetencia", "Ano de competência", { tag: "anoCompetenciaDespesa", numerico: true })}
          ${campo("olp.bruto", "Valor bruto", { tag: "valorBrutoOlp", dinheiro: true })}
          ${campo("olp.justificativa", "Justificativa", { tag: "justificativa", tipo: "textarea", inteiro: true })}
        </div>`) +
        secao("Retenções na OLP", `
          ${liga("olp.usarInss", `INSS (tipo ${tipoInss}: ${tipoInss === "4" ? "credor CPF" : "credor CNPJ"})`)}
          ${o.usarInss ? `<div class="grade">${campo("olp.inss", "Valor do INSS", { tag: "valorRetencao", dinheiro: true })}${campo("olp.credorInss", "Credor da retenção", { tag: "cpfCapfCredorRetencao", numerico: true, ajuda: "29979036000140 = INSS" })}</div>` : ""}
          <div class="bloco-opcional">${liga("olp.usarIssqn", "ISSQN (tipo 13)")}
          ${o.usarIssqn ? `<div class="grade">${campo("olp.issqn", "Valor do ISSQN", { tag: "valorRetencao", dinheiro: true })}${campo("olp.credorIssqn", "Credor da retenção (prefeitura)", { tag: "cpfCapfCredorRetencao", numerico: true, ph: "18715383000140" })}</div>` : ""}</div>
          <div class="resumo-valores"><div>Bruto<strong>${G.valorBr(v.bruto)}</strong></div><div>Retenções<strong>${G.valorBr(v.inss + v.issqn)}</strong></div><div>Líquido (vai para a OP)<strong>${G.valorBr(v.liquido)}</strong></div></div>`,
          "Retenção com valor zero não vai no XML") +
        secao("Regionalização", `${liga("olp.usarRegionalizacao", "Esta despesa exige regionalização (erro 49762 sem ela)")}
          ${o.usarRegionalizacao ? municipios + `<div style="margin-top:10px;display:flex;gap:8px"><button type="button" class="botao pequeno" data-acao="mais-municipio">+ município</button>${o.regionalizacao.length > 1 ? '<button type="button" class="botao pequeno" data-acao="menos-municipio">− último</button>' : ""}</div>` : ""}`);
    },
    conferir() {
      const o = E.olp, v = liquidoOlp();
      let r = faltando([[o.empenho, "número do empenho"], [o.mesCompetencia, "mês"], [o.anoCompetencia, "ano"], [o.bruto, "valor bruto"], [o.justificativa, "justificativa"]]);
      r = r.concat(conferirExecucao("olp"), conferirJustificativa(o.justificativa));
      const mes = parseInt(dig(o.mesCompetencia), 10);
      if (o.mesCompetencia && !(mes >= 1 && mes <= 12)) r.push(conf("erro", "Mês de competência entre 1 e 12"));
      if (o.bruto && !temValor(o.bruto)) r.push(conf("erro", "Valor bruto inválido"));
      if (v.liquido < 0 || (v.bruto && v.liquido === 0)) r.push(conf("erro", "As retenções são iguais ou maiores que o bruto"));
      if (o.usarInss && !dig(o.credorInss)) r.push(conf("erro", "Informe o credor da retenção do INSS"));
      if (o.usarIssqn && !dig(o.credorIssqn)) r.push(conf("erro", "Informe o CNPJ da prefeitura (credor do ISSQN)"));
      if (o.usarRegionalizacao) {
        const soma = o.regionalizacao.reduce((s, m) => s + (cent(m.valor) || 0), 0);
        if (o.regionalizacao.some((m) => dig(m.municipio).length !== 7)) r.push(conf("erro", "Código IBGE do município tem 7 dígitos"));
        if (soma !== v.bruto) r.push(conf("aviso", "A soma dos municípios não fecha o valor bruto", `Soma ${G.valorBr(soma)} · bruto ${G.valorBr(v.bruto)}`));
      }
      return r;
    },
    xml() {
      const o = E.olp, x = execXml(), v = liquidoOlp();
      const credor = dig(E.execucao.credor);
      const retencoes = [];
      if (o.usarInss) retencoes.push({ tipo: G.tipoRetencaoInssOlp(credor), valor: v.inss, credor: dig(o.credorInss) });
      if (o.usarIssqn) retencoes.push({ tipo: G.TIPO_RETENCAO_ISSQN_OLP, valor: v.issqn, credor: dig(o.credorIssqn) });
      return G.xmlOlp({ ...x, numeroRequisicao: requisicao("olp"), mesCompetencia: String(parseInt(dig(o.mesCompetencia), 10) || ""),
        anoCompetencia: dig(o.anoCompetencia), justificativa: G.sanitizarJustificativa(o.justificativa), empenho: dig(o.empenho),
        credor, classificacaoCredor: E.execucao.classificacaoCredor, bruto: v.bruto, liquido: v.liquido, retencoes,
        regionalizacao: o.usarRegionalizacao ? o.regionalizacao.map((m) => ({ municipio: m.municipio, valor: cent(m.valor) || 0 })) : [] });
    },
    levar(r) {
      if (!r.numeroDocumento) return;
      const olp = `${dig(E.execucao.ano)}/${r.numeroDocumento}`;
      E.op.olp = olp; E.anulacao_olp.olp = olp;
      E.op.liquidoOlp = G.valorBr(liquidoOlp().liquido);
      return ["op", `OLP ${olp} levada para a OP`];
    },
    casos: ["22_olp_inss_issqn_aceita", "23_olp_regionalizacao_aceita"],
  };

  const BANCOS_SEM_DV_AGENCIA = { "077": "Inter", "260": "Nubank", "336": "C6" };

  function contaCampos(lado, tagSufixo, ajudaDv) {
    return `<div class="grade">
      ${campo(`op.${lado}.banco`, "Banco", { tag: `codigoBanco${tagSufixo}`, numerico: true, ph: "001" })}
      ${campo(`op.${lado}.agencia`, "Agência", { tag: `codigoAgencia${tagSufixo}`, numerico: true })}
      ${campo(`op.${lado}.dvAgencia`, "DV da agência", { tag: `dvAgencia${tagSufixo}`, ajuda: ajudaDv })}
      ${campo(`op.${lado}.conta`, "Conta", { tag: `codigoConta${tagSufixo}`, numerico: true })}
      ${campo(`op.${lado}.dvConta`, "DV da conta", { tag: `dvConta${tagSufixo}`, ajuda: lado === "creditar" ? "Conta sem DV: vai \"0\"." : "" })}
    </div>`;
  }

  ETAPAS.op = {
    nome: "OP bancária", numero: "4", servico: "op",
    intro: "Paga o credor a partir da OLP. Aqui entram a conta a debitar, a forma de pagamento e o IRRF.",
    formulario() {
      const p = E.op;
      const v = G.valoresOp(cent(p.aPagar) || 0, p.usarIrrf ? cent(p.irrf) || 0 : 0);
      return secao("Origem do pagamento", `<div class="grade">
          ${campo("op.olp", "OLP (ano/número)", { tag: "anoNumeroDaOlpEEmpenho", ph: "2026/57490", ajuda: "O documento da OLP (etapa 3)." })}
          ${campo("op.aPagar", "Valor desta OP", { tag: "valorAPagar", dinheiro: true, ajuda: `Quanto ESTA OP paga (antes do IRRF). Pode ser só uma parte da OLP, mas não pode passar do que falta pagar dela.${p.liquidoOlp ? ` Líquido da OLP: ${h(p.liquidoOlp)} — <a href="#" data-acao="usar-liquido">usar este valor</a>.` : ""}` })}
          ${campo("op.dataProgramada", "Data programada", { tag: "dataProgramadaPagamento", ph: "dd/mm/aaaa" })}
          ${campo("op.justificativa", "Justificativa", { tag: "justificativa", tipo: "textarea", inteiro: true })}
        </div>`) +
        secao("Imposto de Renda (IRRF)", `${liga("op.usarIrrf", "Reter IRRF nesta OP")}
          ${p.usarIrrf ? `<div class="grade">
            ${campo("op.irrf", "Valor do IRRF", { tag: "valorRetencao", dinheiro: true, ajuda: "Informe o valor já calculado: o GRP não calcula a alíquota." })}
            ${campo("op.irrfCodigoReceita", "Código de receita", { tag: "codigoReceita", numerico: true, ajuda: "090140 no exemplo da PRODEMGE (credor pessoa física)." })}
            ${campo("op.irrfCredor", "Credor da retenção", { tag: "cpfCnpjCredorRetencao", numerico: true })}
          </div>` : '<p class="ajuda" style="margin:0;color:var(--apagado)">Sem IRRF, total, líquido e item levam o mesmo valor. Com IRRF, ele vai num bloco &lt;retencao&gt; dentro do item (tipo 10), aceito na produção desde 19/10/2026.</p>'}
          <div class="resumo-valores"><div>Total da OP e do item<strong>${G.valorBr(v.total)}</strong></div><div>IRRF (valorTotalRetencoes)<strong>${G.valorBr(v.retencoes)}</strong></div><div>Líquido (OP e item)<strong>${G.valorBr(v.liquido)}</strong></div></div>`,
          "INSS e ISSQN não vão na OP") +
        secao("Conta a debitar", `${escolha("op.debitarTipo", [["1", "Conta Única do Tesouro", "tipo 1 — sem dados bancários"], ["2", "Conta específica", "tipo 2 — convênios, fundos"]])}
          ${p.debitarTipo === "2" ? `<div style="margin-top:12px">${contaCampos("debitar", "ADebitar", "")}</div>` : ""}
          <div class="grade" style="margin-top:12px">${campo("op.finalidade", "Finalidade do pagamento", { tag: "finalidadePagamento", lista: "lista-finalidades", ajuda: "Exigida com conta específica ou código de barras (erro 38727). Se ficar vazia, a tag não é enviada." })}</div>
          <datalist id="lista-finalidades"><option value="Não se aplica"><option value="Recurso de Convênio"><option value="Contrapartida de Recurso de Convênio"></datalist>`) +
        secao("Forma de pagamento", `${escolha("op.forma", [["001", "Crédito em conta", "forma 001"], ["002", "Código de barras", "forma 002 — boleto ou guia"]])}
          ${p.forma === "002" ? `<div class="grade larga" style="margin-top:12px">${campo("op.codigoBarras", "Código de barras", { tag: "codigoBarras", numerico: true, inteiro: true, ajuda: "Só dígitos. A conta a creditar fica vazia." })}</div>`
            : `<div style="margin-top:12px">${escolha("op.creditarTipo", [["1", "Conta corrente", "tipo 1"], ["2", "Poupança", "tipo 2"]])}</div><div style="margin-top:12px">${contaCampos("creditar", "ACreditar", "Inter, Nubank e C6: deixe vazio (erro 40515).")}</div>`}`);
    },
    conferir() {
      const p = E.op, x = E.execucao;
      let r = faltando([[p.olp, "OLP"], [p.aPagar, "valor a pagar"], [p.dataProgramada, "data programada"], [p.justificativa, "justificativa"]]);
      r = r.concat(conferirExecucao("op"), conferirJustificativa(p.justificativa));
      const olp = G.normalizarOlp(p.olp, dig(x.ano));
      if (p.olp && !/^\d{4}\/\d+$/.test(olp)) r.push(conf("erro", "OLP no formato ano/número", "Ex.: 2026/57490"));
      else if (olp && parseInt(olp, 10) < parseInt(dig(x.ano), 10)) r.push(conf("erro", "OLP de exercício anterior (restos a pagar)", "Toda OLP de ano anterior testada voltou 37144 (getExigeInstrumentoJuridico) pela API. Pela tela do GRP, a OP é gerada normalmente. Caso aberto com a PRODEMGE.", { caso: "10_erro_37144_instrumento_juridico" }));
      if (p.aPagar && !temValor(p.aPagar)) r.push(conf("erro", "Valor a pagar inválido"));
      if (p.dataProgramada && !G.dataXml(p.dataProgramada)) r.push(conf("erro", "Data programada em dd/mm/aaaa"));
      if (p.usarIrrf) {
        if (!temValor(p.irrf)) r.push(conf("erro", "Informe o valor do IRRF"));
        else if (cent(p.irrf) >= (cent(p.aPagar) || 0)) r.push(conf("erro", "O IRRF precisa ser menor que o valor a pagar"));
        if (dig(x.credor).length === 14 && p.irrfCodigoReceita === G.CODIGO_RECEITA_IRRF_PADRAO) r.push(conf("aviso", "Código de receita para credor pessoa jurídica ainda não confirmado", "090140 veio de um exemplo da PRODEMGE com credor pessoa física."));
      }
      const especifica = p.debitarTipo === "2";
      if (especifica && ["banco", "agencia", "conta"].some((k) => !dig(p.debitar[k]))) r.push(conf("erro", "Conta específica: informe banco, agência e conta a debitar", "Ela precisa estar cadastrada como conta de governo; sem esse cadastro, o GRP responde 85910.", { caso: "17_erro_85910_conta_governo" }));
      if ((especifica || p.forma === "002") && !String(p.finalidade || "").trim()) r.push(conf("erro", "Informe a finalidade do pagamento", "Com conta específica ou código de barras o GRP exige (38727). Qualquer texto foi aceito, ex.: Não se aplica."));
      if (p.forma === "002") {
        const barras = dig(p.codigoBarras);
        if (!barras) r.push(conf("erro", "Informe o código de barras"));
        else {
          if (![44, 47, 48].includes(barras.length)) r.push(conf("aviso", "Código de barras costuma ter 44, 47 ou 48 dígitos", `Informado: ${barras.length}.`));
          r.push(conf("aviso", `Boleto do banco ${barras.slice(0, 3)}`, "Alguns bancos não aceitam pagamento por código de barras no GRP (45769): o banco 756 recusou e o 001 aceitou.", { caso: "01_OP_codigo_de_barras_aceita_130321" }));
        }
      } else {
        if (["banco", "agencia", "conta"].some((k) => !dig(p.creditar[k]))) r.push(conf("erro", "Informe banco, agência e conta a creditar"));
        const banco = dig(p.creditar.banco).padStart(3, "0");
        if (BANCOS_SEM_DV_AGENCIA[banco] && String(p.creditar.dvAgencia || "").trim()) r.push(conf("erro", `${BANCOS_SEM_DV_AGENCIA[banco]} não tem DV de agência`, "Deixe o DV da agência vazio (erro 40515)."));
      }
      const ei = elementoItem[`${tres(E.empenho.dotacao.elemento)}/${tres(E.empenho.dotacao.item)}`];
      if (ei && ei.exige_codigo_barra && p.forma !== "002") r.push(conf("erro", `O elemento-item ${ei.elemento}/${ei.item} (do empenho) exige código de barras`, `${ei.tipo_codigo_barra || ""}`, { fonte: fonteCatalogo(C.elemento_item.origem, "elemento") }));
      r.push(conf("ok", "O valor a pagar não pode passar do saldo da OLP", "Pagamentos feitos fora da integração também consomem o saldo (45820 / 36944).", { caso: "15_erro_45820_valor_maior_que_saldo" }));
      return r;
    },
    xml() {
      const p = E.op, x = execXml();
      const conta = (c) => ({ banco: dig(c.banco), agencia: dig(c.agencia), dvAgencia: String(c.dvAgencia || "").trim(), conta: dig(c.conta), dvConta: String(c.dvConta || "").trim() });
      return G.xmlOp({ ...x, numeroRequisicao: requisicao("op"), credor: dig(E.execucao.credor), classificacaoCredor: E.execucao.classificacaoCredor,
        debitar: p.debitarTipo === "2" ? { tipo: "2", ...conta(p.debitar) } : { tipo: "1" },
        creditar: p.forma === "002" ? { tipo: "1" } : { tipo: p.creditarTipo, ...conta(p.creditar) },
        forma: p.forma, codigoBarras: p.forma === "002" ? p.codigoBarras : "", finalidade: String(p.finalidade || "").trim(),
        aPagar: cent(p.aPagar) || 0, irrf: p.usarIrrf ? cent(p.irrf) || 0 : 0, irrfCodigoReceita: dig(p.irrfCodigoReceita),
        irrfCredor: dig(p.irrfCredor), dataProgramada: G.dataXml(p.dataProgramada), justificativa: G.sanitizarJustificativa(p.justificativa),
        olp: G.normalizarOlp(p.olp, dig(E.execucao.ano)) });
    },
    levar(r) {
      if (!r.numeroDocumento) return;
      E.cancelamento.documentoOp = r.numeroDocumento;
      return ["cancelamento", `Documento ${r.numeroDocumento} levado para o cancelamento (se precisar)`];
    },
    casos: ["24_op_conta_unica_aceita", "04_op_irrf_aceita_130905", "25_op_conta_especifica_aceita", "26_op_poupanca_aceita", "01_OP_codigo_de_barras_aceita_130321", "11_erro_37144_saldo_contabil", "16_erro_62229_sistema_da_OLP", "14_erro_36944_sem_saldo_a_pagar"],
  };

  ETAPAS.cancelamento = {
    nome: "Cancelar OP", servico: "cancelamento",
    intro: "Cancela uma OP ainda pendente. Pede o número do DOCUMENTO da OP, não o da solicitação: um número errado cancela outra OP.",
    formulario() {
      return secao("Cancelamento", `<div class="grade">
        ${campo("cancelamento.documentoOp", "Número do documento da OP", { tag: "numeroDocumentoOrdemDePagamento", numerico: true })}
        ${campo("cancelamento.justificativa", "Justificativa", { tag: "justificativa", tipo: "textarea", inteiro: true })}</div>`);
    },
    conferir() {
      const c = E.cancelamento;
      return faltando([[c.documentoOp, "documento da OP"], [c.justificativa, "justificativa"]]).concat(conferirExecucao("cancelamento"), conferirJustificativa(c.justificativa),
        [conf("aviso", "Confira o número do documento antes de enviar", "É o numeroDocumento da resposta da OP (ex.: 116865), não o numeroSolicitacao (ex.: 130321).", { caso: "02_cancelamento_OP_aceito" })]);
    },
    xml() { const c = E.cancelamento; return G.xmlCancelamento({ ...execXml(), numeroRequisicao: requisicao("cancelamento"), documentoOp: dig(c.documentoOp), justificativa: G.sanitizarJustificativa(c.justificativa) }); },
    casos: ["02_cancelamento_OP_aceito", "03_cancelamento_OP_aceito_13-10"],
  };

  ETAPAS.anulacao_olp = {
    nome: "Anular valores na OLP", servico: "anulacao_olp",
    intro: "Anula valores de uma OLP. O sucesso vem como 'Encaminhada para análise', sem número de documento.",
    formulario() {
      return secao("Anulação", `<div class="grade">
        ${campo("anulacao_olp.olp", "OLP (ano/número)", { tag: "numeroOlp", ph: "2026/22606" })}
        ${campo("anulacao_olp.liquido", "Valor líquido anulado", { tag: "valorLiquidoAnulado", dinheiro: true })}
        ${campo("anulacao_olp.total", "Valor total anulado", { tag: "valorTotalAnulado", dinheiro: true, ajuda: "Sem retenções, igual ao líquido." })}
        ${campo("anulacao_olp.justificativa", "Justificativa", { tag: "justificativa", tipo: "textarea", inteiro: true })}</div>`);
    },
    conferir() {
      const a = E.anulacao_olp;
      return faltando([[a.olp, "OLP"], [a.liquido, "líquido anulado"], [a.total, "total anulado"], [a.justificativa, "justificativa"]]).concat(conferirExecucao("anulacao_olp"), conferirJustificativa(a.justificativa));
    },
    xml() {
      const a = E.anulacao_olp, olp = G.normalizarOlp(a.olp, dig(E.execucao.ano));
      return G.xmlAnulacaoOlp({ ...execXml(), ano: olp.split("/")[0] || dig(E.execucao.ano), numeroRequisicao: requisicao("anulacao_olp"),
        numeroOlp: olp.split("/")[1] || "", liquido: cent(a.liquido) || 0, total: cent(a.total) || cent(a.liquido) || 0, justificativa: G.sanitizarJustificativa(a.justificativa) });
    },
    casos: ["32_anulacao_valores_olp_aceita"],
  };

  ETAPAS.reforco = {
    nome: "Reforçar empenho", servico: "reforco",
    intro: "Acrescenta saldo a um empenho. Validado com empenho ESTIMATIVO; ORDINARIO é recusado; GLOBAL ainda não testado.",
    formulario() {
      return secao("Reforço", `<div class="grade">
        ${campo("reforco.empenho", "Número do empenho", { tag: "numeroEmpenho", numerico: true })}
        ${campo("reforco.valor", "Valor do reforço", { tag: "valorReforco", dinheiro: true })}
        ${campo("reforco.justificativa", "Justificativa", { tag: "justificativa", tipo: "textarea", inteiro: true })}</div>`);
    },
    conferir() {
      const a = E.reforco;
      const r = faltando([[a.empenho, "empenho"], [a.valor, "valor"], [a.justificativa, "justificativa"]]).concat(conferirExecucao("reforco"), conferirJustificativa(a.justificativa));
      if (E.empenho.tipoEmpenho === "ORDINARIO" && dig(a.empenho) && dig(a.empenho) === dig(E.olp.empenho)) r.push(conf("erro", "O empenho desta cadeia é ORDINARIO", "Tipo de Empenho não permite reforço."));
      return r;
    },
    xml() { const a = E.reforco; return G.xmlReforco({ ...execXml(), numeroRequisicao: requisicao("reforco"), empenho: dig(a.empenho), valor: cent(a.valor) || 0, justificativa: G.sanitizarJustificativa(a.justificativa) }); },
    casos: ["30_reforco_empenho_aceito"],
  };

  ETAPAS.anulacao_empenho = {
    nome: "Anular empenho", servico: "anulacao_empenho",
    intro: "Anula saldo não liquidado de um empenho. O sucesso vem como 'Encaminhada para análise'.",
    formulario() {
      return secao("Anulação", `<div class="grade">
        ${campo("anulacao_empenho.empenho", "Número do empenho", { tag: "numeroEmpenho", numerico: true })}
        ${campo("anulacao_empenho.valor", "Valor a anular", { tag: "valorAnulacaoEmpenho", dinheiro: true })}
        ${campo("anulacao_empenho.justificativa", "Justificativa", { tag: "justificativa", tipo: "textarea", inteiro: true })}</div>`);
    },
    conferir() {
      const a = E.anulacao_empenho;
      return faltando([[a.empenho, "empenho"], [a.valor, "valor"], [a.justificativa, "justificativa"]]).concat(conferirExecucao("anulacao_empenho"), conferirJustificativa(a.justificativa));
    },
    xml() { const a = E.anulacao_empenho; return G.xmlAnulacaoEmpenho({ ...execXml(), numeroRequisicao: requisicao("anulacao_empenho"), empenho: dig(a.empenho), valor: cent(a.valor) || 0, justificativa: G.sanitizarJustificativa(a.justificativa) }); },
    casos: ["31_anulacao_empenho_aceita"],
  };

  const CADEIA = ["processo", "empenho", "olp", "op"];
  const DEPOIS = ["cancelamento", "anulacao_olp", "reforco", "anulacao_empenho"];
  // Parágrafo "Rótulo curto: texto" ganha o rótulo em negrito.
  const paragrafoMais = (t) => { const m = /^([^:]{3,24}): ([\s\S]*)$/.exec(t); return m ? `<p><strong>${h(m[1])}:</strong> ${h(m[2])}</p>` : `<p>${h(t)}</p>`; };
  const leiaMais = (paragrafos, rotulo = "Leia mais") => `<details class="leia-mais"><summary>${h(rotulo)}</summary>${paragrafos.map(paragrafoMais).join("")}</details>`;

  // Explicação completa das operações de manutenção (aba Início e topo da etapa).
  const DETALHES_ETAPA = {
    cancelamento: { icone: "🚫", mais: [
      "Quando usar: para desfazer uma OP bancária que ainda não foi paga.",
      "O que informar: o número do DOCUMENTO da OP, que vem na resposta da OP (numeroDocumento, ex.: 116865), e uma justificativa. Não use o número da solicitação (numeroSolicitacao, ex.: 130321): a consulta de OPs do GRP pesquisa pela solicitação, mas o cancelamento usa o documento, e um número de documento errado cancela outra OP.",
      "Resultado esperado: situação \"Concluída\", com o número da solicitação de cancelamento (código 54533)."] },
    anulacao_olp: { icone: "↩️", mais: [
      "Quando usar: para reduzir valores de uma OLP já registrada, total ou parcialmente.",
      "O que informar: a OLP (ano/número), o valor líquido anulado, o valor total anulado (igual ao líquido quando não há retenções) e uma justificativa.",
      "Resultado esperado: situação \"Encaminhada para análise\", sem número de documento. A anulação segue para análise no GRP; acompanhe pela tela do GRP."] },
    reforco: { icone: "➕", mais: [
      "Quando usar: para acrescentar saldo a um empenho que já existe.",
      "O que informar: o número do empenho, o valor do reforço e uma justificativa. Não é preciso enviar dotação nem credor: o GRP usa os dados do próprio empenho.",
      "Tipos de empenho: o reforço foi aceito com empenho ESTIMATIVO; com ORDINARIO, o GRP responde \"Tipo de Empenho não permite reforço\"; com GLOBAL, ainda não foi testado.",
      "Resultado esperado: situação \"Encaminhada para análise\", sem número de documento."] },
    anulacao_empenho: { icone: "➖", mais: [
      "Quando usar: para cancelar, total ou parcialmente, o saldo de um empenho que ainda não foi liquidado em OLP, devolvendo o recurso à dotação.",
      "O que informar: o número do empenho, o valor a anular e uma justificativa. Não é preciso enviar dotação nem credor.",
      "Resultado esperado: situação \"Encaminhada para análise\", sem número de documento."] },
  };

  // =================================================================================================================
  // Situação de cada etapa (para a árvore)
  // =================================================================================================================

  function situacao(id) {
    const resposta = E.respostas[id];
    if (resposta) {
      const i = G.interpretar(G.lerResposta(resposta));
      if (i.nivel === "sucesso") return ["ok", "✓ aceita"];
      if (i.nivel === "aviso") return ["aviso", "aceita"];
      return ["erro", "✕ recusada"];
    }
    const lista = ETAPAS[id].conferir();
    if (lista.some((c) => c.nivel === "erro")) return ["neutro", "a preencher"];
    if (lista.some((c) => c.nivel === "aviso")) return ["aviso", "conferir"];
    return ["ligado", "pronta"];
  }

  function ramos(id) {
    if (id === "olp") {
      const o = E.olp;
      return [["Retenções", o.usarInss || o.usarIssqn ? [o.usarInss && "INSS", o.usarIssqn && "ISSQN"].filter(Boolean).join(" + ") : "nenhuma"],
        ["Regionalização", o.usarRegionalizacao ? `${o.regionalizacao.length} município(s)` : "não"]];
    }
    if (id === "op") {
      const p = E.op;
      return [["Conta a debitar", p.debitarTipo === "2" ? "específica" : "Conta Única"],
        ["Forma", p.forma === "002" ? "código de barras" : p.creditarTipo === "2" ? "poupança" : "conta corrente"],
        ["IRRF", p.usarIrrf ? (G.valorBr(cent(p.irrf) || 0) || "sim") : "não"]];
    }
    return [];
  }

  function desenharArvore() {
    const no = (id) => {
      const e = ETAPAS[id];
      const [classe, texto] = situacao(id);
      const ramosHtml = ramos(id).map(([n, v]) => `<button type="button" class="no" data-ir="${id}"><span class="nome">${h(n)}</span><span class="selo neutro">${h(v)}</span></button>`).join("");
      return `<button type="button" class="no estado-${classe}${E.atual === id ? " ativo" : ""}" data-ir="${id}">
          <span class="numero">${h(e.numero || "·")}</span>
          <span class="nome">${h(e.nome)}${e.servico ? `<span class="servico">${h(G.SERVICOS[e.servico].nome)}</span>` : ""}</span>
          <span class="selo ${classe}">${h(texto)}</span></button>${ramosHtml ? `<div class="ramo">${ramosHtml}</div>` : ""}`;
    };
    $("#arvore").innerHTML = `${no("execucao")}<h3>Cadeia da despesa</h3>${CADEIA.map((id, i) => no(id) + (i < CADEIA.length - 1 ? '<div class="ligacao"></div>' : "")).join("")}<h3>Depois da cadeia</h3>${DEPOIS.map(no).join("")}
      <div class="arvore-rodape"><button type="button" class="botao pequeno" data-acao="limpar">Recomeçar do zero</button></div>`;
  }

  // =================================================================================================================
  // Painel da etapa: 1 Preencha · 2 Confira · 3 Envie · 4 Resposta
  // =================================================================================================================

  const ORDEM = ["execucao", ...CADEIA, ...DEPOIS];
  let guiaEnvio = "pagina";

  function passo(numero, titulo, corpo, nota, id) {
    return `<section class="secao passo"${id ? ` id="${id}"` : ""}><header><h3><span class="bolinha">${numero}</span>${h(titulo)}</h3>${nota ? `<span class="nota">${nota}</span>` : ""}</header><div class="corpo">${corpo}</div></section>`;
  }

  function execucaoIncompleta() {
    const x = E.execucao;
    return [x.sistema, x.ano, x.orgao, x.uo, x.ua, x.cpfOrdenador, x.cpfOperador, x.credor, x.classificacaoCredor].some((v) => !String(v || "").trim());
  }

  function desenharEtapa() {
    const id = E.atual, e = ETAPAS[id];
    const servico = e.servico ? G.SERVICOS[e.servico] : null;
    const i = ORDEM.indexOf(id);
    const anterior = ORDEM[i - 1], proxima = ORDEM[i + 1];
    const aviso = id !== "execucao" && execucaoIncompleta()
      ? `<div class="aviso-topo">Faltam dados da execução (órgão, UO, UA, CPFs ou credor). <a href="#" data-ir="execucao">Preencher agora →</a></div>` : "";
    $("#etapa").innerHTML = `<div class="etapa-cabecalho"><div><h2>${e.numero && e.numero !== "◆" ? `Etapa ${e.numero} · ` : ""}${h(e.nome)}</h2>
        ${servico ? `<span class="servico">${h(servico.nome)} · operação ${h(servico.operacao)}${servico.identificador ? " · " + h(servico.identificador) : ""}</span>` : ""}</div></div>
      <p class="etapa-intro">${h(e.intro)}</p>${DETALHES_ETAPA[id] ? `<div class="etapa-intro">${leiaMais(DETALHES_ETAPA[id].mais, "Leia mais sobre esta operação")}</div>` : ""}${aviso}
      ${passo(1, e.xml ? "Preencha" : "Preencha os dados", `<div id="formulario">${e.formulario()}</div>`)}
      <div id="saidas"></div>
      <nav class="navegacao">${anterior ? `<button type="button" class="botao" data-ir="${anterior}">← ${h(ETAPAS[anterior].nome)}</button>` : "<span></span>"}
        ${proxima ? `<button type="button" class="botao principal" data-ir="${proxima}">${h(ETAPAS[proxima].nome)} →</button>` : ""}</nav>`;
    atualizarSaidas();
  }

  function atualizarPrevias() {
    const e = ETAPAS[E.atual];
    $$("[data-previa]").forEach((el) => { el.textContent = ""; el.className = "previa"; });
    if (!e.previas) return;
    for (const [caminho, [texto, ok]] of Object.entries(e.previas())) {
      const el = $(`[data-previa="${caminho}"]`);
      if (el) { el.textContent = texto; el.className = ok ? "previa" : "previa ruim"; }
    }
  }

  function htmlConferencias(lista) {
    if (!lista.length) return '<p class="tudo-certo">✓ Nada a apontar.</p>';
    const ordem = { erro: 0, aviso: 1, ok: 2 };
    const icone = { erro: "✕", aviso: "!", ok: "✓" };
    return `<ul class="conferencias">${lista.slice().sort((a, b) => ordem[a.nivel] - ordem[b.nivel]).map((c) => `<li class="conferencia ${c.nivel}"><span class="icone-conf">${icone[c.nivel]}</span><div><strong>${h(c.titulo)}</strong>${c.texto ? `<p>${h(c.texto)}</p>` : ""}${c.fonte ? `<div class="fonte">${h(c.fonte)}</div>` : ""}${c.caso ? `<div class="fonte"><a href="#" data-caso="${h(c.caso)}">Ver o caso real →</a></div>` : ""}</div></li>`).join("")}</ul>`;
  }

  function resumoConferencias(lista) {
    const erros = lista.filter((c) => c.nivel === "erro").length, avisos = lista.filter((c) => c.nivel === "aviso").length;
    if (erros) return `<span class="selo erro">${erros} para corrigir</span>`;
    if (avisos) return `<span class="selo aviso">${avisos} para conferir</span>`;
    return '<span class="selo ok">tudo certo</span>';
  }

  function blocoCodigo(conteudo, xml) {
    return `<div class="codigo-caixa"><div class="barra-codigo"><span>${xml ? "XML de envio" : "Copie e cole"}</span><button type="button" class="botao pequeno" data-copiar="saida">📋 Copiar</button></div>
      <pre class="codigo${xml ? "" : " quebra"}" id="saida">${xml ? realcarXml(conteudo) : h(conteudo)}</pre></div>`;
  }

  function htmlEnvio(id, e) {
    const xml = e.xml();
    const url = G.endpoint(E.execucao.ambiente, e.servico);
    const cmds = G.comandos(url, xml);
    const guias = [["pagina", "🚀 Pela página"], ["powershell", "PowerShell"], ["curl", "curl"], ["python", "Python"], ["http", "Postman / SoapUI"], ["xml", "Só o XML"]];
    let corpo = "";
    if (guiaEnvio === "pagina") {
      const pendente = E.indeterminado[id];
      corpo = pendente
        ? `<div class="envio-pagina indeterminado"><p><strong>Resultado indeterminado (${h(pendente.quando)}):</strong> ${h(pendente.motivo)}</p>
            <p>O GRP pode ter recebido e registrado a chamada${pendente.numero ? ` (numeroRequisicao <code>${h(pendente.numero)}</code>)` : ""}. Antes de enviar de novo, consulte no GRP se a solicitação existe: as OPs pela tela de consulta de OPs, pelo número da solicitação; os demais documentos, nas telas correspondentes. Se existir, use o número dela e não reenvie.</p>
            <button type="button" class="botao" data-acao="liberar-envio">Conferi no GRP: não foi registrada. Liberar novo envio</button></div>` + blocoCodigo(xml, true)
        : ajudante.ligado
        ? `<div class="envio-pagina ligado"><p><strong>Ajudante de envio ligado.</strong> O XML abaixo vai para <code>${h(url)}</code> pelo curl.exe do seu computador.</p>
            <button type="button" class="botao principal grande" data-acao="enviar">Enviar ao GRP</button><span id="estado-envio" class="estado-envio"></span>
            <p class="ajuda">Fechou a janela do PowerShell? <a href="#" data-acao="copiar-ajudante">Copiar o ajudante de novo</a>.</p></div>` + blocoCodigo(xml, true)
        : `<div class="envio-pagina"><p><strong>Para enviar daqui, ligue o ajudante de envio</strong> (uma vez por sessão; ele roda no seu computador, só aceita esta página e só fala com o GRP):</p>
            <ol><li>Abra o <strong>PowerShell</strong> (menu Iniciar › digite PowerShell).</li>
            <li>Clique em <strong>Copiar o ajudante</strong> abaixo, cole no PowerShell e tecle Enter.</li>
            <li>Deixe a janela aberta e clique em <strong>Verificar</strong>.</li></ol>
            <div class="acoes-linha"><button type="button" class="botao principal" data-acao="copiar-ajudante">📋 Copiar o ajudante</button><button type="button" class="botao" data-acao="verificar-ajudante">↻ Verificar</button><span class="estado-envio">${h(ajudante.mensagem || (ajudante.verificado ? "Ajudante não encontrado." : ""))}</span></div>
            <p class="ajuda">Se o ajudante parar de responder: confira se a janela do PowerShell está aberta e se não foi clicada por dentro (o Windows pausa o programa; tecle Esc). Se fechou, copie e cole de novo.</p>
            <p class="ajuda">Prefere não usar? As outras abas trazem o comando pronto para copiar.</p></div>`;
    } else if (guiaEnvio === "xml") {
      corpo = `<p class="explicacao-envio"><strong>POST</strong> <code>${h(url)}</code> · <code>Content-Type: text/xml; charset=utf-8</code></p>` + blocoCodigo(xml, true);
    } else {
      const explicacao = {
        powershell: "Copie tudo, cole no PowerShell e tecle Enter. A resposta aparece e já fica copiada: volte aqui e cole no passo 4. Usa o curl.exe que vem no Windows 10/11.",
        curl: "Para Linux, macOS ou Git Bash. Copie tudo e cole no terminal.",
        python: "Precisa do pacote requests. Não siga o redirecionamento sozinho: sem www o servidor responde 301 e o POST vira GET.",
        http: "No Postman: método POST, a URL, o cabeçalho e o XML (aba Só o XML) em Body › raw › XML. No SoapUI: importe o WSDL (endereço + ?wsdl) e cole o XML.",
      }[guiaEnvio];
      corpo = `<p class="explicacao-envio">${h(explicacao)}</p>` + blocoCodigo(cmds[guiaEnvio], false);
    }
    return `<nav class="guias">${guias.map(([g, t]) => `<button type="button" class="guia${g === guiaEnvio ? " ativa" : ""}" data-guia="${g}">${h(t)}</button>`).join("")}</nav><div class="corpo-envio">${corpo}</div>
      ${!/<numeroRequisicao>/.test(xml) ? "" : `<p class="rodape-envio">${requisicao(id) ? `Número desta requisição: <code>${h(requisicao(id))}</code> (data e hora AAMMDDhhmmss + ${casasRequisicao(id) === 3 ? "3 dígitos" : "1 dígito"}; usado uma vez só) · <a href="#" data-acao="nova-requisicao">gerar outro</a>` : ""}${E.ultimaCopia[id] ? `<br>A última cópia levou o número <code>${h(E.ultimaCopia[id])}</code>; a próxima cópia ou envio já usa outro.` : ""}</p>`}`;
  }

  function atualizarSaidas() {
    const id = E.atual, e = ETAPAS[id];
    atualizarPrevias();
    const lista = e.conferir();
    let html = passo(2, "Confira", htmlConferencias(lista), resumoConferencias(lista));
    if (e.xml) {
      html += passo(3, "Envie ao GRP", htmlEnvio(id, e), "de dentro da rede do Governo ou da VPN");
      const resposta = E.respostas[id] || "";
      html += passo(4, "Resposta do GRP", `<textarea class="codigo-entrada" rows="4" data-resposta="${id}" placeholder="Cole aqui a resposta que voltou do GRP (ou use Enviar ao GRP, que preenche sozinho)">${h(resposta)}</textarea><div id="interpretacao">${htmlInterpretacao(id, resposta)}</div>`, "", "passo-resposta");
    }
    if (e.casos && e.casos.length) {
      html += `<details class="secao casos-etapa"><summary>📂 Casos reais desta etapa (${e.casos.length})</summary><div class="corpo"><div class="filtros">${e.casos.map((cid) => {
        const c = CASOS[cid];
        return c ? `<a href="#" class="filtro ${c.resultado === "aceito" ? "aceito" : "recusado"}" data-caso="${h(cid)}">${c.resultado === "aceito" ? "✓" : "✕"} ${h(c.titulo)}</a>` : "";
      }).join("")}</div></div></details>`;
    }
    $("#saidas").innerHTML = html;
    desenharArvore();
  }

  function htmlInterpretacao(id, texto) {
    if (!String(texto || "").trim()) return "";
    const r = G.lerResposta(texto);
    const i = G.interpretar(r);
    const etapa = id && ETAPAS[id];
    let acoes = "";
    if (etapa && etapa.levar && i.nivel !== "erro" && (r.numeroDocumento || r.numeroProcesso)) acoes += `<button type="button" class="botao principal" data-acao="levar" data-etapa="${id}">Levar para a próxima etapa →</button>`;
    if (i.caso && CASOS[i.caso]) acoes += `<a href="#" class="botao" data-caso="${h(i.caso)}">Ver um caso real igual</a>`;
    return `<div class="interpretacao ${i.nivel}"><h4>${h(i.titulo)}</h4>${i.dica ? `<p>${h(i.dica)}</p>` : ""}${i.detalhe ? `<pre>${h(i.detalhe)}</pre>` : ""}${acoes ? `<div class="acoes">${acoes}</div>` : ""}</div>`;
  }

  function irPara(id) {
    E.atual = id; salvar(); desenharEtapa();
    $("#painel-montar").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // =================================================================================================================
  // Ajudante de envio (PowerShell local): a página não fala direto com o GRP (o navegador bloqueia), o ajudante sim
  // =================================================================================================================

  const AJUDANTE = "http://127.0.0.1:8765";
  const ajudante = { ligado: false, verificado: false, mensagem: "" };
  if (!E.chaveAjudante) { E.chaveAjudante = Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, "0")).join(""); salvar(); }

  async function verificarAjudante(silencioso) {
    const antes = ajudante.ligado;
    try {
      const controle = new AbortController();
      const t = setTimeout(() => controle.abort(), 4000);
      const r = await fetch(`${AJUDANTE}/status`, { headers: { "X-Chave": E.chaveAjudante }, signal: controle.signal });
      clearTimeout(t);
      ajudante.ligado = r.ok;
    } catch (e) { ajudante.ligado = false; }
    if (ajudante.ligado) ajudante.mensagem = "";
    ajudante.verificado = !silencioso || ajudante.verificado;
    // Sem redesenhar à toa: quem está digitando a resposta perderia o cursor.
    if (ETAPAS[E.atual].xml && guiaEnvio === "pagina" && (!silencioso || antes !== ajudante.ligado)) atualizarSaidas();
  }
  // Mantém a situação do ajudante em dia enquanto a guia "Pela página" está à vista.
  setInterval(() => {
    if ($("#painel-montar").classList.contains("ativo") && guiaEnvio === "pagina" && ETAPAS[E.atual].xml && !document.hidden) verificarAjudante(true);
  }, 10000);

  async function enviarPelaPagina() {
    const id = E.atual, e = ETAPAS[id];
    const estado = $("#estado-envio");
    const botao = $('[data-acao="enviar"]');
    const xml = e.xml();
    const usaNumero = /<numeroRequisicao>/.test(xml);
    const numero = usaNumero ? gastarRequisicao(id) : "";
    botao.disabled = true;
    estado.textContent = "Enviando… (pode levar alguns segundos)";
    const inicio = Date.now();
    try {
      const url = G.endpoint(E.execucao.ambiente, e.servico);
      const r = await fetch(`${AJUDANTE}/enviar?destino=${encodeURIComponent(url)}`, { method: "POST", headers: { "X-Chave": E.chaveAjudante, "Content-Type": "text/plain;charset=utf-8" }, body: xml });
      const texto = await r.text();
      // 504: o curl.exe enviou e não teve resposta (tempo esgotado ou conexão cortada). Não é "não enviou".
      if (r.status === 504) { marcarIndeterminado(id, numero, texto); return; }
      if (!r.ok) {
        ajudante.ligado = r.status !== 403 || !/chave/.test(texto);
        ajudante.mensagem = `O ajudante não enviou: ${texto}`;
        atualizarSaidas(); return;
      }
      E.respostas[id] = texto || `(resposta vazia, HTTP ${r.headers.get("X-Grp-Status") || "?"})`;
      delete E.indeterminado[id];
      novaRequisicaoDepois(id);
      salvar();
      atualizarSaidas();
      $("#passo-resposta").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      ajudante.ligado = false;
      // Falha imediata = o ajudante não estava lá (nada saiu). Falha depois de um tempo = ele parou no meio do envio,
      // e o GRP pode ter recebido.
      if (Date.now() - inicio > 1500) { marcarIndeterminado(id, numero, "o ajudante parou de responder durante o envio."); return; }
      ajudante.mensagem = "O ajudante parou de responder.";
      atualizarSaidas();
    }
  }

  function marcarIndeterminado(id, numero, motivo) {
    E.indeterminado[id] = { numero, motivo, quando: new Date().toLocaleString("pt-BR") };
    salvar();
    atualizarSaidas();
  }

  // Eventos do montador (delegação)
  const painel = $("#painel-montar");
  painel.addEventListener("input", (ev) => {
    const alvo = ev.target;
    if (alvo.dataset.caminho) {
      definir(alvo.dataset.caminho, alvo.value); salvar();
      if (alvo.tagName === "SELECT" || /dotacao\.(elemento|item)$|execucao\.credor$|op\.irrf$|olp\.(bruto|inss|issqn)$|op\.aPagar$/.test(alvo.dataset.caminho)) {
        // campos que mudam o próprio formulário (tipo de INSS, resumos, campos exigidos)
        const foco = alvo.dataset.caminho, pos = alvo.selectionStart;
        $("#formulario").innerHTML = ETAPAS[E.atual].formulario();
        const novo = $(`[data-caminho="${foco}"]`);
        if (novo) { novo.focus(); try { novo.setSelectionRange(pos, pos); } catch (e) { /* select */ } }
      }
      atualizarSaidas();
    } else if (alvo.dataset.resposta) {
      const id = alvo.dataset.resposta;
      const antes = E.respostas[id];
      E.respostas[id] = alvo.value;
      if (alvo.value.trim() && !String(antes || "").trim()) { novaRequisicaoDepois(id); delete E.indeterminado[id]; }
      salvar();
      $("#interpretacao").innerHTML = htmlInterpretacao(id, alvo.value);
      desenharArvore();
    }
  });

  /** Depois que uma resposta chega, a próxima tentativa desta etapa precisa de outro número de requisição. */
  function novaRequisicaoDepois(id) { delete E.req[id]; }

  painel.addEventListener("change", (ev) => {
    const alvo = ev.target;
    if (alvo.dataset.liga) { definir(alvo.dataset.liga, alvo.checked); salvar(); desenharEtapa(); }
  });

  painel.addEventListener("click", (ev) => {
    const alvo = ev.target.closest("[data-ir],[data-escolha],[data-guia],[data-acao],[data-copiar],[data-caso]");
    if (!alvo) return;
    if (alvo.dataset.caso) { ev.preventDefault(); abrirCaso(alvo.dataset.caso); return; }
    if (alvo.dataset.ir) { ev.preventDefault(); irPara(alvo.dataset.ir); return; }
    if (alvo.dataset.escolha) { definir(alvo.dataset.escolha, alvo.dataset.valor); salvar(); desenharEtapa(); return; }
    if (alvo.dataset.guia) { guiaEnvio = alvo.dataset.guia; atualizarSaidas(); if (guiaEnvio === "pagina") verificarAjudante(true); return; }
    if (alvo.dataset.copiar) {
      const el = $("#" + alvo.dataset.copiar); copiar(el.textContent);
      if (alvo.dataset.copiar === "saida" && ETAPAS[E.atual].xml && /<numeroRequisicao>/.test(el.textContent)) { E.ultimaCopia[E.atual] = gastarRequisicao(E.atual); atualizarSaidas(); }
      return;
    }
    const acao = alvo.dataset.acao;
    if (acao === "enviar") enviarPelaPagina();
    else if (acao === "copiar-ajudante") copiar(D.ajudante.replace("__CHAVE__", E.chaveAjudante));
    else if (acao === "verificar-ajudante") verificarAjudante(false);
    else if (acao === "nova-requisicao") { ev.preventDefault(); novaRequisicao(E.atual); atualizarSaidas(); }
    else if (acao === "liberar-envio") { delete E.indeterminado[E.atual]; salvar(); atualizarSaidas(); }
    else if (acao === "usar-liquido") { ev.preventDefault(); E.op.aPagar = E.op.liquidoOlp; salvar(); desenharEtapa(); }
    else if (acao === "mais-municipio") { E.olp.regionalizacao.push({ municipio: "", valor: "" }); salvar(); desenharEtapa(); }
    else if (acao === "menos-municipio") { E.olp.regionalizacao.pop(); salvar(); desenharEtapa(); }
    else if (acao === "levar") {
      const id = alvo.dataset.etapa;
      const r = G.lerResposta(E.respostas[id]);
      const resultado = ETAPAS[id].levar(r);
      if (resultado) { salvar(); avisoCopiado(resultado[1]); irPara(resultado[0]); }
    } else if (acao === "limpar") {
      if (confirm("Apagar todos os dados preenchidos e as respostas coladas neste navegador?")) { E = mesclar(PADRAO, {}); E.op.dataProgramada = hoje(); salvar(); desenharEtapa(); }
    }
  });

  // =================================================================================================================
  // Início: ciclo da despesa e o que precisa existir no GRP
  // =================================================================================================================

  // [ícone, título, resumo, o que aparece quando falta, explicação completa (parágrafos)]
  const REQUISITOS = [
    ["🌐", "Rede do Governo ou VPN", "O GRP só responde de dentro da rede do Governo de Minas ou pela VPN.",
      "o envio demora e termina sem resposta, ou volta uma página de \"serviço indisponível\".",
      ["Os Web Services do GRP ficam na rede interna do Governo de Minas. Fora dela (em casa ou na internet comum), conecte-se à VPN do seu órgão antes de enviar.",
        "Em alguns computadores, a borda da PRODEMGE recusa a conexão feita pelo Python e aceita a do curl.exe do Windows. Por isso o ajudante de envio e o comando de PowerShell desta página usam o curl.exe."]],
    ["🔑", "Sistema de origem autorizado", "O código do seu sistema, o mesmo em todas as etapas da execução.",
      "o erro 62229 — Documento não permitido, a solicitação deve ser registrada via outro sistema.",
      ["Cada sistema integrado ao GRP tem um código, autorizado pela PRODEMGE/STE. Ele vai em codigoSistemaOrigem (no processo, em codigoSistemaSolicitante). O sistema 51 é a Nota Fiscal Mineira.",
        "Todas as etapas de uma mesma execução usam o mesmo código. Documentos registrados pela tela do GRP podem continuar pela API: por exemplo, uma OP enviada pela API sobre uma OLP registrada na tela.",
        "O Portal de Compras (sistema 2) só empenha e liquida. A OP de documentos do Portal de Compras é feita pela tela do GRP, mesmo quando a execução começou pela API.",
        "Não use o código de outro sistema sem autorização da PRODEMGE/STE."]],
    ["✍️", "Ordenador com exceção de assinatura", "Em todas as fases (empenho, OLP e OP), na UA executora.",
      "a resposta sem número de documento: a solicitação fica parada, aguardando aprovação no GRP.",
      ["O CPF informado como ordenador de despesa (cpfOrdenadorDespesa) precisa estar cadastrado no GRP com perfil de exceção de assinatura para o empenho, a OLP e a OP, na UA que executa a despesa.",
        "Com a exceção, o GRP registra e aprova o documento na própria resposta da chamada, e a assinatura formal fica para depois, no portal. Sem ela, cada etapa fica aguardando assinatura manual e a execução não continua pela API."]],
    ["👤", "Ordenador autorizado na UO/UA no exercício", "Autorização do ordenador para a UO e a UA informadas, no ano da chamada.",
      "o erro 0 — Ordenador de despesa não está autorizado para UO …, UA …",
      ["Além da exceção de assinatura, o ordenador precisa estar autorizado a ordenar despesas na UO e na UA informadas na chamada.",
        "A autorização vale por exercício: um ordenador autorizado no ano anterior pode não estar autorizado no ano atual. Confira o cadastro do ordenador no GRP."]],
    ["💰", "Programação orçamentária e financeira", "Saldo aprovado para a dotação (UO, classificação, fonte e IPU).",
      "o empenho recusado com uma mensagem sobre programação orçamentária.",
      ["A UA precisa de cotas vigentes de programação orçamentária (crédito disponível na dotação) e de programação financeira (recurso financeiro descentralizado), aprovadas no GRP.",
        "A cota tem de existir para a combinação exata usada no empenho: UO, classificação orçamentária, grupo, fonte e IPU. Na etapa Empenho, a página mostra as combinações de grupo, fonte e IPU já usadas pela UO no catálogo."]],
    ["🏷️", "Credor cadastrado", "Com a classificação escrita exatamente como no cadastro, com acento.",
      "o erro 85910 — valor não cadastrado no GRP.",
      ["O credor (CPF ou CNPJ) precisa estar cadastrado no GRP antes da chamada, com a sua classificação cadastral (por exemplo, BENEFICIÁRIOS DIVERSOS ou PRESTADOR DE SERVIÇOS).",
        "Na chamada, a classificação do credor tem de ser escrita exatamente como no cadastro, inclusive com acento. Se o favorecido ainda não existir, cadastre-o no GRP antes de enviar."]],
    ["📦", "Elemento-item liberado e parametrizado", "Liberado para o seu sistema e com parametrização contábil no exercício.",
      "o erro 0 — Sistema … diferente do sistema do elemento-item, ou a mensagem \"Natureza item da despesa não possui parametrização contábil\".",
      ["Cada elemento-item de despesa (por exemplo, 039/018) tem um sistema dono e campos que passam a ser exigidos. Ele precisa estar liberado para o sistema que envia a chamada.",
        "A combinação de órgão, elemento e item também precisa de parametrização contábil ativa no plano de contas do GRP para o exercício. Se faltar, acione a Subsecretaria do Tesouro Estadual (STE/SEF) para regularizar.",
        "Na etapa Empenho, a página confere o sistema dono e os campos exigidos no catálogo de elemento-item."]],
    ["🔢", "Um número de requisição por chamada", "Um número novo a cada envio, montado com a data e a hora.",
      "a recusa da chamada: o GRP não aceita número repetido.",
      ["O numeroRequisicao identifica cada chamada, para que o GRP não registre o mesmo pedido duas vezes. Use um número novo a cada envio, só com dígitos.",
        "Formato usado pela página: data e hora até os segundos (AAMMDDhhmmss) + dígitos sorteados. Na OP, 3 dígitos (15 no total, ex.: 261027113130482), formato aceito em OP em 27/10/2026. Nos demais serviços, 1 dígito (13 no total, ex.: 2610271131304) até o teste com 15. Números de 17 a 18 dígitos foram recusados.",
        "Para dois envios terem o mesmo número, precisariam sair no mesmo segundo e sortear os mesmos dígitos. Neste navegador a página nunca repete um número, mesmo com vários cliques no mesmo segundo."]],
    ["⏱️", "Sem resposta? Consulte antes de reenviar", "A solicitação pode ter sido gravada mesmo sem resposta.",
      "o mesmo documento gerado duas vezes.",
      ["Quando o envio termina por tempo esgotado, o GRP pode ter registrado a solicitação mesmo assim. Antes de reenviar, consulte no GRP: as OPs são pesquisadas pelo número da solicitação.",
        "Entre 23h55 e 0h30, o GRP pode bloquear o processamento durante a cópia dos dados para o armazém. Nesse caso, aguarde e envie de novo a mesma chamada."]],
  ];
  // Do impacto mais curto ao mais longo: cartões de altura parecida ficam juntos e sobra menos espaço em branco.
  REQUISITOS.sort((a, b) => a[3].length - b[3].length);
  $("#requisitos").innerHTML = `<div class="requisitos">${REQUISITOS.map(([icone, t, d, sintoma, mais]) => `<div class="requisito"><span class="icone">${icone}</span><div><strong>${h(t)}</strong><p>${h(d)}</p><p class="sintoma"><strong>Impacto da ausência:</strong> ${h(sintoma)}</p>${leiaMais(mais)}</div></div>`).join("")}</div>`;
  $("#manutencoes").innerHTML = `<div class="requisitos">${DEPOIS.map((id) => `<div class="requisito"><span class="icone">${DETALHES_ETAPA[id].icone}</span><div><strong>${h(ETAPAS[id].nome)}</strong><p>${h(ETAPAS[id].intro)}</p><div class="fim-cartao"><p class="abrir"><a href="#" data-ir-etapa="${id}">Abrir esta operação →</a></p>${leiaMais(DETALHES_ETAPA[id].mais)}</div></div></div>`).join("")}</div>`;

  const CICLO = [
    ["1", "Número de processo", "GerarNumeroProcessoGrpWS", "Abre o processo eletrônico", "nº do processo (21 dígitos)"],
    ["2", "Empenho", "SolicitacaoEmpenhoWS", "Reserva a dotação para o credor", "nº do documento do empenho"],
    ["3", "Liquidação (OLP)", "SolicitacaoOlpWS", "Liquida o empenho; retém INSS e ISSQN", "nº do documento da OLP"],
    ["4", "OP bancária", "SolicOrdemPagamentoBancariaWS", "Paga o credor; retém o IRRF", "nº da solicitação e do documento da OP"],
  ];
  $("#ciclo").innerHTML = `<div class="ciclo">${CICLO.map(([n, nome, ws, faz, sai], i) => `<button type="button" class="ciclo-etapa" data-ir-etapa="${CADEIA[i]}"><span class="bolinha">${n}</span><strong>${h(nome)}</strong><code>${h(ws)}</code><span>${h(faz)}</span><span class="saida">Devolve: ${h(sai)}</span></button>${i < CICLO.length - 1 ? '<span class="seta" aria-hidden="true">→</span>' : ""}`).join("")}</div>
    <p class="texto-secao">Não é preciso fazer todas as etapas pela API. Se um documento já foi registrado pela tela do GRP, comece pela etapa seguinte usando o número dele: por exemplo, uma OP pela API sobre uma OLP registrada na tela. A exceção são os documentos do Portal de Compras (sistema 2), cuja OP é feita pela tela do GRP.</p>`;

  // =================================================================================================================
  // Casos reais
  // =================================================================================================================

  const CASOS = {};
  for (const c of D.casos) CASOS[c.id] = c;
  const ROTULO_ETAPA = { processo: "Processo", empenho: "Empenho", olp: "OLP", op: "OP", cancelamento: "Cancelamento de OP", reforco: "Reforço", anulacao_empenho: "Anulação de empenho", anulacao_olp: "Anulação na OLP" };
  let filtroEtapa = "todas", filtroResultado = "todos";

  function desenharCasos() {
    const etapas = ["todas", ...Object.keys(ROTULO_ETAPA)];
    $("#filtros-casos").innerHTML = etapas.map((e) => `<button type="button" class="filtro${filtroEtapa === e ? " ativo" : ""}" data-filtro-etapa="${e}">${e === "todas" ? "Todas as etapas" : ROTULO_ETAPA[e]}</button>`).join("") +
      '<span style="width:12px"></span>' + [["todos", "Todos"], ["aceito", "Aceitos"], ["erro", "Erros"]].map(([v, t]) => `<button type="button" class="filtro${filtroResultado === v ? " ativo" : ""}" data-filtro-resultado="${v}">${t}</button>`).join("");
    const lista = D.casos.filter((c) => (filtroEtapa === "todas" || c.etapa === filtroEtapa) && (filtroResultado === "todos" || c.resultado === filtroResultado));
    $("#lista-casos").innerHTML = lista.map((c) => `<details class="caso" id="caso-${h(c.id)}">
      <summary><span class="selo ${c.resultado === "aceito" ? "ok" : "erro"}">${c.resultado === "aceito" ? "aceito" : "erro"} ${h(c.codigos.join(" · "))}</span>
        <span><span class="titulo">${h(c.titulo)}</span><br><span class="meta">${h(ROTULO_ETAPA[c.etapa])} · ${h(c.data)}</span></span><span class="meta">▾</span></summary>
      <p class="licao">${h(c.licao)}</p>
      <div class="pares mostra-envio"><div class="guias-caso" role="tablist"><button type="button" class="guia ativa" data-ver="envio">📤 Envio</button><button type="button" class="guia" data-ver="resposta">📥 Resposta do GRP</button></div>
      <div class="lado envio">${c.ajustes.length ? `<div class="aviso-historico"><p><strong>XML no formato atual.</strong> O envio de ${h(c.data)} foi ajustado ao contrato de hoje, com os mesmos valores: ${h(c.ajustes.join("; ").replace(/`/g, ""))}.</p>
        <details><summary>Ver o XML como foi enviado em ${h(c.data)}</summary><pre class="codigo">${realcarXml(c.envio_original)}</pre></details></div>` : ""}<pre class="codigo">${realcarXml(c.envio)}</pre></div>
      <div class="lado resposta">${c.formato_resposta === "json" ? '<p class="ajuda">Esta resposta foi registrada em JSON (os campos do &lt;return&gt;).</p>' : ""}<pre class="codigo">${c.formato_resposta === "json" ? h(c.resposta) : realcarXml(c.resposta)}</pre></div></div></details>`).join("") || '<p class="vazio">Nenhum caso com esses filtros.</p>';
  }

  $("#painel-casos").addEventListener("click", (ev) => {
    const v = ev.target.closest("[data-ver]");
    if (v) {
      const pares = v.closest(".pares");
      pares.className = "pares mostra-" + v.dataset.ver;
      pares.querySelectorAll("[data-ver]").forEach((x) => x.classList.toggle("ativa", x === v));
      return;
    }
    const b = ev.target.closest("[data-filtro-etapa],[data-filtro-resultado]");
    if (!b) return;
    if (b.dataset.filtroEtapa) filtroEtapa = b.dataset.filtroEtapa; else filtroResultado = b.dataset.filtroResultado;
    desenharCasos();
  });

  function abrirCaso(id) {
    filtroEtapa = "todas"; filtroResultado = "todos";
    trocarAba("casos"); desenharCasos();
    const el = document.getElementById("caso-" + id);
    if (el) { el.open = true; el.scrollIntoView({ behavior: "smooth", block: "start" }); }
  }

  // =================================================================================================================
  // Respostas e erros
  // =================================================================================================================

  const OUTROS_CODIGOS = [
    ["0", "Erro de regra de negócio", "'Erro inesperado. Causa: ...' (ex.: ordenador não autorizado na UO/UA) ou 'Sistema ... diferente do sistema do elemento-item' ou 'Tipo de Empenho não permite reforço'. Leia a causa.", "19_erro_sistema_do_elemento_item"],
    ["48860", "Usuário sem acesso à unidade administrativa", "Operador ou ordenador sem acesso à UA informada."],
    ["41040", "Sucesso (empenho, OLP e manutenções)", "Nas manutenções a situação vem 'Encaminhada para análise', sem número de documento.", "21_empenho_aceito"],
    ["51424", "Sucesso (OP)", "Guarde o número da solicitação (pesquisável no GRP) e o do documento (usado no cancelamento).", "24_op_conta_unica_aceita"],
    ["54533", "Sucesso (cancelamento de OP)", "Volta 'Concluída' com numeroSolicitacaoDeCancelamentoOP.", "02_cancelamento_OP_aceito"],
    ["HTTP 500", "SOAP Fault: Unmarshalling Error", "'elemento inesperado' = tag fora do contrato; 'For input string' = campo numérico vazio ou com texto. Nenhum documento foi gerado."],
    ["HTTP 301", "Endereço sem www", "Use https://www.grp.servicos.mg.gov.br ou reenvie o POST ao endereço do Location."],
    ["—", "Página de indisponibilidade", "Fora da rede do Governo/VPN, ou borda da PRODEMGE recusando o TLS do cliente (use o curl.exe do Windows)."],
  ];

  function desenharCodigos() {
    const termo = ($("#busca-codigos").value || "").toLowerCase();
    const linhas = Object.entries(G.CODIGOS).map(([c, [t, d, caso]]) => [c, t, d, caso]).concat(OUTROS_CODIGOS)
      .filter((l) => l.join(" ").toLowerCase().includes(termo));
    $("#lista-codigos").innerHTML = `<div class="tabela-rolagem"><table><thead><tr><th>Código</th><th>O que é</th><th>O que fazer</th><th>Caso real</th></tr></thead><tbody>${linhas.map(([c, t, d, caso]) => `<tr><td><code>${h(c)}</code></td><td>${h(t)}</td><td>${h(d)}</td><td>${caso && CASOS[caso] ? `<a href="#" data-caso="${h(caso)}">${h(CASOS[caso].data)}</a>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
  }
  $("#busca-codigos").addEventListener("input", desenharCodigos);
  $("#resposta-avulsa").addEventListener("input", (ev) => { $("#interpretacao-avulsa").innerHTML = htmlInterpretacao(null, ev.target.value); });
  $("#painel-respostas").addEventListener("click", (ev) => { const a = ev.target.closest("[data-caso]"); if (a) { ev.preventDefault(); abrirCaso(a.dataset.caso); } });

  // =================================================================================================================
  // Contrato e dicionário
  // =================================================================================================================

  const TIPOS_DO_SERVICO = {
    processo: ["GerarNumeroProcessoGrpWS", ["gerarNumeroProcessoGrp"]],
    empenho: ["SolicitacaoEmpenhoWS", ["gerarSolicitacaoEmpenhoRequest", "olpPendenteCreditoNaoRegularizarRequest"]],
    olp: ["SolicitacaoOlpWS", ["solicitacaoOlpRequest", "olpDeEmpenhoRequest", "valoresDaOlpRequest", "retencaoOlpRequest", "regionalizacaoDespesaOlpRequest"]],
    op: ["SolicOrdemPagamentoBancariaWS", ["solicitacaoOrdemPagamentoBancariaRequest", "itemDePagamentoSolicOrdemRequest", "retencaoOrdemPagamentoRequest"]],
    cancelamento: ["CancelamentoOrdemPagamentoBancariaWS", ["cancelamentoOrdemPagamentoBancariaRequest"]],
    anulacao_olp: ["SolicitacaoAnulacaoValoresNaOlpWS", ["solicitarAnulacaoValoresNaOLPRequest"]],
    reforco: ["SolicitacaoReforcoDeEmpenhoWS", ["gerarSolicitacaoReforcoEmpenhoRequest"]],
    anulacao_empenho: ["SolicitacaoAnulacaoEmpenhoWS", ["gerarSolicitacaoAnulacaoSaldoEmpenhoRequest"]],
  };
  // Nomes dos grupos de campos (os "tipos" do WSDL) em português.
  const NOME_GRUPO = {
    gerarNumeroProcessoGrp: "Pedido do número do processo",
    gerarSolicitacaoEmpenhoRequest: "Dados do empenho",
    olpPendenteCreditoNaoRegularizarRequest: "OLP pendente de crédito (não regularizar)",
    solicitacaoOlpRequest: "Dados gerais da OLP",
    olpDeEmpenhoRequest: "Empenho que a OLP liquida",
    valoresDaOlpRequest: "Valores da OLP",
    retencaoOlpRequest: "Cada retenção da OLP (INSS, ISSQN…)",
    regionalizacaoDespesaOlpRequest: "Cada município da regionalização",
    solicitacaoOrdemPagamentoBancariaRequest: "Dados gerais da OP",
    itemDePagamentoSolicOrdemRequest: "Cada item de pagamento (a OLP paga)",
    retencaoOrdemPagamentoRequest: "Cada retenção da OP (IRRF)",
    cancelamentoOrdemPagamentoBancariaRequest: "Dados do cancelamento",
    solicitarAnulacaoValoresNaOLPRequest: "Dados da anulação na OLP",
    gerarSolicitacaoReforcoEmpenhoRequest: "Dados do reforço",
    gerarSolicitacaoAnulacaoSaldoEmpenhoRequest: "Dados da anulação do empenho",
  };
  // Tipos do WSDL em palavras de gente.
  function tipoLegivel(tipo) {
    if (tipo === "xs:string") return "texto";
    if (tipo === "xs:int" || tipo === "xs:long") return "número inteiro";
    if (tipo === "xs:decimal") return "valor (ponto decimal)";
    if (tipo === "xs:dateTime") return "data e hora";
    if (tipo === "xs:base64Binary") return "arquivo (base64)";
    if (tipo === "-") return "lista de grupos";
    if (tipo.startsWith("tns:")) return "grupo de campos";
    return tipo;
  }
  const DIC = {};
  for (const t of D.dicionario) DIC[t.tag] = t;
  let servicoContrato = "op";

  function tagsDoXml(xml) { return new Set(Array.from(String(xml).matchAll(/<(?:\w+:)?(\w+)>/g), (m) => m[1])); }

  function desenharContrato() {
    $("#origem-contrato").textContent = `${D.contrato.origem}. Campos em azul: os que a árvore envia hoje nesta etapa.`;
    $("#servicos-contrato").innerHTML = Object.keys(TIPOS_DO_SERVICO).map((s) => `<button type="button" class="filtro${servicoContrato === s ? " ativo" : ""}" data-servico="${s}">${h(ETAPAS[s].nome)}</button>`).join("");
    const [nomeServico, tipos] = TIPOS_DO_SERVICO[servicoContrato];
    const usados = tagsDoXml(ETAPAS[servicoContrato].xml());
    const contrato = D.contrato.servicos[nomeServico] || {};
    const linhas = tipos.filter((t) => contrato[t]).map((t) => `<tr class="subtipo"><td colspan="4">${h(NOME_GRUPO[t] || t)} <code>${h(t)}</code></td></tr>` +
      contrato[t].map(([nome, tipo, min, max]) => `<tr class="${usados.has(nome) ? "usado" : ""}"><td><code>${h(nome)}</code></td>
        <td class="tipo" title="${h(tipo)}">${h(tipoLegivel(tipo))}</td>
        <td class="preenchimento">${min !== "0" ? '<span class="obrigatorio">obrigatório</span>' : '<span class="opcional">opcional</span>'}${max === "unbounded" ? '<br><span class="repete">pode repetir</span>' : ""}</td>
        <td>${DIC[nome] ? h(DIC[nome].conceito) : '<span class="sem-descricao">Sem descrição ainda: o contrato prevê este campo, mas nenhum teste o usou.</span>'}</td></tr>`).join("")).join("");
    $("#tabela-contrato").innerHTML = `<div class="tabela-rolagem"><table class="tabela-contrato"><thead><tr><th>Campo (tag)</th><th>Tipo</th><th>Preenchimento</th><th>O que é</th></tr></thead><tbody>${linhas}</tbody></table></div>`;
  }
  $("#servicos-contrato").addEventListener("click", (ev) => { const b = ev.target.closest("[data-servico]"); if (b) { servicoContrato = b.dataset.servico; desenharContrato(); } });

  function desenharDicionario() {
    const termo = ($("#busca-dicionario").value || "").toLowerCase();
    const linhas = D.dicionario.filter((t) => `${t.tag} ${t.conceito} ${t.regra} ${t.contrato}`.toLowerCase().includes(termo));
    $("#lista-dicionario").innerHTML = `<div class="tabela-rolagem"><table><thead><tr><th>Campo (tag)</th><th>O que é</th><th>No contrato atual</th><th>Como preencher</th></tr></thead><tbody>${linhas.map((t) => `<tr><td><code>${h(t.tag)}</code></td><td>${h(t.conceito)}</td><td class="contrato-tag">${h(t.contrato).replace(/ \| /g, "<br>")}</td><td>${h(t.regra)}</td></tr>`).join("")}</tbody></table></div>`;
  }
  $("#busca-dicionario").addEventListener("input", desenharDicionario);

  // =================================================================================================================
  // Abas e início
  // =================================================================================================================

  function trocarAba(aba) {
    $$(".aba").forEach((b) => b.classList.toggle("ativa", b.dataset.aba === aba));
    $$(".painel").forEach((p) => p.classList.toggle("ativo", p.id === "painel-" + aba));
    if (aba === "contrato") desenharContrato();
    window.scrollTo({ top: 0 });
  }
  $$(".aba").forEach((b) => b.addEventListener("click", () => trocarAba(b.dataset.aba)));
  $("#painel-inicio").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-ir-aba],[data-ir-etapa]");
    if (!b) return;
    if (b.dataset.irEtapa) { E.atual = b.dataset.irEtapa; salvar(); desenharEtapa(); trocarAba("montar"); }
    else trocarAba(b.dataset.irAba);
  });
  // Tema: Automático (segue o sistema) → Claro → Escuro. Guardado só neste navegador.
  const TEMAS = [["auto", "🌓 Automático"], ["claro", "☀️ Claro"], ["escuro", "🌙 Escuro"]];
  function aplicarTema(tema) {
    if (tema === "auto") delete document.documentElement.dataset.tema; else document.documentElement.dataset.tema = tema;
    $("#trocar-tema").textContent = TEMAS.find(([t]) => t === tema)[1];
    try { localStorage.setItem("arvore-grp-tema", tema); } catch (e) { /* sem armazenamento */ }
  }
  aplicarTema(document.documentElement.dataset.tema || "auto");
  $("#trocar-tema").addEventListener("click", () => {
    const atual = document.documentElement.dataset.tema || "auto";
    aplicarTema(TEMAS[(TEMAS.findIndex(([t]) => t === atual) + 1) % TEMAS.length][0]);
  });

  // Dúvidas e sugestões: monta o e-mail (a página não envia nada sozinha).
  const EMAIL_CONTATO = "nicole.peixoto@fazenda.mg.gov.br";
  const EMAIL_COPIA = ["steplanejamento@fazenda.mg.gov.br", "digi@fazenda.mg.gov.br"];
  function textoContato() {
    const tipo = $("#contato-tipo").value, nome = $("#contato-nome").value.trim(), msg = $("#contato-mensagem").value.trim();
    const assunto = `[Árvore da API do GRP] ${tipo}`;
    const corpo = `${msg}\n\n—\n${nome ? `De: ${nome}\n` : ""}Página: Árvore Interativa da API do GRP, versão ${D.versao || ""}`;
    return { assunto, corpo, msg };
  }
  $("#abrir-contato").addEventListener("click", () => $("#contato").showModal());
  $("#contato-fechar").addEventListener("click", () => $("#contato").close());
  $("#contato-copiar").addEventListener("click", () => { const t = textoContato(); copiar(`Para: ${EMAIL_CONTATO}\nCc: ${EMAIL_COPIA.join("; ")}\nAssunto: ${t.assunto}\n\n${t.corpo}`); });
  $("#contato-enviar").addEventListener("click", () => {
    const t = textoContato();
    if (!t.msg) { $("#contato-mensagem").focus(); return; }
    const link = $("#contato-link");
    link.href = `mailto:${EMAIL_CONTATO}?cc=${encodeURIComponent(EMAIL_COPIA.join(","))}&subject=${encodeURIComponent(t.assunto)}&body=${encodeURIComponent(t.corpo)}`;
    link.click();
    $("#contato").close();
  });

  $("#baixar-manual").addEventListener("click", () => baixar("manual_api_grp_llm.md", D.manual, "text/markdown;charset=utf-8"));

  desenharEtapa();
  verificarAjudante(true);
  desenharCasos();
  desenharCodigos();
  desenharDicionario();
})();
