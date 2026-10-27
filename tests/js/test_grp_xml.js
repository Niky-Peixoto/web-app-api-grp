// Testes de web/grp_xml.js (node tests/js/test_grp_xml.js).
// 1) XML igual, byte a byte, ao que o GRP-Tool monta (tests/fixtures/grp_tool, gerado por scripts/gerar_fixtures_grp_tool.py),
//    com uma diferença de propósito: na RetencaoOlp a árvore segue a ordem do contrato (valorRetencao no fim do bloco),
//    e o GRP-Tool envia o valor em segundo. A conformidade com o contrato é conferida em tests/test_10_contrato.py.
// 2) Leitura e interpretação das respostas reais guardadas em data/arvore/casos.
"use strict";
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const G = require("../../web/grp_xml.js");

const raiz = path.join(__dirname, "..", "..");
let falhas = 0;
function teste(nome, fn) {
  try { fn(); console.log("ok   " + nome); } catch (e) { falhas++; console.log("FALHA " + nome + "\n" + e.message); }
}

function primeiraDiferenca(a, b) {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    if (a[i] !== b[i]) return `posição ${i}: esperado ${JSON.stringify(b.slice(i - 40, i + 40))}\n           obtido   ${JSON.stringify(a.slice(i - 40, i + 40))}`;
  }
  return "";
}

const pastaFix = path.join(raiz, "tests", "fixtures", "grp_tool");
// O XML do GRP-Tool com o valorRetencao movido para o fim de cada RetencaoOlp (ordem do contrato).
const naOrdemDoContrato = (xml) => xml.replace(/(<RetencaoOlp>\n)([ \t]*<tipoRetencao>.*\n)([ \t]*<valorRetencao>.*\n)((?:[ \t]*<(?!\/RetencaoOlp).*\n)*?)([ \t]*<\/RetencaoOlp>)/g,
  (_, abre, tipo, valor, resto, fecha) => abre + tipo + resto + valor + fecha);
for (const caso of JSON.parse(fs.readFileSync(path.join(pastaFix, "casos.json"), "utf8"))) {
  teste(`igual ao GRP-Tool: ${caso.nome}`, () => {
    const esperado = naOrdemDoContrato(fs.readFileSync(path.join(pastaFix, caso.nome + ".xml"), "utf8"));
    const obtido = G[caso.funcao](caso.dados);
    if (obtido !== esperado) throw new Error(primeiraDiferenca(obtido, esperado));
  });
}

teste("valores: centavos e formatos", () => {
  assert.strictEqual(G.centavos("1.234,56"), 123456);
  assert.strictEqual(G.centavos("1234.5"), 123450);
  assert.strictEqual(G.centavos("0,05"), 5);
  assert.strictEqual(G.centavos("abc"), null);
  assert.strictEqual(G.valorXml(123456), "1234.56");
  assert.strictEqual(G.valorBr(123456), "1.234,56");
  assert.strictEqual(G.sanitizarJustificativa(" PARCELA 1/2  DA\nOLP "), "PARCELA 1-2 DA OLP");
  assert.strictEqual(G.dataXml("05/11/2026"), "2026-11-05T00:00:00");
  assert.strictEqual(G.normalizarOlp("57490/2026", "2026"), "2026/57490");
  assert.strictEqual(G.normalizarOlp("57490", "2026"), "2026/57490");
  const instante = new Date(2026, 9, 27, 11, 31, 30);
  assert.strictEqual(G.numeroRequisicao(instante, 482, 3), "261027113130482");
  assert.strictEqual(G.numeroRequisicao(instante, 4, 1), "2610271131304");
  assert.strictEqual(G.numeroRequisicao(new Date(2026, 0, 5, 7, 8, 9), 7, 3), "260105070809007");
  assert.throws(() => G.numeroRequisicao(instante, 1000, 3), RangeError);
  assert.throws(() => G.numeroRequisicao(instante, 10, 1), RangeError);
});

teste("OP com IRRF: valores antes e depois do IRRF", () => {
  assert.deepStrictEqual(G.valoresOp(200, 100), { total: 200, retencoes: 100, liquido: 100 });
  assert.deepStrictEqual(G.valoresOp(84, 0), { total: 84, retencoes: 0, liquido: 84 });
});

teste("OLP: retenção zero não entra no XML", () => {
  const xml = G.xmlOlp({ numeroRequisicao: "1", sistema: "51", ano: "2026", uo: "1", orgao: "1", ua: "1", cpfOrdenador: "1",
    cpfOperador: "1", mesCompetencia: "10", anoCompetencia: "2026", justificativa: "X", empenho: "1", credor: "1",
    classificacaoCredor: "X", bruto: 100, liquido: 100, retencoes: [{ tipo: "4", valor: 0, credor: "1" }] });
  assert.ok(!xml.includes("RetencaoOlp") && !xml.includes("valorRetencaoOlp"));
});

const casos = JSON.parse(fs.readFileSync(path.join(raiz, "data", "arvore", "casos.json"), "utf8"));
for (const c of casos) {
  teste(`resposta real: ${c.id}`, () => {
    const ext = c.formato_resposta === "json" ? "json" : "xml";
    const texto = fs.readFileSync(path.join(raiz, "data", "arvore", "casos", `${c.id}_resposta.${ext}`), "utf8");
    const r = G.lerResposta(texto);
    const i = G.interpretar(r);
    if (c.resultado === "aceito") assert.notStrictEqual(i.nivel, "erro", i.titulo);
    else assert.strictEqual(i.nivel, "erro", i.titulo);
    for (const codigo of c.codigos) assert.ok(r.mensagens.some(([cod]) => cod === codigo), `código ${codigo} não lido`);
    if (c.etapa === "processo") assert.ok(/^\d{21}$/.test(r.numeroProcesso));
  });
}

teste("interpretação: cada erro real cai na explicação certa", () => {
  const ler = (id) => G.interpretar(G.lerResposta(fs.readFileSync(path.join(raiz, "data", "arvore", "casos", id + "_resposta.xml"), "utf8")));
  assert.match(ler("10_erro_37144_instrumento_juridico").titulo, /exercício anterior/);
  assert.match(ler("11_erro_37144_saldo_contabil").titulo, /Saldo contábil/);
  assert.match(ler("19_erro_sistema_do_elemento_item").titulo, /PORTAL DE COMPRAS/);
  assert.match(ler("16_erro_62229_sistema_da_OLP").titulo, /^62229/);
  assert.match(ler("16_erro_62229_sistema_da_OLP").dica, /45769/);
  assert.match(ler("12_erro_25081_campos_obrigatorios_empenho").detalhe, /codigoUfg/);
  const ok = ler("01_OP_codigo_de_barras_aceita_130321");
  assert.strictEqual(ok.nivel, "sucesso");
  assert.match(ok.dica, /130321.*116865/);
});

teste("SOAP Fault de tag desconhecida", () => {
  const fault = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><soap:Fault><faultcode>soap:Client</faultcode><faultstring>Unmarshalling Error: elemento inesperado (uri:"", local:"retencao"). </faultstring></soap:Fault></soap:Body></soap:Envelope>';
  const i = G.interpretar(G.lerResposta(fault));
  assert.match(i.titulo, /não reconheceu uma tag/);
});

if (falhas) { console.log(`\n${falhas} falha(s)`); process.exit(1); }
console.log("\ntodos os testes passaram");
