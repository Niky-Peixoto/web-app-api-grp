<p align="center">
  <img src="assets/logo_grp.png" height="72" alt="Logo GRP Minas" />
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/logo_tesouro.png" height="30" alt="Logo Tesouro Estadual" />
</p>

<h1 align="center">Árvore Interativa da API do GRP</h1>

<p align="center">
  <strong>Documentação de testes dos Web Services da API SOAP do GRP Minas (SEF-MG / PRODEMGE)</strong><br>
  Versão 2.1 — 26/10/2026 · Subsecretaria do Tesouro Estadual
</p>

---

Este repositório reúne o que um órgão precisa para integrar o seu sistema à API do GRP e **reproduzir os testes na
prática**: a árvore interativa, o manual da API e a documentação de testes. Tudo vem de chamadas reais ao GRP, feitas
principalmente pelo Assistente GRP (GRP-Tool) da SEF.

| Arquivo | Para quem | O que é |
| :--- | :--- | :--- |
| [`arvore_interativa_grp.html`](arvore_interativa_grp.html) | Quem vai testar a API | Página que monta, confere e envia cada chamada e explica a resposta. |
| [`manual_api_grp_llm.md`](manual_api_grp_llm.md) | Desenvolvedores e assistentes de IA | Manual completo da API em Markdown, pronto para usar como contexto num modelo de linguagem. |
| [`docs/DOCUMENTACAO_API_GRP_TESTES_PRIORIDADE_ALTA.md`](docs/DOCUMENTACAO_API_GRP_TESTES_PRIORIDADE_ALTA.md) | Equipes de integração | Especificação de cada serviço, com contratos, campos, exemplos e regras observadas em teste. |

O manual e a DOCUMENTACAO têm a mesma versão e não se contradizem: os trechos comuns saem de uma fonte só
(`core/conteudo_compartilhado.py`).

---

## Como usar a árvore

1. **Baixar:** abra [`arvore_interativa_grp.html`](arvore_interativa_grp.html) aqui no GitHub e clique em
   **Download raw file** (o ícone de seta para baixo, acima do código).
2. **Abrir:** dê dois cliques no arquivo baixado. Ele abre no navegador e funciona sem internet; não precisa instalar
   nada.
3. **Seguir a aba Início:** ela explica o ciclo da despesa e o que precisa estar pronto no GRP antes do primeiro envio.

O que tem em cada aba:

- **Montar e testar:** a cadeia **Processo → Empenho → OLP → OP** (com retenção de IRRF) e as manutenções: cancelar OP,
  anular valores na OLP, reforçar empenho e anular empenho. Os dados da execução são informados uma vez e cada etapa
  leva o número gerado para a seguinte. Em cada etapa:
  1. **Preencha** os campos (cada um mostra a tag do XML correspondente);
  2. **Confira** os avisos: a página aplica as regras aprendidas nos testes e os catálogos do GRP embutidos
     (elemento-item, centros de custo, classificação orçamentária, combinações grupo/fonte/IPU);
  3. **Envie** pela própria página ou copie o comando pronto (PowerShell, curl, Python, Postman/SoapUI, ou só o XML);
  4. **Cole a resposta** (quando enviar por fora) e veja se deu certo e o que fazer em caso de erro.
- **Casos reais:** chamadas enviadas ao GRP e as respostas que voltaram, com o que cada uma ensina.
- **Entender uma resposta:** cole qualquer resposta do GRP para interpretá-la, e a tabela dos códigos conhecidos.
- **Contrato e dicionário:** os campos que cada serviço aceita (contrato WSDL da produção) e o significado de cada tag.

**Enviar pela página.** O navegador não deixa uma página falar direto com o GRP. Por isso a árvore oferece um
*ajudante de envio*: um pequeno script de PowerShell que a página gera e que você cola no PowerShell do seu computador.
Ele usa o `curl.exe` do próprio Windows, só aceita pedidos da página que o gerou e só envia para os endereços do GRP.
Para desligar, feche a janela. Não clique dentro da janela do PowerShell: o Windows pausa o programa (tecle Esc se
isso acontecer).

**Antes do primeiro envio:** rede do Governo ou VPN (o GRP não responde de fora), sistema de origem autorizado pela
PRODEMGE, ordenador com exceção de assinatura e autorizado na UO/UA, programação orçamentária e financeira, credor
cadastrado e elemento-item liberado para o seu sistema.

> [!IMPORTANT]
> Os dados digitados ficam só no navegador de quem usa. Os catálogos embutidos foram coletados nas datas indicadas em
> cada aviso e podem estar desatualizados: em caso de divergência, vale o cadastro do GRP, que pode ser consultado nas
> telas do sistema.

---

## Regras principais da API

O detalhe de cada regra, com o caso real que a comprovou, está no manual e na DOCUMENTACAO. As mais importantes:

- **Endereços com `www`:** `https://www.grp.servicos.mg.gov.br/serviceBus/...`. Sem o `www` o servidor responde `301` e o
  `POST` se perde.
- **Mesmo sistema de origem em toda a cadeia.** Documentos registrados pela tela do GRP podem continuar pela API
  (ex.: OP pela API sobre uma OLP registrada na tela). O Portal de Compras (sistema `2`) só empenha e liquida: a OP
  desses documentos é feita pela tela do GRP.
- **INSS e ISSQN só na OLP** (INSS `14`, aceito com credor CPF ou CNPJ, e `4` também aceito com CPF; ISSQN `13`).
  A OP paga o líquido da OLP.
- **IRRF na OP** (produção desde 19/10/2026): bloco `<retencao>` dentro do item de pagamento, tipo `10`. O total e o
  item vão antes do IRRF; os líquidos vão sem ele.
- **`numeroRequisicao`:** um número novo por chamada, nunca reaproveitado: data e hora (`AAMMDDhhmmss`) + dígitos
  sorteados. Na OP, 15 dígitos (aceito em 27/10/2026); nos demais serviços, 13 até o teste com 15. Com 17 a 18
  dígitos o GRP recusa.
- **Ordem dos campos:** siga a sequência do contrato (XSD). O GRP hoje aceita alguns campos fora de ordem, mas um
  cliente que valide o XML recusa. Os exemplos de envio dos documentos e da árvore já estão no formato atual
  (os enviados num formato antigo foram ajustados, com os mesmos valores, e a nota diz o que mudou).
- **Justificativa sem barra (`/`)**: troque por hífen.
- **Leia a causa do erro:** o `37144` e o `0` são genéricos; o motivo vem depois de *Causa:*.
- **Sem resposta, o resultado é indeterminado:** o GRP pode ter registrado a chamada. Consulte o GRP antes de reenviar
  e, se reenviar, use outro número de requisição.

Endereços dos 8 serviços:

| Serviço | Endereço (produção) |
| :--- | :--- |
| Processo | `https://www.grp.servicos.mg.gov.br/serviceBus/institucional/GerarNumeroProcessoGrpWS` |
| Empenho | `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoEmpenhoWS` |
| Reforço de empenho | `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoReforcoDeEmpenhoWS` |
| Anulação de empenho | `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoAnulacaoEmpenhoWS` |
| OLP | `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoOlpWS` |
| Anulação de valores na OLP | `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoAnulacaoValoresNaOlpWS` |
| OP bancária | `https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/SolicOrdemPagamentoBancariaWS` |
| Cancelamento de OP | `https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/CancelamentoOrdemPagamentoBancariaWS` |

Todas as chamadas são `POST` com `Content-Type: text/xml; charset=utf-8`.

---

## Para quem mantém o repositório

### Estrutura

```text
web-app-api-grp/
├── cli.py                      # build, testes e o runner histórico
├── arvore_interativa_grp.html  # árvore gerada (não editar à mão)
├── manual_api_grp_llm.md       # manual gerado (não editar à mão)
├── dic-tags-api.xlsx           # dicionário das 138 tags (fonte do dicionário do manual e da árvore)
├── docs/                       # DOCUMENTACAO (escrita à mão, com blocos gerados entre marcadores)
├── contratos/                  # contratos WSDL baixados (produção e desenvolvimento) e seus resumos
├── web/                        # fontes da árvore
│   ├── arvore.html / arvore.css / arvore.js
│   ├── grp_xml.js              # monta os XMLs e lê as respostas (mesmos bytes do GRP-Tool)
│   └── ajudante_envio.ps1      # ajudante de envio que a página entrega ao usuário
├── data/
│   ├── arvore/                 # dados da árvore: catálogos datados, casos reais, contrato
│   └── chamadas_database.json  # matriz histórica de 64 cenários (23/09/2026)
├── core/
│   ├── arvore.py               # junta web/ + data/arvore/ num único HTML
│   ├── conteudo_compartilhado.py  # trechos comuns ao manual e à DOCUMENTACAO
│   ├── markdown_generator.py   # gera o manual
│   ├── config.py, registry.py, sanitizer.py (máscara de CPFs)
│   └── scenarios.py, renderer.py, soap_client.py, runner.py  # runner histórico
├── templates/                  # modelos Jinja2 do runner histórico
├── scripts/
│   ├── baixar_contratos_wsdl.py    # baixa e resume os contratos (só GET; rodar na rede do Governo/VPN)
│   ├── exportar_dados_arvore.py    # atualiza data/arvore/ a partir do GRP-Tool e das evidências
│   ├── gerar_fixtures_grp_tool.py  # gera tests/fixtures/grp_tool/ com o próprio GRP-Tool
│   └── batch_runner_live.py        # execução em lote do runner histórico
└── tests/                      # testes Python (unittest) e tests/js/test_grp_xml.js (Node)
```

### Gerar a árvore, o manual e a DOCUMENTACAO

```bash
python cli.py build
```

Gera `arvore_interativa_grp.html` e `manual_api_grp_llm.md` e reescreve os blocos comuns da DOCUMENTACAO. Para mudar um
trecho comum (versão, endpoints, sistema de origem, IRRF, erros, divergências, como reproduzir os testes, regras de
envio, exemplos e histórico), edite `core/conteudo_compartilhado.py`, nunca direto num dos documentos. A versão fica em
`core/config.py`.

### Testes

```bash
python -m unittest discover -s tests   # 41 testes
node tests/js/test_grp_xml.js          # XML igual ao do GRP-Tool e leitura das respostas reais
```

- `tests/test_9_dados_pessoais.py` varre todos os arquivos versionados atrás de CPFs que não sejam fictícios.
- `tests/test_10_contrato.py` confere com o contrato atual (`core/contrato.py`, a partir de `data/arvore/contrato.json`)
  os XMLs que a árvore monta, os exemplos do manual e da DOCUMENTACAO (todos no formato atual),
  os casos reais da árvore, o dicionário e o apêndice de campos.
- `tests/test_7_sincronia_documentacao.py` garante que o manual e a DOCUMENTACAO dizem o mesmo nos blocos comuns.
- `tests/test_8_arvore.py` confere a árvore gerada: dados embutidos, catálogos datados, ajudante de envio e **nenhum CPF
  sem máscara**. Ele também roda o teste em Node quando o Node está instalado.
- `tests/js/test_grp_xml.js` exige que `web/grp_xml.js` gere **os mesmos bytes** que o GRP-Tool em 14 casos. Se o
  GRP-Tool mudar um envelope, rode `scripts/gerar_fixtures_grp_tool.py` e ajuste `grp_xml.js` até o teste passar.

### Atualizar os dados da árvore

- **Catálogos e casos reais:** `python scripts/exportar_dados_arvore.py --grp-tool ../grp-tool --evidencias Evidencias.txt`.
  O índice dos casos (títulos, datas e lições) é escrito à mão em `data/arvore/casos.json`.
- **Contrato:** `python scripts/baixar_contratos_wsdl.py` (na rede do Governo/VPN) e depois o script acima, para o
  `data/arvore/contrato.json`.
- **Dicionário:** edite `dic-tags-api.xlsx` e rode o build.

> [!CAUTION]
> Os arquivos atuais do repositório usam só CPFs fictícios (`000000001-91`, `000000002-72`, ...) e contas de crédito
> fictícias; os CPFs e contas reais da base histórica foram substituídos em 26/10/2026. Duas proteções conferem isso:
> - `tests/test_9_dados_pessoais.py` varre **todos** os arquivos versionados e falha se encontrar um CPF válido que não
>   seja fictício, em texto ou em base64;
> - o build ainda mascara os CPFs nos artefatos gerados, e `tests/test_8_arvore.py` confere o HTML.
>
> O histórico do git anterior a essa data ainda contém os dados reais. Não versione configurações, XMLs de uso ou
> resultados de testes com dados reais.

### Runner histórico (64 cenários)

A árvore antiga era um catálogo dos 64 cenários homologados em 23/09/2026 (5 variáveis: credor CPF/CNPJ,
regionalização, conta a debitar, conta a creditar e retenções na OLP). São chamadas reais, mas anteriores ao IRRF e a
várias regras aprendidas depois, por isso a árvore atual não se baseia mais neles. Continuam no repositório como
histórico, com o runner de linha de comando:

```bash
python cli.py list-scenarios                 # lista os 64 cenários
python cli.py run --scenario Chamada-04      # simula um cenário (valida XML e tags)
python cli.py validate                       # confere as tags dos modelos Jinja2 contra o dicionário
python cli.py list-tags                      # lista as 138 tags
```

O runner também tem o modo `--live`, que envia ao GRP. Só use com autorização e com dados de teste combinados.
