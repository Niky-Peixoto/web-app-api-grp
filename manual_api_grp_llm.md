# 📘 Manual Oficial de Integração SOAP da API do GRP-Minas (SEF-MG / PRODEMGE)

> **📌 Contexto do Sistema para Modelos de Linguagem (LLMs / Agentes de IA):**
> Este manual é a especificação técnica consolidada dos Web Services SOAP do **Sistema Integrado de Gestão Pública (GRP)** do **Governo do Estado de Minas Gerais (PRODEMGE / SEF-MG)**.
> Ele documenta a arquitetura de execução da despesa pública estadual, os contratos WSDL/XSD, as regras fiscobancárias, a cadeia sequencial de herança de dados entre etapas, a retenção de IRRF na OP, exemplos reais de envio e resposta, a matriz histórica de 64 cenários (23/09/2026), o dicionário de 138 tags XML e o guia de diagnóstico de erros.
> Utilize este contexto para gerar código de integração robusto (Python, Java, Node, C#, etc.), validar envelopes XML e auxiliar equipes de desenvolvimento em auditorias fiscais.

> **Versão 2.1 — 26/10/2026.** Este documento e o seu par (`manual_api_grp_llm.md` / `docs/DOCUMENTACAO_API_GRP_TESTES_PRIORIDADE_ALTA.md`) têm a mesma versão e não se contradizem: os trechos comuns são gerados de uma fonte só. O histórico de versões está no fim.

---

## 1. 🌐 Arquitetura Geral & Endpoints Oficiais

* **Protocolo:** SOAP 1.1 / 1.2 sobre HTTP/HTTPS
* **Método HTTP:** `POST`
* **Header Obrigatório:** `Content-Type: text/xml; charset=utf-8`
* **Formato do Body:** XML estruturado no envelope SOAP padrão (`<soapenv:Envelope>`)
* **Aviso Crítico de URL:** Utilize sempre o subdomínio oficial com `www` (`https://www.grp.servicos.mg.gov.br/...`). Requisições sem `www` recebem redirecionamento `HTTP 301 Moved Permanently`, descartando o payload `POST`.

### Tabela de Endpoints dos Web Services:

| Etapa / Operação | Serviço | Operação SOAP | `identificadorProcessoExecucao` | Endpoint (produção) | Situação |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Abertura de processo | `GerarNumeroProcessoGrpWS` | `gerarNumeroProcessoGrp` | — | `https://www.grp.servicos.mg.gov.br/serviceBus/institucional/GerarNumeroProcessoGrpWS` | Validado |
| Empenho | `SolicitacaoEmpenhoWS` | `gerarSolicitacaoEmpenho` | `EMPOLP1.1` | `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoEmpenhoWS` | Validado |
| Reforço de empenho | `SolicitacaoReforcoDeEmpenhoWS` | `gerarSolicitacaoReforcoEmpenho` | `EMPOLP1.2` | `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoReforcoDeEmpenhoWS` | Validado em 16/06/2026; estrutura confirmada pelo contrato de 26/10/2026 |
| Anulação de empenho | `SolicitacaoAnulacaoEmpenhoWS` | `gerarSolicitacaoAnulacaoSaldoEmpenho` | `EMPOLP1.3` | `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoAnulacaoEmpenhoWS` | Validado em 15/06/2026; estrutura confirmada pelo contrato de 26/10/2026 |
| Liquidação (OLP) | `SolicitacaoOlpWS` | `solicitarOLP` | `EMPOLP2.1` | `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoOlpWS` | Validado |
| Anulação de valores na OLP | `SolicitacaoAnulacaoValoresNaOlpWS` | `solicitarAnulacaoValoresNaOLP` | `EMPOLP2.2` | `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoAnulacaoValoresNaOlpWS` | Validado em 15/06/2026 |
| OP bancária | `SolicOrdemPagamentoBancariaWS` | `gerarSolicOrdemPagamentoBancaria` | `PGBANESC1.1.1` | `https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/SolicOrdemPagamentoBancariaWS` | Validado; contrato novo (IRRF no item) na produção desde 19/10/2026 |
| Cancelamento de OP bancária | `CancelamentoOrdemPagamentoBancariaWS` | `cancelarOrdemPagamentoBancaria` | `PGBANESC1.2.1` | `https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/CancelamentoOrdemPagamentoBancariaWS` | Validado em 15/06 e 13/10/2026 |

* **Produção:** `https://www.grp.servicos.mg.gov.br/serviceBus/...`. Sem o `www`, o servidor responde `301` para o endereço com `www`; se o cliente seguir o redirecionamento sozinho, o `POST` vira `GET` e o conteúdo se perde. Use o endereço com `www` ou reenvie o `POST` ao endereço do `Location`.
* **Desenvolvimento (PRODEMGE):** `https://desenvolvimento.grp.servicos.mg.gov.br/serviceBus/...`. Publica os contratos (`?wsdl`) e recebe primeiro as mudanças de contrato (o IRRF no item apareceu lá em 14/10/2026). Não use para gerar documentos sem autorização da PRODEMGE: os dados são outros.
* **Contratos WSDL:** conferidos em 26/10/2026 — produção e desenvolvimento publicam o contrato dos 8 serviços (HTTP 200), com os mesmos campos nos dois ambientes; cada contrato declara o próprio endereço (`www` na produção). Resumos em `contratos/producao/2026-10-26/RESUMO.md` e `contratos/desenvolvimento/2026-10-26/RESUMO.md`. Até 16/10/2026 o `?wsdl` da produção redirecionava para `indisponivel.mg.gov.br`. Para baixar de novo e conferir os 8 endereços, rode na rede do Governo ou na VPN `python scripts/baixar_contratos_wsdl.py`: ele só faz `GET`, salva os arquivos em `contratos/<ambiente>/<data>/` e gera um `RESUMO.md` com a situação de cada endpoint e os campos de cada tipo.
* **Rede:** o GRP só responde de dentro da rede do Governo de Minas ou pela VPN. Em algumas máquinas, a borda da PRODEMGE devolve a página de indisponibilidade para o TLS do Python (OpenSSL) e aceita o `curl.exe` do Windows; nesses casos, use o `curl.exe` como transporte (sem imitar navegador).
* **Ambiente atual:** segundo a SEF (15/10/2026), a instalação do GRP em `www.grp.servicos` é de teste: as OPs geradas lá não seguem para os bancos.
* **Fora da API para o sistema 51:** a consulta IS47588 (recuperar dados da execução da despesa) não aceita `codigoSistemaSolicitante` 51. Conferir OPs só pela tela de consulta do GRP, pelo Nº da solicitação.

### 1.1. Como Reproduzir os Testes (Árvore Interativa)

A **Árvore Interativa da API do GRP** (`arvore_interativa_grp.html`, um arquivo só, que abre em qualquer navegador e funciona sem internet) é a forma recomendada de reproduzir os testes descritos aqui. Para baixá-la: no GitHub, abra o arquivo `arvore_interativa_grp.html` e clique em *Download raw file*.

* **Montar e testar:** a cadeia Processo → Empenho → OLP → OP (com IRRF) e as manutenções (cancelar OP, anular valores na OLP, reforçar e anular empenho). Os dados da execução são informados uma vez; cada etapa leva o número gerado para a seguinte. Os dados ficam só no navegador de quem usa.
* **Conferência antes de enviar:** a página confere as regras desta documentação e os catálogos do GRP embutidos (elemento-item e sistema dono, centros de custo da UA, classificação orçamentária, combinações grupo/fonte/IPU). Os catálogos foram coletados nas datas indicadas e podem estar desatualizados: em caso de divergência, vale o cadastro do GRP, que pode ser consultado nas telas do sistema.
* **Envio:** pela própria página, com um *ajudante de envio* que roda no computador de quem usa (PowerShell com o `curl.exe` do Windows; só aceita a página que o gerou e só fala com o GRP), ou por comandos prontos para PowerShell, curl, Python e Postman/SoapUI. O XML gerado é igual, byte a byte, ao do Assistente GRP (GRP-Tool), que gerou os casos reais.
* **Resposta:** a página lê a resposta do GRP (XML ou JSON), diz se deu certo, o que fazer em caso de erro e mostra o caso real parecido.
* **Casos reais, códigos de resposta, contrato e dicionário:** as mesmas informações desta documentação, com o envio e a resposta de cada caso (CPFs mascarados).

Antes do primeiro envio: rede do Governo ou VPN, sistema de origem autorizado, ordenador com exceção de assinatura e autorizado na UO/UA, programação orçamentária e financeira, credor cadastrado e elemento-item liberado para o sistema (ver pré-requisitos).

---

## 2. 🔄 O Ciclo da Despesa em Cadeia (A Regra de Ouro da Herança de Dados)

A execução regular de despesa pública no GRP é **sequencial e encadeada**: cada etapa usa o número do documento gerado na etapa anterior. Esse documento pode ter sido gerado pela API ou registrado pela tela do GRP, então não é preciso fazer todas as etapas pela API (ex.: uma OP pela API sobre uma OLP registrada na tela). A exceção são os documentos do Portal de Compras (sistema `2`), cuja OP é feita pela tela do GRP (seção 2.1).

### Fluxo Sequencial de Execução:
```text
  [ 1. ABERTURA DE PROCESSO ] (GerarNumeroProcessoGrpWS)
              │
              ▼ (Retorna: <numeroProcesso> com 21 dígitos)
  [ 2. RESERVA E EMPENHO ]    (SolicitacaoEmpenhoWS)
              │
              ▼ (Recebe: <numeroProcessoGeral> | Retorna: <numeroDocumento> do Empenho)
  [ 3. LIQUIDAÇÃO / OLP ]     (SolicitacaoOlpWS)
              │
              ▼ (Recebe: <numeroDocumentoEmpenho> | Retorna: <numeroDocumento> da OLP)
  [ 4. PAGAMENTO / OBM ]      (SolicOrdemPagamentoBancariaWS)
                (Recebe: <anoNumeroDaOlpEEmpenho> como 'AAAA/Nº OLP' | Gera Ordem Bancária)
```

> **💡 A Regra de Ouro:** O número de documento (`<numeroDocumento>`) gerado com sucesso em uma fase é a chave de entrada da chamada seguinte. O integrador deve guardar o retorno de cada etapa para alimentar a próxima.

### 2.1. Regra do Sistema de Origem

* **Mesmo sistema em toda a cadeia:** processo, empenho, OLP, OP e as operações de manutenção de uma mesma execução devem usar o mesmo `codigoSistemaOrigem` (no processo, `codigoSistemaSolicitante`). Só o próprio GRP, pela interface web, opera documentos de qualquer origem.
* **Documentos registrados pela tela do GRP** podem continuar pela API: não é preciso fazer todas as etapas pela API. Exemplo testado: OP enviada pela API sobre uma OLP registrada na tela do GRP.
* **Evidência (15/10/2026):** uma OP enviada com sistema `2` (Portal de Compras) sobre uma OLP criada pelo sistema `51` voltou `62229` — *"Documento não permitido, a solicitação deve ser registrada via NOTA MINEIRA"*.
* **Portal de Compras (sistema `2`):** é um sistema que só empenha e liquida. A OP de documentos do Portal de Compras é feita pela interface do GRP, inclusive quando a execução inteira começou do zero com o sistema `2`.
* **Não troque de sistema por conta própria:** usar o código de outro sistema exige autorização da PRODEMGE/STE. O sistema `51` é a Nota Fiscal Mineira.

---

## 3. 🔧 Operações de Manutenção (Fora da Cadeia Linear)

Quando um empenho, uma OLP ou uma OP já foi emitido e precisa de ajuste ou cancelamento sem reprocessar toda a cadeia, utilizam-se os serviços de manutenção:

### 3.1. Solicitação de Reforço de Empenho (`SolicitacaoReforcoDeEmpenhoWS`)
* **Objetivo:** Acréscimo de saldo orçamentário em empenhos vigentes. Validado com empenho `ESTIMATIVO`; `ORDINARIO` é recusado (*Tipo de Empenho não permite reforço*); `GLOBAL` ainda não testado (divergência D4).
* **Campos:** `<numeroEmpenho>`, UO, órgão, UA, ordenador, operador, `<valorReforco>` e justificativa, todos direto em `<solicitacaoReforcoEmpenho>`. O GRP herda credor, dotações e contas do empenho.

### 3.2. Solicitação de Anulação de Saldo de Empenho (`SolicitacaoAnulacaoEmpenhoWS`)
* **Objetivo:** Cancelamento parcial ou total de saldo orçamentário não liquidado em OLP, liberando o recurso orçamentário.
* **Campos:** `<numeroEmpenho>`, UO, órgão, UA, ordenador, operador, `<valorAnulacaoEmpenho>` e justificativa, dentro de um elemento interno com o mesmo nome da operação (`<gerarSolicitacaoAnulacaoSaldoEmpenho>`). Atua sobre o saldo remanescente do empenho.

### 3.3. Solicitação de Anulação de Valores na OLP (`SolicitacaoAnulacaoValoresNaOlpWS`)
* **Objetivo:** Anular valores de uma OLP já gerada.
* **Mínimo aceito:** `<numeroOlp>`, UO, órgão, UA, ordenador, `<valorLiquidoAnulado>`, `<valorTotalAnulado>` e justificativa. O sucesso vem como *Encaminhada para análise*, sem `numeroDocumento`.

### 3.4. Cancelamento de Ordem de Pagamento Bancária (`CancelamentoOrdemPagamentoBancariaWS`)
* **Objetivo:** Cancelar uma OP bancária já gerada (enquanto pendente).
* **Chave:** `<numeroDocumentoOrdemDePagamento>` é o **número do documento** da OP (`numeroDocumento` da resposta), não o número da solicitação. Um número errado cancela **outra** OP.
* **Identificador:** só `PGBANESC1.2.1` funcionou (`PGBANESC1.1.x`, `1.2.2` e `1.2.3` falharam). O sucesso vem como *Concluída* (`54533`).

---

## 4. ⚙️ Pré-requisitos & Cadastros Prévios no Sistema GRP

Antes de disparar chamadas de API, o ambiente administrativo do GRP deve atender às seguintes condições:

1. **✍️ Exceção de Assinatura do Ordenador de Despesa:**
   - O CPF informado como `<cpfOrdenadorDespesa>` deve estar cadastrado no GRP com **perfil de exceção de assinatura** para todas as fases (Empenho, OLP e OP) na Unidade Administrativa (UA) executora.
   - *Finalidade:* Permite que o GRP registre e auto-aprove o documento imediatamente na resposta síncrona SOAP. Sem isso, as etapas ficam retidas aguardando assinatura manual no portal web, interrompendo a cadeia via API.

2. **💰 Programação Orçamentária e Financeira:**
   - A UA deve possuir cotas ativas de Programação Orçamentária (saldo de dotação) e de Programação Financeira (recurso financeiro descentralizado) aprovadas no GRP para evitar rejeição por saldo insuficiente.

3. **👥 Cadastro Prévio de Favorecidos / Credores:**
   - O credor (CPF ou CNPJ) deve estar cadastrado no GRP antes da chamada. Confira o cadastro e use em `<classificacaoCredor>` a classificação efetiva do credor, escrita exatamente como no cadastro, com acento (ex.: `BENEFICIÁRIOS DIVERSOS`, `PRESTADOR DE SERVIÇOS`, `SERVIDOR PÚBLICO ESTADUAL`).
   - Trocar a classificação não substitui o cadastro: se o favorecido ainda não existe no GRP, ou se a classificação enviada não é a dele, o GRP responde **Erro 85910** (*valor não cadastrado*). Nesse caso, cadastre o credor no GRP ou corrija a classificação, e envie de novo.

4. **📊 Parametrização Contábil da Natureza do Item:**
   - A combinação Órgão + Elemento de Despesa + Item de Despesa (ex.: `031` / `005`) deve possuir amarração contábil ativa no plano de contas da **Subsecretaria do Tesouro Estadual (STE/SEF)** para o exercício financeiro.

5. **👤 Ordenador Autorizado na UO/UA no Exercício:**
   - Sem essa autorização, o GRP responde `0` — *Ordenador de despesa não está autorizado para UO ..., UA ...*.

6. **📦 Elemento-Item Liberado para o Sistema de Origem:**
   - Cada elemento-item tem um sistema dono no GRP. Com outro sistema, o GRP responde `0` — *Sistema ... diferente do sistema do elemento-item*.

### 4.1. Regras Práticas de Envio

* **`numeroRequisicao`:** um número novo por chamada, nunca reaproveitado (nem depois de uma falha). Formato recomendado: data e hora até os segundos (`AAMMDDhhmmss`) seguidas de dígitos sorteados. Na OP, 3 dígitos, 15 no total (ex.: `261027113130482`): aceito em OP em 27/10/2026. Nos demais serviços, 1 dígito, 13 no total (ex.: `2610271131304`), até o teste com 15. Também foram aceitos números de 10 dígitos e de 13 dígitos no formato ano + UO + sequencial (26/10/2026). Números de 17 a 18 dígitos fizeram o GRP recusar todas as OPs (*DataException*, 14/09/2026).
* **Por que data e hora:** o número muda a cada segundo, não se esgota e não exige combinar faixas entre executores. Dois envios só coincidem se saírem no mesmo segundo e sortearem os mesmos dígitos; se acontecer, o GRP recusa o segundo e basta reenviar com outro número. A árvore interativa monta o número assim e, no mesmo navegador, nunca repete um número (cliques no mesmo segundo seguem em sequência).
* **Justificativa sem barra:** uma barra (`/`) na justificativa da OP fez o GRP responder *ArrayIndexOutOfBoundsException* em todas as chamadas (14/09/2026). Troque por hífen (`-`).
* **Sem resposta, o resultado é indeterminado:** quando a chamada termina sem resposta (tempo esgotado ou conexão cortada), a solicitação pode ter sido gravada. Consulte o GRP antes de reenviar, para não gerar documento em dobro; se reenviar, use um número de requisição novo. A árvore mostra esses casos como *resultado indeterminado* e só libera novo envio depois que a pessoa confirma que conferiu no GRP.

---

## 5. 📄 Especificação dos 8 Contratos SOAP & Exemplos Autênticos de XML

### 5.1. Etapa 1: Abertura do Processo Eletrônico (`GerarNumeroProcessoGrpWS`)
* **Endpoint:** `https://www.grp.servicos.mg.gov.br/serviceBus/institucional/GerarNumeroProcessoGrpWS`
* **Operação SOAP:** `gerarNumeroProcessoGrp`
* **Parâmetros-Chave:** `<anoExercicio>`, `<codigoOrgao>`, `<codigoProcessoDeNegocio>` (`18` para despesas comuns), `<codigoUnidadeAdministrativa>`, `<codigoUnidadeOrcamentaria>`, `<codigoSistemaSolicitante>` (`51`).
* **Saída Esperada:** Número do Processo GRP com 21 dígitos (ex.: `101901800000398202611`).

#### Payload de Envio (Request):

```xml
<?xml version="1.0" ?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:int="http://interfaces.webservices.institucional.business.grp.prodemge.gov.br/">
  <soapenv:Header/>
  <soapenv:Body>
    <int:gerarNumeroProcessoGrp>
      <anoExercicio>2026</anoExercicio>
      <codigoOrgao>10190</codigoOrgao>
      <codigoProcessoDeNegocio>18</codigoProcessoDeNegocio>
      <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
      <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
      <codigoSistemaSolicitante>51</codigoSistemaSolicitante>
    </int:gerarNumeroProcessoGrp>
  </soapenv:Body>
</soapenv:Envelope>
```

#### Payload de Retorno (Response):
```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:gerarNumeroProcessoGrpResponse xmlns:ns2="http://interfaces.webservices.institucional.business.grp.prodemge.gov.br/">
      <return>101901800000431202611</return>
    </ns2:gerarNumeroProcessoGrpResponse>
  </soap:Body>
</soap:Envelope>
```

### 5.2. Etapa 2: Reserva Orçamentária e Empenho (`SolicitacaoEmpenhoWS`)
* **Endpoint:** `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoEmpenhoWS`
* **Operação SOAP:** `gerarSolicitacaoEmpenho`
* **Entrada Obrigatória:** `<numeroProcessoGeral>` (recebe os 21 dígitos da Etapa 1).
* **Parâmetros-Chave:** `<tipoEmpenhoComum>` (`ORDINARIO`, `ESTIMATIVO`, `GLOBAL`), dotação orçamentária completa, dados do favorecido e `<classificacaoCredor>`.
* **Saída Esperada:** Mensagem `41040` e `<numeroDocumento>` (Nº do Empenho gerado).

#### Payload de Envio (Request):

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicitacaoEmpenho>
      <solicitacaoEmpenho>
        <numeroRequisicao>1790189797</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP1.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <justificativa>EXECUCAO DO CENARIO Chamada-04 - INSS + ISSQN</justificativa>
        <tipoEmpenhoComum>ORDINARIO</tipoEmpenhoComum>
        <olpPendenteCreditoNaoRegularizar>
          <indicadorReconhecimentoPassivo>NAO</indicadorReconhecimentoPassivo>
          <cpfOperador>00000000000</cpfOperador>
          <numeroProcessoGeral>101901800000431202611</numeroProcessoGeral>
          <cpfCnpjCredor>00000000000</cpfCnpjCredor>
          <classificacaoCredor>BENEFICIÁRIOS DIVERSOS</classificacaoCredor>
          <codigoFuncao>04</codigoFuncao>
          <codigoSubfuncao>129</codigoSubfuncao>
          <codigoPrograma>045</codigoPrograma>
          <codigoProjetoAtividade>4081</codigoProjetoAtividade>
          <codigoSubprojetoSubatividade>0001</codigoSubprojetoSubatividade>
          <codigoCategoriaEconomica>3</codigoCategoriaEconomica>
          <codigoGrupoDespesa>3</codigoGrupoDespesa>
          <codigoModalidadeDespesa>90</codigoModalidadeDespesa>
          <codigoElementoDespesa>031</codigoElementoDespesa>
          <codigoItem>005</codigoItem>
          <codigoIag>00</codigoIag>
          <codigoGrupoFonte>11</codigoGrupoFonte>
          <codigoFonteRecurso>500010</codigoFonteRecurso>
          <codigoIpu>01</codigoIpu>
          <valorEmpenho>1.00</valorEmpenho>
          <codigoCc>0243</codigoCc>
        </olpPendenteCreditoNaoRegularizar>
      </solicitacaoEmpenho>
    </grp:gerarSolicitacaoEmpenho>
  </soap-env:Body>
</soap-env:Envelope>
```

#### Payload de Retorno (Response):
```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:gerarSolicitacaoEmpenhoResponse xmlns:ns2="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1790189797</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacao>58086</numeroSolicitacao>
        <situacaoSolicitacao>Concluída</situacaoSolicitacao>
        <numeroDocumento>57511</numeroDocumento>
        <situacaoDocumento>Registrado e pendente de assinatura</situacaoDocumento>
        <urlDocumento>https://www.grp.servicos.mg.gov.br/grp-srv-rs/rest/serviceBus/documento/00000000000/ee1413f3-474b-48a7-b16c-abee8e11ec9a</urlDocumento>
        <dataSolicitacao>2026-09-23T15:56:43.595-03:00</dataSolicitacao>
        <mensagens>
          <mensagem>
            <codigo>41040</codigo>
            <descricao>Solicitação Empenho gerado com sucesso!</descricao>
          </mensagem>
        </mensagens>
      </return>
    </ns2:gerarSolicitacaoEmpenhoResponse>
  </soap:Body>
</soap:Envelope>
```

### 5.3. Etapa 3: Liquidação da Despesa / OLP (`SolicitacaoOlpWS`)
* **Endpoint:** `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoOlpWS`
* **Operação SOAP:** `solicitarOLP`
* **Entrada Obrigatória:** `<numeroDocumentoEmpenho>` (recebe o Nº do Empenho da Etapa 2).
* **Regras Fiscais:**
  - **Retenções Tributárias (Erro `39148`):** O valor líquido deve fechar matematicamente: `<valorBrutoOlp> - <valorRetencaoOlp> = <valorLiquido>`. Retenções típicas: INSS (tipo `14`, aceito com credor CPF e CNPJ; o tipo `4` também foi aceito com credor CPF) e ISSQN (tipo `13`). O credor da retenção vai em `<cpfCapfCredorRetencao>`.
  - **IRRF não é retido na OLP:** a lista de tipos de retenção da OLP não tem o IRRF. Ele é inscrito na Etapa 4, dentro do item da OP (ver seção 5.4.1).
  - **Regionalização da Despesa (Erro `49762`):** Quando exigida, o bloco `<regionalizacaoDespesaOlpRequestList>` com `<codigoMunicipio>` de 7 dígitos (padrão IBGE) é obrigatório; nas demais, deve ser omitido.
* **Saída Esperada:** Mensagem `41040` e `<numeroDocumento>` (Nº da OLP gerada).

#### Payload de Envio (Request):

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:solicitarOLP>
      <solicitacaoOlp>
        <numeroRequisicao>1790189806</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP2.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <mesCompetenciaDespesa>8</mesCompetenciaDespesa>
        <anoCompetenciaDespesa>2026</anoCompetenciaDespesa>
        <justificativa>EXECUCAO DO CENARIO Chamada-04 - INSS + ISSQN</justificativa>
        <OlpDeEmpenho>
          <numeroDocumentoEmpenho>57511</numeroDocumentoEmpenho>
          <cpfCredorBeneficiario>00000000000</cpfCredorBeneficiario>
          <tipoClassificacaoCredor>BENEFICIÁRIOS DIVERSOS</tipoClassificacaoCredor>
        </OlpDeEmpenho>
        <ValoresDaOlp>
          <valorBrutoOlp>1.00</valorBrutoOlp>
          <valorLiquido>0.84</valorLiquido>
          <valorRetencaoOlp>0.16</valorRetencaoOlp>
        </ValoresDaOlp>
        <retencaoOlpRequestList>
          <RetencaoOlp>
            <tipoRetencao>14</tipoRetencao>
            <cpfCapfCredorRetencao>29979036000140</cpfCapfCredorRetencao>
            <mesCompetenciaRetencao>8</mesCompetenciaRetencao>
            <anoCompetenciaRetencao>2026</anoCompetenciaRetencao>
            <valorRetencao>0.11</valorRetencao>
          </RetencaoOlp>
          <RetencaoOlp>
            <tipoRetencao>13</tipoRetencao>
            <cpfCapfCredorRetencao>18715383000140</cpfCapfCredorRetencao>
            <mesCompetenciaRetencao>8</mesCompetenciaRetencao>
            <anoCompetenciaRetencao>2026</anoCompetenciaRetencao>
            <valorRetencao>0.05</valorRetencao>
          </RetencaoOlp>
        </retencaoOlpRequestList>
      </solicitacaoOlp>
    </grp:solicitarOLP>
  </soap-env:Body>
</soap-env:Envelope>
```

> **XML no formato atual.** O envio original, aceito pelo GRP na época, foi ajustado ao contrato da produção de 26/10/2026, sem mudar os valores: `valorRetencao` foi para a posição do contrato atual (depois de `anoCompetenciaRetencao`).

#### Payload de Retorno (Response):
```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:solicitarOLPResponse xmlns:ns2="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1790189806</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacaoOlp>57926</numeroSolicitacaoOlp>
        <situacaoSolicitacao>Concluída</situacaoSolicitacao>
        <numeroDocumento>57837</numeroDocumento>
        <situacaoDocumento>Registrado e pendente de assinatura</situacaoDocumento>
        <urlDocumento>https://www.grp.servicos.mg.gov.br/grp-srv-rs/rest/serviceBus/documento/00000000000/e6219aed-da55-4a00-a79d-ccab86c5fd73</urlDocumento>
        <dataSolicitacao>2026-09-23T15:56:46.767-03:00</dataSolicitacao>
        <retencaoResponseList>
          <Retencao>
            <tipoRetencao>14</tipoRetencao>
            <credorRetencao>29979036000140</credorRetencao>
            <valorRetencao>0.11</valorRetencao>
          </Retencao>
          <Retencao>
            <tipoRetencao>13</tipoRetencao>
            <credorRetencao>18715383000140</credorRetencao>
            <valorRetencao>0.05</valorRetencao>
          </Retencao>
        </retencaoResponseList>
        <mensagemResponseList>
          <Mensagem>
            <codigo>41040</codigo>
            <descricao>Solicitação 57926 gerado com sucesso!</descricao>
          </Mensagem>
        </mensagemResponseList>
      </return>
    </ns2:solicitarOLPResponse>
  </soap:Body>
</soap:Envelope>
```

### 5.4. Etapa 4: Autorização Bancária de Pagamento / OBM (`SolicOrdemPagamentoBancariaWS`)
* **Endpoint:** `https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/SolicOrdemPagamentoBancariaWS`
* **Operação SOAP:** `gerarSolicOrdemPagamentoBancaria`
* **Entrada Obrigatória:** `<anoNumeroDaOlpEEmpenho>` (no formato `AAAA/Nº da OLP`, ex.: `2026/49995`).
* **Regras Bancárias:**
  - `<tipoContaADebitar>`: `1` para Conta Única (Tesouro Estadual, dispensa dados bancários a debitar) ou `2` para Conta Específica (convênios/projetos com banco/agência/conta preenchidos).
  - **Dígito Verificador da Agência (Erro `40515`):** Bancos digitais sem DV de agência (Inter `077`, Nubank `260`, C6 `336`) exigem a **omissão completa** da tag `<dvAgenciaACreditar>`.
  - **Dígito Verificador da Conta:** Contas bancárias sem DV exigem obrigatoriamente `<dvContaACreditar>0</dvContaACreditar>`.
  - **Conta Específica (`tipoContaADebitar` 2):** exige banco, agência, DV, conta e DV a debitar e `<finalidadePagamento>` (sem ela, erro `38727`).
  - **Código de barras (`codigoFormaPagamento` 002):** exige `<codigoBarras>` e `<finalidadePagamento>`, sem conta a creditar. Funciona também em OLP registrada como crédito em conta (aceito em 15/10/2026, solicitação `130321`); alguns bancos recusam o boleto (erro `45769`).
  - **`<finalidadePagamento>`:** com Conta Única e forma 001 pode ser omitida. Quando exigida, o GRP aceitou qualquer texto (ex.: `01`, `Não se aplica`).
  - **INSS e ISSQN não vão na OP:** essas retenções são formalizadas e retidas exclusivamente na Etapa 3 (`SolicitacaoOlpWS`). Na Etapa 4 (`SolicOrdemPagamentoBancariaWS`), **não se inclui** `<retencaoList>` nem `<valorTotalRetencoes>`; informa-se diretamente o valor líquido já descontado em `<valorTotalAPagarDaOP>`, `<valorLiquidoPagamento>` e nos campos do item de pagamento.
  - **Exceção: IRRF.** O Imposto de Renda Retido na Fonte é inscrito **na própria OP**, num bloco `<retencao>` dentro do `<ItemDePagamento>`, e muda a regra dos valores. Ver seção 5.4.1.
  - **OLP de exercício anterior (restos a pagar):** toda OLP de exercício anterior testada voltou `37144` (*getExigeInstrumentoJuridico() is null*) pela API, com qualquer valor de instrumento jurídico e de exercício; pela tela do GRP o pagamento funciona. Caso aberto com a PRODEMGE.
  - **Número da solicitação × número do documento:** a consulta de OPs do GRP pesquisa pelo `numeroSolicitacao`; o cancelamento usa o `numeroDocumento`. Os dois andam juntos, mas não são iguais.
* **Saída Esperada:** Mensagem `51424` e emissão da Ordem de Pagamento Bancária (OBM).

#### Payload de Envio (Request):

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicOrdemPagamentoBancaria>
      <solicitacaoOrdemPagamentoBancaria>
        <numeroRequisicao>1790189813</numeroRequisicao>
        <identificadorProcessoExecucao>PGBANESC1.1.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <numeroArquivo>1</numeroArquivo>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <cpfCnpjCredor>00000000000</cpfCnpjCredor>
        <classificacaoCredor>BENEFICIÁRIOS DIVERSOS</classificacaoCredor>
        <origemPagamento>OLP Diversos</origemPagamento>
        <cpfCnpjCredorOP>00000000000</cpfCnpjCredorOP>
        <classificacaoCredorDaOP>BENEFICIÁRIOS DIVERSOS</classificacaoCredorDaOP>
        <tipoContaADebitar>1</tipoContaADebitar>
        <finalidadePagamento>01</finalidadePagamento>
        <codigoFormaPagamento>001</codigoFormaPagamento>
        <tipoContaACreditar>1</tipoContaACreditar>
        <codigoBancoACreditar>001</codigoBancoACreditar>
        <codigoAgenciaACreditar>9012</codigoAgenciaACreditar>
        <dvAgenciaACreditar>6</dvAgenciaACreditar>
        <codigoContaACreditar>90006</codigoContaACreditar>
        <dvContaACreditar>3</dvContaACreditar>
        <valorTotalAPagarDaOP>0.84</valorTotalAPagarDaOP>
        <valorLiquidoPagamento>0.84</valorLiquidoPagamento>
        <dataProgramadaPagamento>2026-08-20T00:00:00</dataProgramadaPagamento>
        <justificativa>EXECUCAO DO CENARIO Chamada-04 - INSS + ISSQN</justificativa>
        <itemDePagamentoList>
          <ItemDePagamento>
            <itemDePagamento>1</itemDePagamento>
            <anoNumeroDaOlpEEmpenho>2026/57837</anoNumeroDaOlpEEmpenho>
            <valorAPagar>0.84</valorAPagar>
            <valorTotalAPagar>0.84</valorTotalAPagar>
            <valorLiquido>0.84</valorLiquido>
          </ItemDePagamento>
        </itemDePagamentoList>
      </solicitacaoOrdemPagamentoBancaria>
    </grp:gerarSolicOrdemPagamentoBancaria>
  </soap-env:Body>
</soap-env:Envelope>
```

> **XML no formato atual.** O envio original, aceito pelo GRP na época, foi ajustado ao contrato da produção de 26/10/2026, sem mudar os valores: `finalidadePagamento` foi para a posição do contrato atual (depois de `tipoContaADebitar`).

#### Payload de Retorno (Response):
```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:gerarSolicOrdemPagamentoBancariaResponse xmlns:ns2="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1790189813</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacao>115603</numeroSolicitacao>
        <situacaoSolicitacao>Concluída</situacaoSolicitacao>
        <numeroDocumento>99834</numeroDocumento>
        <situacaoDocumento>REGISTRADO_PENDENTE_ASSINATURA</situacaoDocumento>
        <urlDocumento>https://www.grp.servicos.mg.gov.br/grp-srv-rs/rest/serviceBus/documento/00000000000/2c277037-f92c-4127-9c1f-2743e09947d6</urlDocumento>
        <dataSolicitacao>2026-09-23T15:56:58.685-03:00</dataSolicitacao>
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
```

### 5.4.1. OP com Retenção de Imposto de Renda (IRRF)

> **Situação (26/10/2026):** formato **aceito na produção** (`www.grp.servicos.mg.gov.br`) desde **19/10/2026**, quando a PRODEMGE publicou o contrato novo da OP. Primeira OP com IRRF aceita: solicitação `130905`, documento `117423`, mensagem `51424`. Antes dessa data, a produção recusava o bloco `<retencao>` (erro `Unmarshalling Error` na tabela de erros).

* **INSS e ISSQN não vão na OP:** essas retenções são feitas só na OLP. A OP sem IRRF não leva `<retencaoList>` nem `<valorTotalRetencoes>` e informa o líquido em `<valorTotalAPagarDaOP>`, `<valorLiquidoPagamento>` e nos valores do item. A `<retencaoList>` no nível da OP nunca descontou nada (o GRP a ignorava) e saiu do contrato novo.
* **Onde vai o IRRF:** um bloco `<retencao>` **dentro** do `<ItemDePagamento>`, logo depois de `<valorLiquido>`.
* **Campos do bloco `<retencao>`** (nesta ordem):
  - `<tipoRetencao>`: `10` (IRRF). Os códigos de retenção da OP não são os mesmos da OLP.
  - `<valorRetencao>`: valor do IRRF, com ponto decimal e 2 casas (ex.: `1.00`). O GRP não calcula a alíquota: o integrador informa o valor.
  - `<codigoReceita>`: `090140` no exemplo da PRODEMGE.
  - `<cpfCnpjCredorRetencao>`: `18715615000160` no exemplo da PRODEMGE (credor da retenção), só dígitos.
* **Regra dos valores (diferente da OP sem IRRF):** o total da OP e o valor a pagar do item vão **antes** do IRRF; o líquido vai **sem** o IRRF.

| Tag | Valor | Exemplo (valor antes do IRRF 2,00; IRRF 1,00) |
| :--- | :--- | :--- |
| `<valorTotalAPagarDaOP>` | valor antes do IRRF | `2.00` |
| `<valorTotalRetencoes>` | valor do IRRF (logo após `<valorTotalAPagarDaOP>`) | `1.00` |
| `<valorLiquidoPagamento>` | valor antes do IRRF − IRRF | `1.00` |
| `<valorAPagar>` e `<valorTotalAPagar>` (item) | valor antes do IRRF | `2.00` |
| `<valorLiquido>` (item) | valor antes do IRRF − IRRF | `1.00` |
| `<valorRetencao>` (dentro de `<retencao>`) | valor do IRRF | `1.00` |

* **Saldo da OLP:** o que sai do saldo é o valor antes do IRRF (o INSS e o ISSQN já ficaram retidos na OLP). Ou seja: `valor antes do IRRF = valor bruto − INSS − ISSQN`.
* **Formatos que não funcionam:** IRRF na `<retencaoList>` com todos os valores líquidos → aceito, mas nada é retido; IRRF na `<retencaoList>` com valores antes do IRRF → erro `123`.
* **Pontos ainda em aberto com a PRODEMGE:**
  - O código de receita `090140` é o do exemplo da PRODEMGE, feito com credor **pessoa física**. Falta confirmar o código para credor **pessoa jurídica**.
  - Falta conferir no documento gerado no GRP se a retenção ficou inscrita como esperado (a OP foi aceita, mas a inscrição ainda não foi verificada na tela).
* **Contrato novo da OP** (visto no desenvolvimento em 14/10/2026; confirmado no contrato da produção em 26/10/2026): além de `<retencao>`, o item passa a ter `<valorDesconto>`, `<encargoFinanceiro>` e `<compensacao>`; a guia GPS saiu (ficaram `darf` e `guiaPrevidenciaEstadualGpe`). Segundo a PRODEMGE, inscrição de retenção, desconto e encargos devem ficar dentro do item. Só o IRRF foi testado na produção até agora.

**Caso real: OP com IRRF aceita em 19/10/2026** (solicitação `130905`, OLP `2026/57490`). CPFs e o identificador do documento na URL mascarados; demais dados como foram enviados.

Envio:

```xml
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
```

Resposta (quebras de linha acrescentadas para leitura):

```xml
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
```

* **Observações do caso real:** a `finalidadePagamento` foi enviada (`Não se aplica`) mesmo com Conta Única e forma 001, e foi aceita; o banco `756` não tem DV de agência e a tag `<dvAgenciaACreditar>` foi vazia; a `urlDocumento` agora vem pelo gateway `apigw.mgapi.prodemge.gov.br` e traz o CPF do operador codificado (Base64) no caminho — mascare antes de publicar.

### 5.5. Manutenção: Solicitação de Reforço de Empenho (`SolicitacaoReforcoDeEmpenhoWS`)
* **Endpoint:** `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoReforcoDeEmpenhoWS`
* **Operação SOAP:** `gerarSolicitacaoReforcoEmpenho`
* **Parâmetros:** `<numeroEmpenho>`, `<codigoUnidadeOrcamentaria>`, `<codigoOrgaoExecutor>`, `<codigoUnidadeAdministrativa>`, `<cpfOrdenadorDespesa>`, `<cpfOperador>`, `<valorReforco>`, `<justificativa>`.
* **Estrutura confirmada** pelo contrato de 26/10/2026 e pelo caso real abaixo (solicitação `27`, 16/06/2026). O retorno foi registrado só com os campos do `<return>`, por isso aparece em JSON.

#### Payload de Envio (Request):

```xml
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/"
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
</soap-env:Envelope>
```

#### Retorno (campos do `<return>`, registrados em JSON):
```json
{
  "numeroRequisicao": "222",
  "codigoSistemaOrigem": "51",
  "anoExercicioFinanceiro": "2026",
  "numeroSolicitacao": "27",
  "situacaoSolicitacao": "Encaminhada para análise",
  "dataSolicitacao": "2026-06-16T10:16:22.433-03:00",
  "mensagens": [{"codigo": "41040", "descricao": "Solicitação Reforço de empenho da despesa gerado com sucesso!"}]
}
```

### 5.6. Manutenção: Solicitação de Anulação de Saldo de Empenho (`SolicitacaoAnulacaoEmpenhoWS`)
* **Endpoint:** `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoAnulacaoEmpenhoWS`
* **Operação SOAP:** `gerarSolicitacaoAnulacaoSaldoEmpenho`
* **Parâmetros:** `<numeroEmpenho>`, `<codigoUnidadeOrcamentaria>`, `<codigoOrgaoExecutor>`, `<codigoUnidadeAdministrativa>`, `<cpfOrdenadorDespesa>`, `<cpfOperador>`, `<valorAnulacaoEmpenho>`, `<justificativa>`.
* **Estrutura confirmada** pelo contrato de 26/10/2026 e pelo caso real abaixo (solicitação `98`, 15/06/2026). O retorno foi registrado só com os campos do `<return>`, por isso aparece em JSON.

#### Payload de Envio (Request):

```xml
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/"
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
</soap-env:Envelope>
```

#### Retorno (campos do `<return>`, registrados em JSON):
```json
{
  "numeroRequisicao": "1510363400",
  "codigoSistemaOrigem": "51",
  "anoExercicioFinanceiro": "2026",
  "numeroSolicitacao": "98",
  "situacaoSolicitacao": "Encaminhada para análise",
  "numeroDocumento": null,
  "situacaoDocumento": null,
  "dataSolicitacao": "2026-06-15T10:36:39.632-03:00",
  "mensagens": [{"codigo": "41040", "descricao": "Solicitação de anulação de empenho gerado com sucesso!"}]
}
```

### 5.7. Manutenção: Anulação de Valores na OLP (`SolicitacaoAnulacaoValoresNaOlpWS`)
* **Endpoint:** `https://www.grp.servicos.mg.gov.br/serviceBus/empenho/SolicitacaoAnulacaoValoresNaOlpWS`
* **Operação SOAP:** `solicitarAnulacaoValoresNaOLP` (o elemento interno tem o mesmo nome da operação).
* **Identificador:** `EMPOLP2.2`.

#### Payload de Envio (Request) — caso real de 15/06/2026:

```xml
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
```

#### Retorno (campos do `<return>`, registrados em JSON):
```json
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
```

### 5.8. Cancelamento de Ordem de Pagamento Bancária (`CancelamentoOrdemPagamentoBancariaWS`)
* **Endpoint:** `https://www.grp.servicos.mg.gov.br/serviceBus/pagBancarioEEscritural/CancelamentoOrdemPagamentoBancariaWS`
* **Operação SOAP:** `cancelarOrdemPagamentoBancaria`.
* **Identificador:** `PGBANESC1.2.1`. Chave: `numeroDocumentoOrdemDePagamento` = número do **documento** da OP.

#### Payload de Envio (Request) — caso real de 15/06/2026 (confirmado de novo em 13/10/2026):

```xml
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
```

#### Retorno (campos do `<return>`, registrados em JSON):
```json
{
  "numeroRequisicao": "1602370114",
  "codigoSistemaOrigem": "51",
  "anoExercicioFinanceiro": "2026",
  "numeroSolicitacaoDeCancelamentoOP": "53",
  "situacaoSolicitacao": "Concluída",
  "dataHora": "2026-06-15T16:02:42.063-03:00",
  "mensagens": [{"codigo": "54533", "descricao": "Solicitação de cancelamento gerada com sucesso"}]
}
```

### 5.9. Contratos WSDL Atuais (o que mudou)

Fonte: contratos WSDL da **produção** e do desenvolvimento baixados em 26/10/2026 com `scripts/baixar_contratos_wsdl.py` — os dois são idênticos (resumos completos em `contratos/producao/2026-10-26/` e `contratos/desenvolvimento/2026-10-26/`). O contrato diz o que o servidor aceita ler; regras de negócio (o que o GRP valida depois) só aparecem em chamada real.

* **Os 8 serviços** responderam com contrato (HTTP 200) e as operações documentadas.
* **OP bancária — item de pagamento (`itemDePagamentoSolicOrdemRequest`):** `itemDePagamento`, `valorAPagar`, `valorTotalAPagar` e `valorLiquido` obrigatórios; `retencao`, `encargoFinanceiro` e `compensacao` aparecem **no máximo uma vez** por item; também `valorDesconto`, `codigoReceita`, `anoNumeroDaOp`, `anoNumeroDoEmpenho`, `notaFiscal`, `tipoDiaria` e `tipoDepositoVinculado`.
* **OP bancária — bloco `retencao` (`retencaoOrdemPagamentoRequest`):** `tipoRetencao` (int), `valorRetencao`, `codigoReceita`, `cpfCnpjCredorRetencao` e cinco campos opcionais ainda não testados, ligados ao IR: `valorRendimentoTributavel`, `valorContribuicaoPrevidenciaSocial`, `valorTituloPensaoAlimenticia`, `qtdDependentesIR` e `valorRendimentosIsentos`.
* **OP bancária — nível da OP:** não há `retencaoList` nem `guiaPrevidenciaSocialGps`; há `valorTotalRetencoes`, `valorDesconto`, `darf`, `guiaPrevidenciaEstadualGpe`, `codigoBarras`, `finalidadePagamento`, os campos da OP de retenção (`tipoDeRetencao`, `contribuinte`, `mesAnoDeCompetencia`, `codigoDeReceita`) e os de instrumento jurídico (`instrumentoJuridico`, `numeroInstrumentoJuridicoEntrada` e variantes financiado/financiador).
* **OLP — retenção (`retencaoOlpRequest`):** `tipoRetencao` (int), `valorRetencao`, `cpfCapfCredorRetencao`, `cnpJCredorRetencao`, competência, `dataPagamentoRetencao`, `codigoReceita` e `codigoUoBeneficiariaRetencao`. A resposta da OLP devolve, por retenção, `numeroUnicoRetencao` e `cpfCnpjContribuinte`.
* **Empenho:** além dos instrumentos de entrada, financiado, financiador e **saída** (número, tipo e ano), aparecem `indicadorAntecipacaoPagamento` e `transferenciaVoluntaria`.
* **Tipos numéricos:** a maior parte dos códigos da dotação é `xs:long` (por isso os zeros à esquerda são opcionais); `codigoElementoDespesa`, `codigoItem` e `codigoUnidadeOrcamentaria` são texto e mantêm os zeros.

---

## 6. 📊 Matriz Combinatória dos 64 Cenários Homologados

> **Base histórica (23/09/2026):** chamadas reais, mas anteriores ao IRRF e a várias regras aprendidas depois. Para montar uma chamada atual, use a árvore interativa (seção 1.1).

A matriz completa de testes cobre **64 combinações ortogonais** derivadas de 5 variáveis fiscobancárias ($2 \times 2 \times 2 \times 2 \times 4 = 64$):

1. **Tipo de Credor / Favorecido (2 variações):**
   - `CPF`: Pessoa Física (11 dígitos).
   - `CNPJ`: Pessoa Jurídica (14 dígitos).
2. **Regionalização na OLP (2 variações):**
   - `Sem Regionalização`: Despesas administrativas comuns.
   - `Com Regionalização`: Despesas com preenchimento obrigatório de `<codigoMunicipio>` de 7 dígitos (IBGE).
3. **Tipo de Conta a Debitar (2 variações):**
   - `1 - Conta Única (Tesouro)`: Débito automático na Conta Única do Estado.
   - `2 - Conta Específica`: Débito em conta bancária vinculada a convênios ou fundos.
4. **Tipo de Conta a Creditar (2 variações):**
   - `1 - Conta Corrente`: Crédito em conta corrente do favorecido.
   - `2 - Poupança`: Crédito em caderneta de poupança (exige mesmo banco da conta debitada).
5. **Perfil de Retenção Tributária (4 variações):**
   - `Sem Retenção`: Pagamento bruto integral.
   - `INSS`: Retenção previdenciária (tipo 14).
   - `ISSQN`: Retenção de imposto municipal (tipo 13).
   - `INSS + ISSQN`: Dupla retenção com cálculo líquido estrito.

> **IRRF fora da matriz:** a retenção de Imposto de Renda é feita na Etapa 4 (OP), não na OLP, e não faz parte destes 64 cenários. Ver seção 5.4.1.

### 6.1. Exemplos de Envio e Resposta por Cenário

As etapas que não aparecem num exemplo são iguais às do exemplo principal (`Chamada-04`: credor CPF, sem regionalização, Conta Única, conta corrente, INSS + ISSQN). Os 64 cenários são de 23/09/2026: são chamadas reais, mas anteriores ao IRRF e a várias regras aprendidas depois. A matriz completa fica em `data/chamadas_database.json`; para montar uma chamada atual, use a árvore interativa.

#### Empenho com credor CNPJ (`Chamada-33`, etapa Empenho)

O que muda: credor pessoa jurídica.

Envio:

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicitacaoEmpenho>
      <solicitacaoEmpenho>
        <numeroRequisicao>1786631051</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP1.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <justificativa>PAGAMENTO DE PRESTADOR DE SERVICOS PRODEMGE CNPJ SEM RETENCAO</justificativa>
        <tipoEmpenhoComum>ORDINARIO</tipoEmpenhoComum>
        <olpPendenteCreditoNaoRegularizar>
          <indicadorReconhecimentoPassivo>NAO</indicadorReconhecimentoPassivo>
          <cpfOperador>00000000000</cpfOperador>
          <numeroProcessoGeral>101901800000258202611</numeroProcessoGeral>
          <cpfCnpjCredor>55012456000163</cpfCnpjCredor>
          <classificacaoCredor>BENEFICIÁRIOS DIVERSOS</classificacaoCredor>
          <codigoFuncao>04</codigoFuncao>
          <codigoSubfuncao>129</codigoSubfuncao>
          <codigoPrograma>045</codigoPrograma>
          <codigoProjetoAtividade>4081</codigoProjetoAtividade>
          <codigoSubprojetoSubatividade>0001</codigoSubprojetoSubatividade>
          <codigoCategoriaEconomica>3</codigoCategoriaEconomica>
          <codigoGrupoDespesa>3</codigoGrupoDespesa>
          <codigoModalidadeDespesa>90</codigoModalidadeDespesa>
          <codigoElementoDespesa>031</codigoElementoDespesa>
          <codigoItem>005</codigoItem>
          <codigoIag>00</codigoIag>
          <codigoGrupoFonte>11</codigoGrupoFonte>
          <codigoFonteRecurso>500010</codigoFonteRecurso>
          <codigoIpu>01</codigoIpu>
          <valorEmpenho>1.00</valorEmpenho>
          <codigoCc>0243</codigoCc>
        </olpPendenteCreditoNaoRegularizar>
      </solicitacaoEmpenho>
    </grp:gerarSolicitacaoEmpenho>
  </soap-env:Body>
</soap-env:Envelope>
```

Resposta:

```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:gerarSolicitacaoEmpenhoResponse xmlns:ns2="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1786631051</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacao>42347</numeroSolicitacao>
        <situacaoSolicitacao>Concluída</situacaoSolicitacao>
        <numeroDocumento>41960</numeroDocumento>
        <situacaoDocumento>Registrado e pendente de assinatura</situacaoDocumento>
        <urlDocumento>https://www.grp.servicos.mg.gov.br/grp-srv-rs/rest/serviceBus/documento/00000000000/e1029f77-058a-4498-9795-fc589b04ace6</urlDocumento>
        <dataSolicitacao>2026-08-13T11:24:15.426-03:00</dataSolicitacao>
        <mensagens>
          <mensagem>
            <codigo>41040</codigo>
            <descricao>Solicitação Empenho gerado com sucesso!</descricao>
          </mensagem>
        </mensagens>
      </return>
    </ns2:gerarSolicitacaoEmpenhoResponse>
  </soap:Body>
</soap:Envelope>
```

#### OLP sem retenção (`Chamada-01`, etapa OLP)

O que muda: sem `retencaoOlpRequestList`; `valorLiquido` = bruto.

Envio:

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:solicitarOLP>
      <solicitacaoOlp>
        <numeroRequisicao>1786386247</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP2.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <mesCompetenciaDespesa>8</mesCompetenciaDespesa>
        <anoCompetenciaDespesa>2026</anoCompetenciaDespesa>
        <justificativa>PAGAMENTO DE PREMIO NOTA FISCAL MINEIRA REQUISICAO 2026-08-03</justificativa>
        <OlpDeEmpenho>
          <numeroDocumentoEmpenho>41903</numeroDocumentoEmpenho>
          <cpfCredorBeneficiario>00000000000</cpfCredorBeneficiario>
          <tipoClassificacaoCredor>BENEFICIÁRIOS DIVERSOS</tipoClassificacaoCredor>
        </OlpDeEmpenho>
        <ValoresDaOlp>
          <valorBrutoOlp>1.55</valorBrutoOlp>
          <valorLiquido>1.55</valorLiquido>
          <valorRetencaoOlp>0.00</valorRetencaoOlp>
        </ValoresDaOlp>
      </solicitacaoOlp>
    </grp:solicitarOLP>
  </soap-env:Body>
</soap-env:Envelope>
```

> **XML no formato atual.** O envio original, aceito pelo GRP na época, foi ajustado ao contrato da produção de 26/10/2026, sem mudar os valores: `valorLiquido` foi para a posição do contrato atual (depois de `valorBrutoOlp`).

Resposta:

```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:solicitarOLPResponse xmlns:ns2="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1786386247</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacaoOlp>42067</numeroSolicitacaoOlp>
        <situacaoSolicitacao>Concluída</situacaoSolicitacao>
        <numeroDocumento>41998</numeroDocumento>
        <situacaoDocumento>Registrado e pendente de assinatura</situacaoDocumento>
        <urlDocumento>https://www.grp.servicos.mg.gov.br/grp-srv-rs/rest/serviceBus/documento/00000000000/1b878f8b-d6b7-4e10-9bc5-d0408340329a</urlDocumento>
        <dataSolicitacao>2026-08-10T15:26:50.751-03:00</dataSolicitacao>
        <mensagemResponseList>
          <Mensagem>
            <codigo>41040</codigo>
            <descricao>Solicitação 42067 gerado com sucesso!</descricao>
          </Mensagem>
        </mensagemResponseList>
      </return>
    </ns2:solicitarOLPResponse>
  </soap:Body>
</soap:Envelope>
```

#### OLP com INSS (`Chamada-02`, etapa OLP)

O que muda: uma retenção, tipo `14`.

Envio:

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:solicitarOLP>
      <solicitacaoOlp>
        <numeroRequisicao>1790189646</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP2.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <mesCompetenciaDespesa>8</mesCompetenciaDespesa>
        <anoCompetenciaDespesa>2026</anoCompetenciaDespesa>
        <justificativa>EXECUCAO DO CENARIO Chamada-02 - INSS</justificativa>
        <OlpDeEmpenho>
          <numeroDocumentoEmpenho>57509</numeroDocumentoEmpenho>
          <cpfCredorBeneficiario>00000000000</cpfCredorBeneficiario>
          <tipoClassificacaoCredor>BENEFICIÁRIOS DIVERSOS</tipoClassificacaoCredor>
        </OlpDeEmpenho>
        <ValoresDaOlp>
          <valorBrutoOlp>1.00</valorBrutoOlp>
          <valorLiquido>0.89</valorLiquido>
          <valorRetencaoOlp>0.11</valorRetencaoOlp>
        </ValoresDaOlp>
        <retencaoOlpRequestList>
          <RetencaoOlp>
            <tipoRetencao>14</tipoRetencao>
            <cpfCapfCredorRetencao>29979036000140</cpfCapfCredorRetencao>
            <mesCompetenciaRetencao>8</mesCompetenciaRetencao>
            <anoCompetenciaRetencao>2026</anoCompetenciaRetencao>
            <valorRetencao>0.11</valorRetencao>
          </RetencaoOlp>
        </retencaoOlpRequestList>
      </solicitacaoOlp>
    </grp:solicitarOLP>
  </soap-env:Body>
</soap-env:Envelope>
```

> **XML no formato atual.** O envio original, aceito pelo GRP na época, foi ajustado ao contrato da produção de 26/10/2026, sem mudar os valores: `valorRetencao` foi para a posição do contrato atual (depois de `anoCompetenciaRetencao`).

Resposta:

```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:solicitarOLPResponse xmlns:ns2="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1790189646</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacaoOlp>57924</numeroSolicitacaoOlp>
        <situacaoSolicitacao>Concluída</situacaoSolicitacao>
        <numeroDocumento>57835</numeroDocumento>
        <situacaoDocumento>Registrado e pendente de assinatura</situacaoDocumento>
        <urlDocumento>https://www.grp.servicos.mg.gov.br/grp-srv-rs/rest/serviceBus/documento/00000000000/0c026ab1-ef07-4ab5-aa0d-8bf40470e609</urlDocumento>
        <dataSolicitacao>2026-09-23T15:54:07.685-03:00</dataSolicitacao>
        <retencaoResponseList>
          <Retencao>
            <tipoRetencao>14</tipoRetencao>
            <credorRetencao>29979036000140</credorRetencao>
            <valorRetencao>0.11</valorRetencao>
          </Retencao>
        </retencaoResponseList>
        <mensagemResponseList>
          <Mensagem>
            <codigo>41040</codigo>
            <descricao>Solicitação 57924 gerado com sucesso!</descricao>
          </Mensagem>
        </mensagemResponseList>
      </return>
    </ns2:solicitarOLPResponse>
  </soap:Body>
</soap:Envelope>
```

#### OLP com ISSQN (`Chamada-03`, etapa OLP)

O que muda: uma retenção, tipo `13`.

Envio:

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:solicitarOLP>
      <solicitacaoOlp>
        <numeroRequisicao>1790189717</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP2.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <mesCompetenciaDespesa>8</mesCompetenciaDespesa>
        <anoCompetenciaDespesa>2026</anoCompetenciaDespesa>
        <justificativa>EXECUCAO DO CENARIO Chamada-03 - ISSQN</justificativa>
        <OlpDeEmpenho>
          <numeroDocumentoEmpenho>57510</numeroDocumentoEmpenho>
          <cpfCredorBeneficiario>00000000000</cpfCredorBeneficiario>
          <tipoClassificacaoCredor>BENEFICIÁRIOS DIVERSOS</tipoClassificacaoCredor>
        </OlpDeEmpenho>
        <ValoresDaOlp>
          <valorBrutoOlp>1.00</valorBrutoOlp>
          <valorLiquido>0.95</valorLiquido>
          <valorRetencaoOlp>0.05</valorRetencaoOlp>
        </ValoresDaOlp>
        <retencaoOlpRequestList>
          <RetencaoOlp>
            <tipoRetencao>13</tipoRetencao>
            <cpfCapfCredorRetencao>18715383000140</cpfCapfCredorRetencao>
            <mesCompetenciaRetencao>8</mesCompetenciaRetencao>
            <anoCompetenciaRetencao>2026</anoCompetenciaRetencao>
            <valorRetencao>0.05</valorRetencao>
          </RetencaoOlp>
        </retencaoOlpRequestList>
      </solicitacaoOlp>
    </grp:solicitarOLP>
  </soap-env:Body>
</soap-env:Envelope>
```

> **XML no formato atual.** O envio original, aceito pelo GRP na época, foi ajustado ao contrato da produção de 26/10/2026, sem mudar os valores: `valorRetencao` foi para a posição do contrato atual (depois de `anoCompetenciaRetencao`).

Resposta:

```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:solicitarOLPResponse xmlns:ns2="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1790189717</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacaoOlp>57925</numeroSolicitacaoOlp>
        <situacaoSolicitacao>Concluída</situacaoSolicitacao>
        <numeroDocumento>57836</numeroDocumento>
        <situacaoDocumento>Registrado e pendente de assinatura</situacaoDocumento>
        <urlDocumento>https://www.grp.servicos.mg.gov.br/grp-srv-rs/rest/serviceBus/documento/00000000000/afb83598-5621-4ba2-8136-af789a57d7cb</urlDocumento>
        <dataSolicitacao>2026-09-23T15:55:18.756-03:00</dataSolicitacao>
        <retencaoResponseList>
          <Retencao>
            <tipoRetencao>13</tipoRetencao>
            <credorRetencao>18715383000140</credorRetencao>
            <valorRetencao>0.05</valorRetencao>
          </Retencao>
        </retencaoResponseList>
        <mensagemResponseList>
          <Mensagem>
            <codigo>41040</codigo>
            <descricao>Solicitação 57925 gerado com sucesso!</descricao>
          </Mensagem>
        </mensagemResponseList>
      </return>
    </ns2:solicitarOLPResponse>
  </soap:Body>
</soap:Envelope>
```

#### OLP com regionalização (`Chamada-17`, etapa OLP)

O que muda: `regionalizacaoDespesaOlpRequestList` com município IBGE.

Envio:

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:solicitarOLP>
      <solicitacaoOlp>
        <numeroRequisicao>1786628290</numeroRequisicao>
        <identificadorProcessoExecucao>EMPOLP2.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>20071</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>20070</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>2007080001</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <mesCompetenciaDespesa>8</mesCompetenciaDespesa>
        <anoCompetenciaDespesa>2026</anoCompetenciaDespesa>
        <justificativa>DESPESA REGIONALIZADA PROJETO APQ FAPEMIG SEM RETENCAO</justificativa>
        <OlpDeEmpenho>
          <numeroDocumentoEmpenho>41943</numeroDocumentoEmpenho>
          <cpfCredorBeneficiario>00000000000</cpfCredorBeneficiario>
          <tipoClassificacaoCredor>SERVIDOR PÚBLICO ESTADUAL</tipoClassificacaoCredor>
        </OlpDeEmpenho>
        <ValoresDaOlp>
          <valorBrutoOlp>1.00</valorBrutoOlp>
          <valorLiquido>1.00</valorLiquido>
        </ValoresDaOlp>
        <regionalizacaoDespesaOlpRequestList>
          <RegionalizacaoDespesa>
            <codigoMunicipio>3106200</codigoMunicipio>
            <valorDistribuicao>1.00</valorDistribuicao>
          </RegionalizacaoDespesa>
        </regionalizacaoDespesaOlpRequestList>
      </solicitacaoOlp>
    </grp:solicitarOLP>
  </soap-env:Body>
</soap-env:Envelope>
```

Resposta:

```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:solicitarOLPResponse xmlns:ns2="http://interfaces.webservices.empenho.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1786628290</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacaoOlp>42094</numeroSolicitacaoOlp>
        <situacaoSolicitacao>Concluída</situacaoSolicitacao>
        <numeroDocumento>42025</numeroDocumento>
        <situacaoDocumento>Registrado e pendente de assinatura</situacaoDocumento>
        <urlDocumento>https://www.grp.servicos.mg.gov.br/grp-srv-rs/rest/serviceBus/documento/00000000000/8ea6177f-3644-432e-8941-67cd202f41c5</urlDocumento>
        <dataSolicitacao>2026-08-13T10:38:20.152-03:00</dataSolicitacao>
        <mensagemResponseList>
          <Mensagem>
            <codigo>41040</codigo>
            <descricao>Solicitação 42094 gerado com sucesso!</descricao>
          </Mensagem>
        </mensagemResponseList>
      </return>
    </ns2:solicitarOLPResponse>
  </soap:Body>
</soap:Envelope>
```

#### OP com crédito em poupança (`Chamada-05`, etapa OP bancária)

O que muda: `tipoContaACreditar` `2`.

Envio:

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicOrdemPagamentoBancaria>
      <solicitacaoOrdemPagamentoBancaria>
        <numeroRequisicao>1786386251</numeroRequisicao>
        <identificadorProcessoExecucao>PGBANESC1.1.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <numeroArquivo>1</numeroArquivo>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>10190</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <cpfCnpjCredor>00000000000</cpfCnpjCredor>
        <classificacaoCredor>BENEFICIÁRIOS DIVERSOS</classificacaoCredor>
        <origemPagamento>OLP Diversos</origemPagamento>
        <cpfCnpjCredorOP>00000000000</cpfCnpjCredorOP>
        <classificacaoCredorDaOP>BENEFICIÁRIOS DIVERSOS</classificacaoCredorDaOP>
        <tipoContaADebitar>1</tipoContaADebitar>
        <finalidadePagamento>01</finalidadePagamento>
        <codigoFormaPagamento>001</codigoFormaPagamento>
        <tipoContaACreditar>2</tipoContaACreditar>
        <codigoBancoACreditar>104</codigoBancoACreditar>
        <codigoAgenciaACreditar>9002</codigoAgenciaACreditar>
        <dvAgenciaACreditar>7</dvAgenciaACreditar>
        <codigoContaACreditar>900000021</codigoContaACreditar>
        <dvContaACreditar>0</dvContaACreditar>
        <valorTotalAPagarDaOP>1.55</valorTotalAPagarDaOP>
        <valorLiquidoPagamento>1.55</valorLiquidoPagamento>
        <dataProgramadaPagamento>2026-08-10T00:00:00</dataProgramadaPagamento>
        <justificativa>PAGAMENTO DE PREMIO NOTA FISCAL MINEIRA REQUISICAO 2026-08-03</justificativa>
        <itemDePagamentoList>
          <ItemDePagamento>
            <itemDePagamento>1</itemDePagamento>
            <anoNumeroDaOlpEEmpenho>2026/41999</anoNumeroDaOlpEEmpenho>
            <valorAPagar>1.55</valorAPagar>
            <valorTotalAPagar>1.55</valorTotalAPagar>
            <valorLiquido>1.55</valorLiquido>
          </ItemDePagamento>
        </itemDePagamentoList>
      </solicitacaoOrdemPagamentoBancaria>
    </grp:gerarSolicOrdemPagamentoBancaria>
  </soap-env:Body>
</soap-env:Envelope>
```

> **XML no formato atual.** O envio original, aceito pelo GRP na época, foi ajustado ao contrato da produção de 26/10/2026, sem mudar os valores: `finalidadePagamento` foi para a posição do contrato atual (depois de `tipoContaADebitar`).

Resposta:

```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:gerarSolicOrdemPagamentoBancariaResponse xmlns:ns2="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1786386251</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacao>69705</numeroSolicitacao>
        <situacaoSolicitacao>Concluída</situacaoSolicitacao>
        <numeroDocumento>64611</numeroDocumento>
        <situacaoDocumento>REGISTRADO_PENDENTE_ASSINATURA</situacaoDocumento>
        <urlDocumento>https://www.grp.servicos.mg.gov.br/grp-srv-rs/rest/serviceBus/documento/00000000000/f981e295-b7c2-45bc-a720-cbce090b5b2f</urlDocumento>
        <dataSolicitacao>2026-08-10T15:27:29.099-03:00</dataSolicitacao>
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
```

#### OP com débito em conta específica (`Chamada-09`, etapa OP bancária)

O que muda: `tipoContaADebitar` `2` com banco/agência/conta a debitar.

Envio:

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicOrdemPagamentoBancaria>
      <solicitacaoOrdemPagamentoBancaria>
        <numeroRequisicao>1786386227</numeroRequisicao>
        <identificadorProcessoExecucao>PGBANESC1.1.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <numeroArquivo>1</numeroArquivo>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>20121</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>20120</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>2012080010</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <cpfCnpjCredor>00000000000</cpfCnpjCredor>
        <classificacaoCredor>FORNECEDOR</classificacaoCredor>
        <origemPagamento>OLP Diversos</origemPagamento>
        <cpfCnpjCredorOP>00000000000</cpfCnpjCredorOP>
        <classificacaoCredorDaOP>FORNECEDOR</classificacaoCredorDaOP>
        <tipoContaADebitar>2</tipoContaADebitar>
        <codigoBancoADebitar>001</codigoBancoADebitar>
        <codigoAgenciaADebitar>1615</codigoAgenciaADebitar>
        <dvAgenciaADebitar>2</dvAgenciaADebitar>
        <codigoContaADebitar>22768</codigoContaADebitar>
        <dvContaADebitar>4</dvContaADebitar>
        <finalidadePagamento>01</finalidadePagamento>
        <codigoFormaPagamento>001</codigoFormaPagamento>
        <tipoContaACreditar>1</tipoContaACreditar>
        <codigoBancoACreditar>001</codigoBancoACreditar>
        <codigoAgenciaACreditar>9000</codigoAgenciaACreditar>
        <codigoContaACreditar>90011</codigoContaACreditar>
        <dvContaACreditar>2</dvContaACreditar>
        <valorTotalAPagarDaOP>1.37</valorTotalAPagarDaOP>
        <valorLiquidoPagamento>1.37</valorLiquidoPagamento>
        <dataProgramadaPagamento>2026-08-10T00:00:00</dataProgramadaPagamento>
        <justificativa>pagamento individualizado do prestador de saúde 00000000434 - Tipo contrato 27</justificativa>
        <itemDePagamentoList>
          <ItemDePagamento>
            <itemDePagamento>1</itemDePagamento>
            <anoNumeroDaOlpEEmpenho>2026/41991</anoNumeroDaOlpEEmpenho>
            <valorAPagar>1.37</valorAPagar>
            <valorTotalAPagar>1.37</valorTotalAPagar>
            <valorLiquido>1.37</valorLiquido>
          </ItemDePagamento>
        </itemDePagamentoList>
      </solicitacaoOrdemPagamentoBancaria>
    </grp:gerarSolicOrdemPagamentoBancaria>
  </soap-env:Body>
</soap-env:Envelope>
```

> **XML no formato atual.** O envio original, aceito pelo GRP na época, foi ajustado ao contrato da produção de 26/10/2026, sem mudar os valores: `finalidadePagamento` foi para a posição do contrato atual (depois de `dvContaADebitar`).

Resposta:

```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:gerarSolicOrdemPagamentoBancariaResponse xmlns:ns2="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1786386227</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacao>69697</numeroSolicitacao>
        <situacaoSolicitacao>Encaminhada para análise</situacaoSolicitacao>
        <dataSolicitacao>2026-08-10T15:24:02.446-03:00</dataSolicitacao>
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
```

#### OP com conta específica e poupança (`Chamada-13`, etapa OP bancária)

O que muda: `tipoContaADebitar` `2` e `tipoContaACreditar` `2`.

Envio:

```xml
<?xml version="1.0" ?>
<soap-env:Envelope xmlns:grp="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/" xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <grp:gerarSolicOrdemPagamentoBancaria>
      <solicitacaoOrdemPagamentoBancaria>
        <numeroRequisicao>1786565122</numeroRequisicao>
        <identificadorProcessoExecucao>PGBANESC1.1.1</identificadorProcessoExecucao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <numeroArquivo>1</numeroArquivo>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <codigoUnidadeOrcamentaria>20071</codigoUnidadeOrcamentaria>
        <codigoOrgaoExecutor>20070</codigoOrgaoExecutor>
        <codigoUnidadeAdministrativa>2007080001</codigoUnidadeAdministrativa>
        <cpfOrdenadorDespesa>00000000000</cpfOrdenadorDespesa>
        <cpfOperador>00000000000</cpfOperador>
        <cpfCnpjCredor>00000000000</cpfCnpjCredor>
        <classificacaoCredor>SERVIDOR PÚBLICO ESTADUAL</classificacaoCredor>
        <origemPagamento>OLP Diversos</origemPagamento>
        <cpfCnpjCredorOP>00000000000</cpfCnpjCredorOP>
        <classificacaoCredorDaOP>SERVIDOR PÚBLICO ESTADUAL</classificacaoCredorDaOP>
        <tipoContaADebitar>2</tipoContaADebitar>
        <codigoBancoADebitar>801</codigoBancoADebitar>
        <codigoAgenciaADebitar>8001</codigoAgenciaADebitar>
        <dvAgenciaADebitar/>
        <codigoContaADebitar>20071004</codigoContaADebitar>
        <dvContaADebitar>0</dvContaADebitar>
        <finalidadePagamento>01</finalidadePagamento>
        <codigoFormaPagamento>001</codigoFormaPagamento>
        <tipoContaACreditar>2</tipoContaACreditar>
        <codigoBancoACreditar>801</codigoBancoACreditar>
        <codigoAgenciaACreditar>8001</codigoAgenciaACreditar>
        <codigoContaACreditar>90000010</codigoContaACreditar>
        <dvContaACreditar>0</dvContaACreditar>
        <valorTotalAPagarDaOP>1.00</valorTotalAPagarDaOP>
        <valorLiquidoPagamento>1.00</valorLiquidoPagamento>
        <dataProgramadaPagamento>2026-08-20T00:00:00</dataProgramadaPagamento>
        <justificativa>DESPESA CONTA ESPECIFICA EM POUPANCA SEM RETENCAO</justificativa>
        <itemDePagamentoList>
          <ItemDePagamento>
            <itemDePagamento>1</itemDePagamento>
            <anoNumeroDaOlpEEmpenho>2026/42018</anoNumeroDaOlpEEmpenho>
            <valorAPagar>1.00</valorAPagar>
            <valorTotalAPagar>1.00</valorTotalAPagar>
            <valorLiquido>1.00</valorLiquido>
          </ItemDePagamento>
        </itemDePagamentoList>
      </solicitacaoOrdemPagamentoBancaria>
    </grp:gerarSolicOrdemPagamentoBancaria>
  </soap-env:Body>
</soap-env:Envelope>
```

> **XML no formato atual.** O envio original, aceito pelo GRP na época, foi ajustado ao contrato da produção de 26/10/2026, sem mudar os valores: `finalidadePagamento` foi para a posição do contrato atual (depois de `dvContaADebitar`).

Resposta:

```xml
<?xml version="1.0" ?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns2:gerarSolicOrdemPagamentoBancariaResponse xmlns:ns2="http://interfaces.webservices.escritural.bancario.pagamento.business.grp.prodemge.gov.br/">
      <return>
        <numeroRequisicao>1786565122</numeroRequisicao>
        <codigoSistemaOrigem>51</codigoSistemaOrigem>
        <anoExercicioFinanceiro>2026</anoExercicioFinanceiro>
        <numeroSolicitacao>69727</numeroSolicitacao>
        <situacaoSolicitacao>Encaminhada para análise</situacaoSolicitacao>
        <dataSolicitacao>2026-08-12T17:05:38.011-03:00</dataSolicitacao>
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
```

---

## 7. 🏷️ Dicionário Consolidado das 138 Tags XML

As 138 tags da planilha `dic-tags-api.xlsx`. As colunas separam três coisas diferentes:

* **Contrato atual:** tipo estrutural e obrigatoriedade, lidos do contrato WSDL da produção de 26/10/2026, por serviço, separando envio e resposta. Quando a mesma tag tem tipos diferentes em serviços diferentes, cada um aparece.
* **Formatação e regra:** como preencher (formatação recomendada) e as regras de negócio observadas em chamadas reais, que vão além do contrato.
* Tags marcadas *Não está no contrato atual* aparecem em casos históricos e não devem ser usadas em implementações novas.

| Tag XML | Conceito | Contrato atual (tipo e obrigatoriedade) | Formatação e regra |
| :--- | :--- | :--- | :--- |
| `<anoCompetenciaDespesa>` | Ano de referência do fato gerador do serviço prestado ou fornecimento realizado. | Envio — OLP: xs:int, obrigatório | 4 dígitos (ex.: 2026). |
| `<anoCompetenciaRetencao>` | Ano de competência fiscal do fato gerador da obrigação tributária retida. | Envio — OLP: xs:int, opcional | 4 dígitos (ex.: 2026). |
| `<anoExercicio>` | Exercício financeiro orçamentário no qual se pretende iniciar a execução da despesa. | Envio — Processo: xs:int, obrigatório | 4 dígitos (ex.: 2026). |
| `<anoExercicioFinanceiro>` | Exercício financeiro orçamentário no qual se pretende iniciar a execução da despesa. | Envio — Empenho, Reforço, Anulação de empenho, OLP, Anulação na OLP, OP: xs:int, obrigatório | Resposta — OLP, OP, Cancelamento de OP: xs:int, opcional | 4 dígitos (ex.: 2026). |
| `<anoNumeroDaOlpEEmpenho>` | Identificador no formato Ano/Número da OLP vinculado a este pagamento bancário. | Envio — OP: xs:string, opcional | No formato AAAA/NúmeroOLP (ex.: 2026/41991). |
| `<cancelamentoOrdemPagamentoBancaria>` | - | Envio — Cancelamento de OP: grupo de campos, opcional | Elemento que encapsula os campos do pedido de cancelamento de OP. |
| `<cancelarOrdemPagamentoBancaria>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope da operação de cancelamento de OP bancária. |
| `<cancelarOrdemPagamentoBancariaResponse>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags de resposta do cancelamento de OP. |
| `<classificacaoCredor>` | Classificação cadastral do favorecido no GRP (ex.: BENEFICIÁRIOS DIVERSOS, PRESTADOR DE SERVIÇOS, SERVIDOR PÚBLICO ESTADUAL). | Envio — Empenho, OP: xs:string, obrigatório · OLP: xs:int, obrigatório | A classificação efetiva do credor no cadastro do GRP, escrita exatamente como lá, com acento e maiúsculas. Se o credor não estiver cadastrado ou a classificação não for a dele, o GRP responde 85910: trocar a classificação não substitui o cadastro. |
| `<classificacaoCredorDaOP>` | Classificação cadastral do titular da Ordem de Pagamento no GRP. | Envio — OP: xs:string, obrigatório | Obrigatoriamente herdada do Empenho/OLP (ex.: BENEFICIÁRIOS DIVERSOS). |
| `<codigo>` | Código numérico padronizado de retorno da API GRP (ex.: 41040 para sucesso na solicitação de empenho/OLP, 51424 para sucesso na Ordem de Pagamento Bancária, ou códigos de erro do catálogo). | Resposta — Cancelamento de OP: xs:int, opcional | Código de diagnóstico ou sucesso retornado pelo barramento. |
| `<codigoAgenciaACreditar>` | Código da agência bancária do favorecido destinatário do pagamento. | Envio — OP: xs:string, opcional | 4 dígitos, só números (ex.: 1615). |
| `<codigoAgenciaADebitar>` | Código da agência bancária governamental de onde os recursos serão debitados. | Envio — OP: xs:string, opcional | 4 dígitos, só números (ex.: 8001). Omitido se tipoContaADebitar = 1. |
| `<codigoBancoACreditar>` | Código do banco de destino onde o favorecido mantém conta (ex.: 001 - Banco do Brasil, 237 - Bradesco, 077 - Inter). | Envio — OP: xs:string, opcional | 3 dígitos, só números (ex.: 001). |
| `<codigoBancoADebitar>` | Código do banco pagador do Governo de Minas para contas específicas (ex.: 801 para BDMG, 001 para Banco do Brasil). | Envio — OP: xs:string, opcional | 3 dígitos, só números (ex.: 801). Omitido se tipoContaADebitar = 1. |
| `<codigoBarras>` | Linha digitável/código de barras do boleto ou guia pago pela OP. Usado com codigoFormaPagamento = 002; funciona também em OLP registrada como crédito em conta, se o banco do boleto aceitar (senão, erro 45769). | Envio — OP: xs:string, opcional | Obrigatório com forma 002; exige finalidadePagamento; conta a creditar fica vazia. |
| `<codigoCategoriaEconomica>` | Classificação da despesa quanto ao seu impacto econômico (3 - Despesas Correntes, 4 - Despesas de Capital). | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 1 dígito, só números (ex.: 3). |
| `<codigoCc>` | Código de Centro de Custo é uma subunidade do Órgão Executor utilizado para agrupar e rastrear despesas e receitas de forma isolada. No ambiente do GRP é possível listar os códigos dos Centros de Custos acessando: "Módulo Institucional" > "Gerir" > "Centro de custo" > "Manter centro de custo" > clicar em "Pesquisar" para elencar todos os Centros de Custo do Órgão Executor indicado. | Envio — Empenho: xs:long, obrigatório | Zeros à esquerda aceitos, mas não obrigatórios: os dois formatos foram aceitos em chamadas reais (ex.: 0243 e 243). |
| `<codigoContaACreditar>` | Número da conta bancária do favorecido recebedor do pagamento. | Envio — OP: xs:string, opcional | Número da conta (ex.: 90013). |
| `<codigoContaADebitar>` | Número da conta corrente governamental específica debitada. | Envio — OP: xs:string, opcional | Até 19 dígitos. Omitido se tipoContaADebitar = 1. |
| `<codigoElementoDespesa>` | Identifica o objeto final de gasto (ex.: 031 - Premiações, 018 - Auxílio Financeiro a Estudantes, 036 - Outros Serviços de Terceiros PF). | Envio — Empenho, OLP: xs:string, obrigatório | 3 dígitos, só números, preservando zeros à esquerda (ex.: 031). |
| `<codigoFonteRecurso>` | Código completo da Fonte de Recursos que financia a despesa pública (ex.: 500010 - Recursos Livres do Estado). | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 6 dígitos, só números (ex.: 500010). |
| `<codigoFormaPagamento>` | Modalidade de pagamento da OP: 001 - Crédito em conta; 002 - Código de barras (exige <codigoBarras> e <finalidadePagamento>, sem conta a creditar). | Envio — OP: xs:string, obrigatório | 3 dígitos, só números (ex.: 001). |
| `<codigoFuncao>` | Maior nível de agregação das ações do governo na estrutura orçamentária (ex.: 04 - Administração, 10 - Saúde). | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 2 dígitos, só números. Zeros à esquerda aceitos, mas não obrigatórios: os dois formatos foram aceitos em chamadas reais (ex.: 04 e 4). |
| `<codigoGrupoDespesa>` | Agrupamento da despesa segundo o objeto de gasto (1 - Pessoal, 3 - Outras Despesas Correntes, 4 - Investimentos). | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 1 dígito, só números (ex.: 3). |
| `<codigoGrupoFonte>` | Grupo de Origem da Fonte de Recursos (ex.: 11 - Recurso Próprio do Exercício Corrente, 12 - Recurso do Tesouro do Exercício Corrente). | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 2 dígitos, só números (ex.: 11). |
| `<codigoIag>` | Indicador de Acompanhamento Governamental, indicando se o Projeto Atividade possui acompanhamento estratégico pelo Governo ou não (00 - Não possui, 01 - Possui). | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 2 dígitos, só números. Zeros à esquerda aceitos, mas não obrigatórios: os dois formatos foram aceitos em chamadas reais (ex.: 00 e 0). |
| `<codigoIpu>` | Identificador do Uso da Fonte de Recursos (IPU) para detalhar a destinação do recurso. | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 2 dígitos, só números. Zeros à esquerda aceitos, mas não obrigatórios: os dois formatos foram aceitos em chamadas reais (ex.: 01 e 1). |
| `<codigoItem>` | Desdobramento do Elemento da Despesa detalhando o gasto programado. | Envio — Empenho: xs:string, obrigatório | 3 dígitos, só números, preservando zeros à esquerda (ex.: 005). |
| `<codigoModalidadeDespesa>` | Indica se os recursos são aplicados diretamente pela UO ou mediante transferência/convênio (ex.: 90 - Aplicações Diretas). | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 2 dígitos, só números (ex.: 90). |
| `<codigoMunicipio>` | Código IBGE identificador do município mineiro onde a despesa pública foi executada ou beneficiada. | Envio — OLP: xs:int, obrigatório · Anulação na OLP: xs:int, opcional | Código IBGE oficial de 7 dígitos (ex.: 3106200 para Belo Horizonte). |
| `<codigoOrgao>` | Código identificador da instituição ou secretaria de estado responsável pela abertura do processo (ex.: 10190 para SEF). | Envio — Processo: xs:int, obrigatório | 5 dígitos, só números (ex.: 10190). |
| `<codigoOrgaoExecutor>` | Código da unidade orçamentária executora responsável pelo empenhamento da despesa. | Envio — Empenho, Reforço, Anulação de empenho, OLP, Anulação na OLP, OP: xs:long, obrigatório | 5 dígitos, só números (ex.: 10190). |
| `<codigoProcessoDeNegocio>` | Classificação interna do processo no GRP (preencher por padrão com '18'). | Envio — Processo: xs:int, obrigatório | 2 dígitos, só números, preencher sempre com '18'. |
| `<codigoPrograma>` | Instrumento de organização das ações governamentais visando à concretização dos objetivos pretendidos (ex.: 045). | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 3 dígitos, só números. Zeros à esquerda aceitos, mas não obrigatórios: os dois formatos foram aceitos em chamadas reais (ex.: 045 e 45). |
| `<codigoProjetoAtividade>` | Ação orçamentária prevista no PPAG e LOA da unidade. | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 4 dígitos, só números, preservando zeros à esquerda (ex.: 4081). |
| `<codigoReceita>` | Código de receita da retenção inscrita na OP (IRRF). O exemplo da PRODEMGE usa 090140 (credor pessoa física); o código para pessoa jurídica ainda não foi confirmado. | Envio — OLP, OP: xs:string, opcional · OP: xs:string, obrigatório | Mantendo os zeros à esquerda (ex.: 090140). |
| `<codigoSistemaOrigem>` | Classificação interna do processo no GRP (preencher por padrão com '51'). | Envio — Empenho, Reforço, Anulação de empenho: xs:long, obrigatório · OLP, Anulação na OLP, OP, Cancelamento de OP: xs:int, obrigatório | Resposta — OLP, Cancelamento de OP: xs:int, opcional · OP: xs:long, opcional | Código do sistema de origem autorizado pela PRODEMGE/STE (51 = Nota Fiscal Mineira; 2 = Portal de Compras). O mesmo em todas as etapas da execução. |
| `<codigoSistemaSolicitante>` | Classificação interna do processo no GRP (preencher por padrão com '51'). | Envio — Processo: xs:string, obrigatório | Código do sistema de origem autorizado pela PRODEMGE/STE (51 = Nota Fiscal Mineira; 2 = Portal de Compras). O mesmo que será usado nas etapas seguintes. |
| `<codigoSubfuncao>` | Particionamento da função que identifica o setor específico da atuação governamental (ex.: 122 - Administração Geral, 129 - Formação de Recursos Humanos). | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 3 dígitos, só números, preservando zeros à esquerda (ex.: 129). |
| `<codigoSubprojetoSubatividade>` | Detalhamento específico do projeto ou atividade para controle interno do órgão (preencher com '0001'). | Envio — Empenho: xs:long, obrigatório · OLP: xs:int, obrigatório | 4 dígitos, só números, preencher com '0001'. Zeros à esquerda aceitos, mas não obrigatórios: os dois formatos foram aceitos em chamadas reais (ex.: 0001 e 1). |
| `<codigoUnidadeAdministrativa>` | Unidade Administrativa (UA) gestora responsável pelo acompanhamento físico e operacional da despesa. | Envio — Processo: xs:long, opcional · Empenho, Reforço, Anulação de empenho, OLP, Anulação na OLP, OP: xs:long, obrigatório | 10 dígitos, só números (ex.: 1019080124). |
| `<codigoUnidadeOrcamentaria>` | Unidade Orçamentária (UO) à qual os créditos orçamentários e cotas de empenho estão vinculados. | Envio — Processo, Empenho, Reforço, Anulação de empenho, OLP, Anulação na OLP, OP: xs:string, obrigatório | 5 dígitos, só números (ex.: 10191). |
| `<cpfCapfCredorRetencao>` | CNPJ ou CPF/CAPF do órgão arrecadador destinatário do recolhimento do tributo retido (ex.: 29979036000140 para INSS da Receita Federal ou CNPJ da Prefeitura para ISSQN). | Envio — OLP: xs:string, opcional | 11 dígitos (CPF/CAPF) ou 14 (CNPJ), só números, sem máscara de pontuação (ex.: 00000000000 ou 00000000000000). |
| `<cpfCnpjContribuinte>` | CPF ou CNPJ do contribuinte sobre o qual recaiu a obrigação tributária retida na liquidação da despesa. | Resposta — OLP: xs:string, opcional | 11 dígitos (CPF) ou 14 (CNPJ), só números, sem máscara de pontuação (ex.: 00000000000 ou 00000000000000). |
| `<cpfCnpjCredor>` | CPF do favorecido (pessoa física) ou CNPJ do fornecedor/prestador (pessoa jurídica) destinatário do empenho. | Envio — Empenho: xs:string, opcional · OP: xs:string, obrigatório | 11 dígitos (CPF) ou 14 (CNPJ), só números, sem máscara de pontuação (ex.: 00000000000 ou 00000000000000). |
| `<cpfCnpjCredorOP>` | CPF ou CNPJ do favorecido cadastrado como titular do pagamento na Ordem de Pagamento. | Envio — OP: xs:string, obrigatório | 11 dígitos (CPF) ou 14 (CNPJ), só números, sem máscara de pontuação (ex.: 00000000000 ou 00000000000000). |
| `<cpfCnpjCredorRetencao>` | CNPJ/CPF do credor da retenção. Na OP com IRRF vai dentro do bloco <retencao> do item (exemplo da PRODEMGE: 18715615000160). Na OLP a tag equivalente é <cpfCapfCredorRetencao>. | Envio — OP: xs:string, opcional | 11 dígitos (CPF) ou 14 (CNPJ), só números, sem máscara de pontuação (ex.: 00000000000 ou 00000000000000). |
| `<cpfCredorBeneficiario>` | CPF ou CNPJ do favorecido final que receberá o valor líquido da OLP. | Envio — OLP: xs:string, opcional | 11 dígitos (CPF) ou 14 (CNPJ), só números, sem máscara de pontuação (ex.: 00000000000 ou 00000000000000). |
| `<cpfOperador>` | CPF do usuário ou operador do sistema cliente encarregado de registrar a solicitação no GRP. | Envio — Empenho, Reforço, Anulação de empenho, OLP, Anulação na OLP: xs:string, opcional · OP, Cancelamento de OP: xs:string, obrigatório | 11 dígitos (CPF), só números, sem máscara de pontuação (ex.: 00000000000). |
| `<cpfOrdenadorDespesa>` | CPF da autoridade pública competente investida do poder de autorizar a realização de despesas e pagamentos. | Envio — Empenho, Reforço, OLP, Anulação na OLP, OP, Cancelamento de OP: xs:string, obrigatório · Anulação de empenho: xs:string, opcional | 11 dígitos (CPF), só números, sem máscara de pontuação (ex.: 00000000000). |
| `<credorRetencao>` | Identificador do credor do tributo retido confirmado pelo GRP na resposta da OLP. | Resposta — OLP: xs:string, opcional | Retornada no XML de resposta da OLP. |
| `<dataHora>` | Data e hora em que o GRP registrou o cancelamento de OP. | Resposta — Cancelamento de OP: xs:dateTime, opcional | ISO-8601 com fuso (ex.: 2026-06-15T16:02:42.063-03:00). |
| `<dataProgramadaPagamento>` | Data e hora agendadas para o processamento da Ordem Bancária no sistema financeiro. | Envio — OP: xs:dateTime, opcional | No formato ISO-8601 (ex.: 2026-08-10T00:00:00). |
| `<dataSolicitacao>` | Data e horário exatos em que a requisição foi registrada e processada pelo barramento do GRP. | Resposta — OLP, OP: xs:dateTime, opcional | Formatada no padrão ISO-8601 com fuso horário (ex.: 2026-08-10T15:26:46.221-03:00). |
| `<descricao>` | Texto descritivo associado ao código de retorno informando o resultado da operação ou a causa de eventuais inconsistências. | Resposta — Cancelamento de OP: xs:string, opcional | Mensagem explicativa retornada pelo GRP (ex.: "Solicitação Empenho gerado com sucesso!"). |
| `<dvAgenciaACreditar>` | Dígito verificador da agência bancária do favorecido. | Envio — OP: xs:string, opcional | Omitir completamente a tag em bancos sem DV de agência (ex.: Inter, Nubank, C6). |
| `<dvAgenciaADebitar>` | Dígito verificador da agência bancária de débito governamental. | Envio — OP: xs:string, opcional | Ex.: 0 ou X. Omitido se tipoContaADebitar = 1 ou se a agência não possuir DV. |
| `<dvContaACreditar>` | Dígito verificador da conta bancária do favorecido recebedor. | Envio — OP: xs:string, opcional | Não omitir. Em contas sem DV, enviar obrigatoriamente <dvContaACreditar>0</dvContaACreditar> para evitar exceção Java. |
| `<dvContaADebitar>` | Dígito verificador da conta corrente governamental de débito. | Envio — OP: xs:string, opcional | Ex.: 0. Omitido se tipoContaADebitar = 1. |
| `<exercicioFinanceiro>` | Exercício financeiro da OP a cancelar (no cancelamento, o nome da tag é este, não anoExercicioFinanceiro). | Envio — Cancelamento de OP: xs:int, obrigatório | 4 dígitos (ex.: 2026). |
| `<finalidadePagamento>` | Finalidade do pagamento. Obrigatória (erro 38727) quando tipoContaADebitar = 2 (Conta Específica) ou codigoFormaPagamento = 002 (Código de barras); dispensável com Conta Única e forma 001. O Manual GRP V16 lista os literais 'Recurso de Convênio', 'Contrapartida de Recurso de Convênio' e 'Não se aplica'. | Envio — OP: xs:string, opcional | Nos testes, o GRP aceitou qualquer texto nessa validação (ex.: 01, Não se aplica). Omitir a tag quando não for exigida. |
| `<gerarNumeroProcessoGrp>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<gerarNumeroProcessoGrpResponse>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags de resposta da chamada da API SOAP. |
| `<gerarSolicitacaoAnulacaoSaldoEmpenho>` | - | Envio — Anulação de empenho: grupo de campos, obrigatório | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<gerarSolicitacaoAnulacaoSaldoEmpenhoResponse>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags de resposta da chamada da API SOAP. |
| `<gerarSolicitacaoEmpenho>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<gerarSolicitacaoEmpenhoResponse>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags de resposta da chamada da API SOAP. |
| `<gerarSolicitacaoReforcoEmpenho>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<gerarSolicitacaoReforcoEmpenhoResponse>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags de resposta da chamada da API SOAP. |
| `<gerarSolicOrdemPagamentoBancaria>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<gerarSolicOrdemPagamentoBancariaResponse>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags de resposta da chamada da API SOAP. |
| `<identificadorProcessoExecucao>` | Identificador do fluxo de integração da API SOAP no GRP (ex.: EMPOLP1.1 para Empenho, EMPOLP2.1 para OLP, PGBANESC1.1.1 para OP). | Envio — Empenho, Reforço, Anulação de empenho, OLP, Anulação na OLP, OP, Cancelamento de OP: xs:string, obrigatório | Literal exato. Sensível a maiúsculas e minúsculas. Não alterar a string da operação. |
| `<indicadorReconhecimentoPassivo>` | Indica se o empenho refere-se ao reconhecimento de obrigação de exercício anterior ou passivo já constituído. | Envio — Empenho: xs:string, opcional | Literais aceitos: 'NAO' ou 'SIM'. |
| `<ItemDePagamento>` | Registro individual de vinculação da OP à OLP e Empenho a serem efetivamente pagos (ou número sequencial do item). | Envio — OP: grupo de campos, opcional, repetível | Grupo composto por <itemDePagamento>, <anoNumeroDaOlpEEmpenho>, <valorAPagar>, <valorTotalAPagar> e <valorLiquido>. |
| `<itemDePagamentoList>` | - | Envio — OP: lista, opcional | Elemento de envelope que encapsula a lista de itens de pagamento da chamada SOAP. |
| `<justificativa>` | Texto explicativo simples sobre o objeto da despesa. | Envio — Empenho, Reforço, Anulação de empenho, OLP, Anulação na OLP, OP, Cancelamento de OP: xs:string, obrigatório | Texto livre com descrição do objeto da despesa. |
| `<mensagem>` | - | Resposta — OP: grupo de campos, opcional, repetível | Elemento de envelope que encapsula as tags de mensagem de retorno. |
| `<mensagemResponseList>` | - | Resposta — OLP, Cancelamento de OP: lista, opcional | Elemento de envelope que encapsula a lista de mensagens de resposta da chamada SOAP. |
| `<mensagens>` | - | Resposta — OP: lista, opcional | Elemento de envelope que encapsula as tags de mensagens da chamada SOAP. |
| `<mesCompetenciaDespesa>` | Mês de referência do fato gerador do serviço prestado ou fornecimento realizado. | Envio — OLP: xs:int, obrigatório | Mês de 1 a 12, sem zero à esquerda (ex.: 8 para agosto). |
| `<mesCompetenciaRetencao>` | Mês de competência fiscal do fato gerador do tributo a ser recolhido aos cofres públicos. | Envio — OLP: xs:int, opcional | Mês de 1 a 12, sem zero à esquerda (ex.: 8). |
| `<numeroArquivo>` | Número de controle da remessa do arquivo bancário na Ordem de Pagamento. | Envio — Empenho, Reforço, Anulação de empenho, OLP, Anulação na OLP: xs:int, opcional · OP: xs:long, opcional · Cancelamento de OP: xs:string, opcional | Opcional no contrato. Os casos validados enviam <numeroArquivo>1</numeroArquivo>. |
| `<numeroDocumento>` | Número oficial do documento público definitivo gerado no GRP (Número do Empenho, Número da OLP ou Número da Ordem de Pagamento Bancária/OBM). | Resposta — OLP, OP: xs:long, opcional | Só números; retornado no XML de resposta. É o identificador fundamental que deve ser persistido pelo sistema cliente para encadear as etapas subsequentes. |
| `<numeroDocumentoEmpenho>` | Número oficial do empenho gerado previamente na etapa de Geração de Empenho que está sendo liquidado. | Envio — OLP: xs:long, opcional | Número do empenho (ex.: 41896). |
| `<numeroDocumentoOrdemDePagamento>` | Número do DOCUMENTO da OP a cancelar (o numeroDocumento da resposta da OP), não o número da solicitação. Um número errado cancela outra OP. | Envio — Cancelamento de OP: xs:string, obrigatório | Só números (ex.: 38536). |
| `<numeroEmpenho>` | Número oficial do empenho originário cadastrado no GRP sobre o qual incide a operação de reforço ou anulação de saldo. | Envio — Reforço, Anulação de empenho: xs:long, obrigatório | Número do empenho (ex.: 22575). O GRP herda automaticamente dotação, credor e domicílio bancário do empenho informado. |
| `<numeroOlp>` | Número do documento da OLP sobre a qual incide a anulação de valores. | Envio — Anulação na OLP: xs:long, obrigatório | Ex.: 22606. |
| `<numeroProcessoGeral>` | Número único institucional do processo GRP gerado previamente na operação Gerar Numero Processo GRP. | Envio — Empenho, OLP: xs:string, opcional · OLP: xs:string, obrigatório | Código de processo retornado na tag <return> da chamada Gerar Numero Processo GRP. |
| `<numeroRequisicao>` | Número único de controle para evitar duplicidade de envio. | Envio — Empenho, Reforço, Anulação de empenho, OLP, Anulação na OLP, OP, Cancelamento de OP: xs:long, obrigatório | Resposta — OLP, OP, Cancelamento de OP: xs:long, opcional | Só números, um número novo por chamada, nunca reaproveitado (nem depois de falha). Formato recomendado: data e hora AAMMDDhhmmss + dígitos sorteados. OP: 3 dígitos, 15 no total (ex.: 261027113130482), aceito em 27/10/2026. Demais serviços: 1 dígito, 13 no total (ex.: 2610271131304), até o teste com 15. Também aceitos: 10 dígitos e 13 no formato ano + UO + sequencial (26/10/2026). Números de 17 a 18 dígitos fizeram o GRP recusar as OPs (DataException, 14/09/2026). |
| `<numeroSolicitacao>` | Número sequencial único de controle gerado internamente pelo GRP para protocolar e rastrear a solicitação de serviço no barramento. | Resposta — OP: xs:long, opcional | Só dígitos; retornado no payload SOAP de resposta. |
| `<numeroSolicitacaoDeCancelamentoOP>` | Número da solicitação de cancelamento devolvido pelo GRP. | Resposta — Cancelamento de OP: xs:int, opcional | Retornado na resposta (ex.: 53). |
| `<numeroSolicitacaoOlp>` | Identificador sequencial único da solicitação de OLP gerado pelo barramento do GRP para protocolo. | Resposta — OLP: xs:long, opcional | Só dígitos; retornado no XML de resposta da OLP. |
| `<OlpDeEmpenho>` | - | Envio — OLP: grupo de campos, opcional | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<olpPendenteCreditoNaoRegularizar>` | - | Envio — Empenho: grupo de campos, opcional | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<origemPagamento>` | Identificação da origem do pagamento no módulo bancário (ex.: OLP Diversos). | Envio — OP: xs:string, obrigatório | Literal exato. 'OLP Diversos' para pagamento de OLP (validado). 'Retenção' é a origem da OP de retenção (INSS/ISSQN), ainda bloqueada por defeito no GRP. |
| `<RegionalizacaoDespesa>` | - | Envio — OLP: grupo de campos, opcional, repetível | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<regionalizacaoDespesaOlpRequestList>` | - | Envio — OLP: lista, opcional | Elemento de envelope que encapsula a lista de regionalizações de despesa da chamada SOAP. |
| `<Retencao>` | - | Envio — Anulação na OLP: grupo de campos, opcional, repetível | Resposta — OLP: grupo de campos, opcional, repetível | Elemento de envelope que encapsula as tags de retenção da chamada SOAP. |
| `<retencao>` | Bloco da retenção de Imposto de Renda (IRRF) inscrita na OP, dentro do <ItemDePagamento>, logo depois de <valorLiquido>. Em produção desde 19/10/2026. | Envio — OP: grupo de campos, opcional | Elemento complexo, no máximo 1 por item: <tipoRetencao> (10 = IRRF), <valorRetencao>, <codigoReceita>, <cpfCnpjCredorRetencao>; opcionais não testados: valorRendimentoTributavel, valorContribuicaoPrevidenciaSocial, valorTituloPensaoAlimenticia, qtdDependentesIR, valorRendimentosIsentos. |
| `<retencaoList>` | - | Não está no contrato atual (26/10/2026) | Elemento de envelope que encapsula a lista de retenções da chamada SOAP. |
| `<RetencaoOlp>` | - | Envio — OLP, Anulação na OLP: grupo de campos, opcional, repetível | Elemento de envelope que encapsula as tags de retenção da OLP da chamada SOAP. |
| `<retencaoOlpRequestList>` | - | Envio — OLP, Anulação na OLP: lista, opcional | Elemento de envelope que encapsula a lista de retenções de OLP da chamada SOAP. |
| `<RetencaoOrdemPagamento>` | - | Não está no contrato atual (26/10/2026) | Elemento de envelope que encapsula as tags de retenção da Ordem de Pagamento da chamada SOAP. |
| `<retencaoResponseList>` | - | Resposta — OLP: lista, opcional | Elemento de envelope que encapsula a lista de retenções da resposta SOAP. |
| `<return>` | Valor com a mensagem de retorno principal gerada pela chamada da API SOAP do GRP. | Resposta — Processo: xs:string, opcional · Empenho, Reforço, Anulação de empenho, OLP, Anulação na OLP, OP, Cancelamento de OP: grupo de campos, opcional | Varia por operação: 21 dígitos numéricos no GerarNumeroProcessoGrpWS; objeto complexo de retorno nas demais operações contendo numeroRequisicao, numeroSolicitacao, numeroDocumento, etc. |
| `<situacaoDocumento>` | Situação funcional e contábil do documento gerado no GRP (ex.: "Registrado e pendente de assinatura"). | Resposta — OLP, OP: xs:string, opcional | Texto. Informa a fase administrativa do documento no sistema de gestão pública estadual. |
| `<situacaoSolicitacao>` | Estado de processamento da solicitação no barramento de serviços do GRP (ex.: "Concluída" para solicitações aprovadas com êxito ou "Encaminhada para analise" em anulações/reforços). | Resposta — OLP, OP, Cancelamento de OP: xs:string, opcional | Texto. Retornado no XML de resposta indicando se a transação síncrona foi finalizada com sucesso. |
| `<solicitacaoEmpenho>` | - | Envio — Empenho: grupo de campos, obrigatório | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<solicitacaoOlp>` | - | Envio — OLP: grupo de campos, obrigatório | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<solicitacaoOrdemPagamentoBancaria>` | - | Envio — OP: grupo de campos, opcional | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<solicitacaoReforcoEmpenho>` | - | Envio — Reforço: grupo de campos, obrigatório | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<solicitarAnulacaoValoresNaOLP>` | - | Envio — Anulação na OLP: grupo de campos, obrigatório | Elemento da operação de anulação de valores na OLP; o elemento interno tem o mesmo nome da operação. |
| `<solicitarAnulacaoValoresNaOLPResponse>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags de resposta da anulação de valores na OLP. |
| `<solicitarOLP>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<solicitarOLPResponse>` | - | Operação (primeiro elemento dentro do Body) | Elemento de envelope que encapsula as tags de resposta da chamada da API SOAP. |
| `<tipoClassificacaoCredor>` | Classificação cadastral do favorecido da OLP no GRP (deve corresponder à usada no empenho). | Envio — OLP: xs:string, opcional | Sensível a acentuação e maiúsculas (ex.: BENEFICIÁRIOS DIVERSOS). |
| `<tipoContaACreditar>` | Classificação da conta do favorecido recebedor (1 - Conta Corrente, 2 - Poupança/Outras). | Envio — OP: xs:int, opcional | 1 ou 2. |
| `<tipoContaADebitar>` | Identifica se o débito sai da Conta Única do Tesouro (1) ou de uma Conta Específica (2). | Envio — OP: xs:int, opcional | 1 = Conta Única, 2 = Conta Específica. Opcional no contrato, mas enviado em todos os casos validados. |
| `<tipoEmpenhoComum>` | Modalidade de empenho quanto à forma de execução (ORDINARIO para despesa de valor certo e pagamento único; ESTIMATIVO para despesas com quantitativo incerto; GLOBAL para despesas contratuais parceladas). | Envio — Empenho: xs:string, obrigatório | Literais aceitos: 'ORDINARIO', 'ESTIMATIVO' ou 'GLOBAL'. Se omitido, adota 'ORDINARIO' por padrão. |
| `<tipoRetencao>` | Código do tipo de retenção. Na OLP (retencaoOlpRequestList): INSS 14 (aceito com credor CPF e CNPJ; 4 também foi aceito com credor CPF) e ISSQN 13. Na OP: IRRF 10, dentro do bloco <retencao> do item de pagamento. A OP não leva INSS nem ISSQN. | Envio — OLP, OP: xs:int, opcional | Resposta — OLP: xs:int, opcional | Só números (ex.: 13). |
| `<urlDocumento>` | Endereço eletrônico seguro (URL REST) fornecido pelo GRP para visualização, download ou impressão do espelho em PDF do documento gerado. | Resposta — OLP, OP: xs:string, opcional | URL HTTPS formatada. |
| `<valorAnulacaoEmpenho>` | Valor financeiro monetário a ser deduzido/anulado do saldo disponível do empenho originário, liberando a cota orçamentária. | Envio — Anulação de empenho: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 30.00). Aplicável a empenhos ordinários, estimativos ou globais. |
| `<valorAPagar>` | Valor financeiro alocado no item de pagamento referente à OLP individual. | Envio — OP: xs:decimal, opcional · OP: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 2153.21). |
| `<valorBrutoOlp>` | Valor financeiro total bruto da nota fiscal, fatura ou recibo que está sendo liquidado na OLP. | Envio — OLP: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 2153.21). |
| `<valorDistribuicao>` | Valor financeiro alocado ao município especificado na regionalização da OLP. | Envio — OLP: xs:decimal, opcional | Ponto decimal e 2 casas (ex.: 2153.21). O somatório das distribuições deve totalizar o valor da OLP. |
| `<valorEmpenho>` | Valor financeiro total do compromisso que está sendo reservado na dotação orçamentária. | Envio — Empenho: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 2153.21). |
| `<ValoresDaOlp>` | - | Envio — OLP: grupo de campos, obrigatório | Elemento de envelope que encapsula as tags da chamada da API SOAP. |
| `<valorLiquido>` | Valor financeiro líquido a ser efetivamente pago ao credor após as retenções tributárias. | Envio — OLP: xs:decimal, opcional · OP: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 2153.21). |
| `<valorLiquidoAnulado>` | Valor líquido anulado na OLP. | Envio — Anulação na OLP: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 500.00). Obrigatório. |
| `<valorLiquidoPagamento>` | Valor financeiro líquido efetivamente creditado na conta do favorecido. | Envio — OP: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 2153.21). |
| `<valorReforco>` | Valor financeiro monetário suplementar a ser acrescido ao saldo do empenho estimativo originário. | Envio — Reforço: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 50.00). Reforço aceito com empenho ESTIMATIVO; ORDINARIO é recusado; GLOBAL ainda não testado. |
| `<valorRetencao>` | Valor financeiro monetário da parcela individual retida para o tributo especificado (ex.: valor da retenção de INSS ou de ISSQN). | Envio — OLP, Anulação na OLP, OP: xs:decimal, opcional | Resposta — OLP: xs:decimal, opcional | Ponto decimal e 2 casas (ex.: 11.00). |
| `<valorRetencaoOlp>` | Valor financeiro total consolidado de todas as retenções tributárias (INSS, ISSQN, IR) incidentes sobre a OLP, que serão deduzidas do valor bruto. | Envio — OLP: xs:decimal, opcional | Ponto decimal e 2 casas (ex.: 11.00 ou 0.00). Deve ser estritamente igual à soma dos itens de retenção. |
| `<valorTotalAnulado>` | Valor total anulado na OLP. | Envio — Anulação na OLP: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 500.00). Obrigatório. |
| `<valorTotalAPagar>` | Valor financeiro consolidado no item de pagamento da Ordem de Pagamento. | Envio — OP: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 2153.21). |
| `<valorTotalAPagarDaOP>` | Valor total da OP. Sem IRRF: igual ao líquido (INSS/ISSQN já retidos na OLP). Com IRRF: valor antes do IRRF. | Envio — OP: xs:decimal, obrigatório | Ponto decimal e 2 casas (ex.: 2153.21). |
| `<valorTotalRetencoes>` | Na OP com IRRF: valor do IRRF inscrito no item (bloco <retencao>). Na OP sem IRRF: omitir a tag. | Envio — OP: xs:decimal, opcional | Ponto decimal e 2 casas (ex.: 0.00). |

---

## 8. 🔍 Tabela de Diagnóstico & Resolução de Erros SOAP do GRP

| Código | Etapa | Mensagem do GRP | Causa | Tratamento |
| :--- | :--- | :--- | :--- | :--- |
| `41040` | Empenho, OLP, manutenções | *Solicitação ... gerado(a) com sucesso!* | Sucesso. Nas manutenções a situação vem *Encaminhada para análise*, sem `numeroDocumento`. | Guardar `numeroSolicitacao` e `numeroDocumento`; acompanhar a tramitação das manutenções. |
| `51424` | OP bancária | *Solicitação de ordem de pagamento Bancária gerada com sucesso!* | Sucesso. | Guardar `numeroSolicitacao` (é o número pesquisável na consulta de OPs) e `numeroDocumento` (usado no cancelamento). |
| `54533` | Cancelamento de OP | *Solicitação de cancelamento gerada com sucesso* | Sucesso. | Guardar `numeroSolicitacaoDeCancelamentoOP`. |
| `30782` | Empenho, OLP | *Requisição em formato inválido* | XML inválido, wrapper ou nome de tag errado. | Conferir envelope, operação, wrappers e `CamelCase` das tags. |
| `44448` | OP bancária | *Requisição em formato inválido* | Estrutura incompatível; visto com `origemPagamento` errado. | Usar `OLP Diversos` e conferir a estrutura do item. |
| `25081` | Empenho, OLP | *Campo obrigatório ausente* | Campo exigido pela parametrização. Ex. (15/10/2026): empenho pedindo `numeroInstrumentoJuridicoEntrada` e procedimento de contratação numa combinação grupo/fonte/IPU nunca usada pela UO. | Conferir a parametrização do elemento-item e a combinação de dotação. |
| `38727` | OP bancária | *O campo finalidadePagamento é de preenchimento obrigatório* | `finalidadePagamento` ausente com conta específica (`tipoContaADebitar` 2) ou código de barras (forma 002). | Enviar a tag (o GRP aceitou qualquer texto, ex.: `Não se aplica`). |
| `39148` | OLP | *Divergência de valores de retenção* | `valorBrutoOlp − valorRetencaoOlp ≠ valorLiquido`. | Fechar a conta com 2 casas decimais. |
| `49762` | OLP | *Município de regionalização obrigatório* | Item exige regionalização. | Enviar `regionalizacaoDespesaOlpRequestList` com `codigoMunicipio` IBGE de 7 dígitos. |
| `40515` | OP bancária | *DV de agência inválido* | DV enviado para banco sem DV de agência. | Omitir `dvAgenciaACreditar` (Inter `077`, Nubank `260`, C6 `336`). |
| `85910` | Empenho, OP | *... não cadastrado no GRP* | Valor que não existe no cadastro: credor sem cadastro, classificação sem acento na OP, número de instrumento jurídico inexistente. | Usar a classificação exatamente como no cadastro (com acento) e números que existam no GRP. |
| `37144` | OP bancária | *Varia: leia a `descricao`* | Código genérico. Mensagens observadas: (a) *Erro inesperado... getExigeInstrumentoJuridico() is null* — toda OLP de exercício anterior (restos a pagar) pela API; (b) *Não existe parametrização para o segmento 3 e empresa 138 para a classificação ...* — código de barras de arrecadação incompatível com o credor; (c) *Ocorreu um erro ao contabilizar bloqueio de saldo. Causa: O saldo atual da Conta contábil ... é insuficiente* — a OLP não tem saldo contábil para o valor da OP (caso real de 08/10/2026). | (a) Pagar pela tela do GRP; caso aberto com a PRODEMGE. (b) Conferir o código de barras e o credor. (c) Conferir o saldo da OLP no GRP. |
| `45769` | OP bancária | *O Banco não aceita transmissão para pagamento por código de Barras* | O banco do boleto não aceita (visto com boleto do banco `756`; banco `001` aceito). | Pagar por outra forma. |
| `62229` | OP bancária | *Documento não permitido, a solicitação deve ser registrada via NOTA MINEIRA* | Sistema de origem diferente do sistema que criou a OLP. | Usar o mesmo sistema de origem da cadeia (ver regra do sistema de origem). |
| `123` | OP bancária | *O valor líquido informado (x) é menor que o valor calculado (y)* | OP com valores antes do IRRF, mas com o IRRF na `retencaoList` em vez do item. | Usar o formato do IRRF no item. |
| `93285` | OP bancária | *Valor líquido não pode ser negativo* | Cálculo do líquido errado. | Recalcular `valorLiquidoPagamento`. |
| `48860` | OP bancária | *Usuário não possui acesso a Unidade Administrativa ...* | Operador/ordenador sem acesso à UA informada. | Conferir UA e perfis no GRP. |
| `0` | Vários | *Erro inesperado. Causa: ...* | Regra de negócio. Ex.: *Ordenador de despesa não está autorizado para UO ..., UA ...* (ordenador sem autorização naquele exercício); *Tipo de Empenho não permite reforço* (reforço em empenho `ORDINARIO`). | Ler a causa; conferir ordenador, exercício e tipo do empenho. |
| `HTTP 500` Unmarshalling | OP bancária | *elemento inesperado (uri:"", local:"retencao")* | Servidor com o contrato antigo da OP (era a resposta da produção até 19/10/2026). | Conferir o endereço (use `www`). |
| `HTTP 500` Unmarshalling | Vários | *For input string: ""* | Tag numérica enviada vazia ou com texto (ex.: `numeroInstrumentoJuridicoEntrada`). | Omitir a tag ou enviar número. |
| Erro interno | OP de retenção | *NullPointerException em `getContribuinte()`; `Parameter value [4] did not match expected type [java.lang.Integer]`; `Parametro de pesquisa 'numeroUnicoOlp' não encontrado`* | OP com `origemPagamento` *Retenção* (pagar INSS/ISSQN ao arrecadador): defeito do GRP no campo `tipoDeRetencao`. | Ainda não é possível pela API (14/10/2026). Caso aberto com a PRODEMGE. |
| Erro contábil | Empenho, OLP, OP | *Natureza item da despesa não possui parametrização contábil* | Elemento/item sem amarração contábil no exercício. | Acionar a STE/SEF. |
| Bloqueio | Vários | *... janela de cópia dos dados do armazém ...* | Bloqueio temporário de processamento (visto uma vez entre 23h55 e 0h30). | Aguardar e repetir a mesma chamada. |
| `HTTP 301` | Todos | *Moved Permanently* | Endereço sem `www`. | Usar `www` ou reenviar o `POST` ao `Location`. |

> Uma resposta de sucesso não basta: confira também `situacaoSolicitacao`, `numeroDocumento` e `situacaoDocumento`. Quando a chamada fica sem resposta (tempo esgotado), consulte o GRP pelo Nº da solicitação antes de reenviar, para não gerar documento em dobro.

---

## 9. 🐍 Template de Código Pronto em Python (`requests`)

Snippet didático e funcional para disparo da primeira etapa (`GerarNumeroProcessoGrpWS`) com tratamento de proxy e SSL corporativo:

```python
import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

# 1. Configuração do Endpoint e Headers SOAP
url = "https://www.grp.servicos.mg.gov.br/serviceBus/institucional/GerarNumeroProcessoGrpWS"
headers = {"Content-Type": "text/xml; charset=utf-8"}

# 2. Payload XML de Envio
xml_payload = '''<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:grp="http://interfaces.webservices.institucional.business.grp.prodemge.gov.br/">
  <soapenv:Header/>
  <soapenv:Body>
    <grp:gerarNumeroProcessoGrp>
      <anoExercicio>2026</anoExercicio>
      <codigoOrgao>10190</codigoOrgao>
      <codigoProcessoDeNegocio>18</codigoProcessoDeNegocio>
      <codigoUnidadeAdministrativa>1019080124</codigoUnidadeAdministrativa>
      <codigoUnidadeOrcamentaria>10191</codigoUnidadeOrcamentaria>
      <codigoSistemaSolicitante>51</codigoSistemaSolicitante>
    </grp:gerarNumeroProcessoGrp>
  </soapenv:Body>
</soapenv:Envelope>'''

# 3. Disparo da Requisição HTTP POST
session = requests.Session()
session.trust_env = False  # Desativa interferência de proxies locais da rede
response = session.post(url, data=xml_payload.encode('utf-8'), headers=headers, verify=False, timeout=30)

print(f"Status Code: {response.status_code}")
print(f"XML de Retorno: {response.text}")
```

---

## 10. ⚠️ Divergências em Verificação

Pontos em que as versões anteriores dos dois documentos diziam coisas diferentes e que dependem de teste real. Esta lista vale para os dois documentos.

| # | Assunto | Versão A | Versão B | Como verificar |
| :--- | :--- | :--- | :--- | :--- |
| D4 | Tipo de empenho no reforço | Só `ESTIMATIVO` testado; `ORDINARIO` recusado (DOCUMENTACAO). | `ESTIMATIVO` ou `GLOBAL` (manual v1, sem teste com `GLOBAL`). | Reforço num empenho `GLOBAL`. |

**Resolvidas em 26/10/2026:**

* **D3 — significado do `37144`:** as duas versões estavam certas. O `37144` é um código genérico (*Solicitação não registrada... Causa: ...*), e saldo contábil insuficiente é uma das causas: caso real de 08/10/2026, *O saldo atual da Conta contábil ... é insuficiente para o lançamento*. Leia sempre a causa (tabela de erros).
* **D1 — reforço de empenho** (pelos contratos da produção e do desenvolvimento): os campos vão direto em `<solicitacaoReforcoEmpenho>` (`numeroEmpenho`, UO, órgão, UA, ordenador, operador, `valorReforco`, justificativa). O bloco `<reforcoDeEmpenhoComum>` da versão 1 do manual não existe no contrato.
* **D2 — anulação de empenho** (pelos mesmos contratos): o elemento interno é `<gerarSolicitacaoAnulacaoSaldoEmpenho>`, com os campos direto. `<solicitacaoAnulacaoSaldoEmpenho>` e `<anulacaoSaldoEmpenhoComum>` não existem no contrato.

---

## 11. 🗂️ Histórico de Versões

| Versão | Data | Mudanças |
| :--- | :--- | :--- |
| 2.1 | 26/10/2026 | • Árvore interativa refeita: monta cada chamada com os dados de quem usa, confere as regras aprendidas nos testes reais (as mesmas do Assistente GRP), envia ao GRP pela própria página ou por comando pronto e explica a resposta. Os 64 cenários de 23/09/2026 deixam de ser a base da árvore e ficam como histórico.<br>• Nova seção *Como reproduzir os testes* nos dois documentos.<br>• Divergência D3 resolvida: o `37144` também aparece com *saldo contábil insuficiente* (caso real de 08/10/2026).<br>• `numeroRequisicao` montado com data e hora (AAMMDDhhmmss) + dígitos sorteados: 15 dígitos na OP (aceito em 27/10/2026) e 13 nos demais serviços; 17 a 18 dígitos recusados. Barra (`/`) na justificativa da OP quebra a chamada.<br>• Textos de rede valem para todos os órgãos: rede do Governo ou VPN.<br>• Auditoria de 26/10/2026: exemplos de envio no formato do contrato atual (os enviados em formato antigo foram ajustados, com os mesmos valores); dicionário com o tipo de cada tag lido do contrato, por serviço; campos fora do contrato separados; orientação do credor não cadastrado corrigida; `numeroRequisicao` sem repetição e resultado indeterminado no tempo esgotado; CPFs e contas reais retirados das fontes.<br>• Ciclo da despesa: não é preciso fazer todas as etapas pela API; documentos registrados pela tela do GRP podem continuar pela API (exceto os do Portal de Compras).<br>• Árvore: pré-requisitos e operações de manutenção com explicação completa (*Leia mais*). |
| 2.0 | 26/10/2026 | • Retenção de Imposto de Renda (IRRF) na OP bancária: formato aceito na produção desde 19/10/2026, com o envio e a resposta reais (solicitação 130905).<br>• INSS e ISSQN só na OLP; a `retencaoList` da OP saiu do contrato novo.<br>• Matriz com os 8 serviços (incluídos anulação de valores na OLP e cancelamento de OP no manual), endereços com `www` e o script `scripts/baixar_contratos_wsdl.py` para baixar e conferir os contratos.<br>• Regra do sistema de origem (mesmo sistema em todas as etapas; Portal de Compras não paga pela API).<br>• Tabela única de erros e tratamentos, com as mensagens observadas em chamadas reais.<br>• Exemplos de envio e resposta por cenário.<br>• Correções: ISSQN na OLP é o tipo `13`; `codigoFormaPagamento` `002` é código de barras; `finalidadePagamento` aceita texto e só é exigida com conta específica ou código de barras; zeros à esquerda são opcionais nos códigos numéricos da dotação.<br>• Dicionário de tags: 15 tags novas (IRRF, código de barras, anulação de valores na OLP e cancelamento de OP), passando de 123 para 138; textos corrigidos de forma de pagamento, finalidade, retenções e zeros à esquerda.<br>• Contratos WSDL da produção e do desenvolvimento baixados em 26/10/2026 (idênticos; o `?wsdl` da produção voltou a responder): estrutura do reforço e da anulação de empenho confirmada (divergências D1 e D2 resolvidas; modelos `manut_*.xml.j2` corrigidos).<br>• Lista de divergências ainda em verificação. |
| 1.x | 06/2026 a 09/2026 | • DOCUMENTACAO: 8 serviços validados com o sistema 51 (casos de 28/05 a 16/06/2026).<br>• Manual: 6 serviços e matriz de 64 cenários homologados (base de 23/09/2026). |
