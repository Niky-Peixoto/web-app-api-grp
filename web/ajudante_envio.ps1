# Ajudante de envio da Árvore interativa da API do GRP
# Deixa a página da árvore enviar os XMLs ao GRP pelo curl.exe deste computador (o mesmo transporte do Assistente GRP).
# - Só aceita pedidos deste computador (127.0.0.1) que tragam a chave da sua página.
# - Só envia para os endereços do GRP. Não guarda nada além do último envio e da última resposta, na pasta temporária.
# Para desligar, feche esta janela.
$porta = 8765
$chave = '__CHAVE__'
$hostsPermitidos = @('www.grp.servicos.mg.gov.br', 'desenvolvimento.grp.servicos.mg.gov.br')
$pasta = Join-Path $env:TEMP 'arvore-grp'
New-Item -ItemType Directory -Force -Path $pasta | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding $false

function Responder($fluxo, $codigo, $texto, [byte[]]$corpo, $extras) {
  $cabecalho = "HTTP/1.1 $codigo $texto`r`n" +
    "Access-Control-Allow-Origin: *`r`n" +
    "Access-Control-Allow-Headers: Content-Type, X-Chave`r`n" +
    "Access-Control-Allow-Methods: GET, POST, OPTIONS`r`n" +
    "Access-Control-Allow-Private-Network: true`r`n" +
    "Access-Control-Expose-Headers: X-Grp-Status`r`n" +
    "Content-Type: text/plain; charset=utf-8`r`n" +
    "Content-Length: $($corpo.Length)`r`n" + $extras + "Connection: close`r`n`r`n"
  $bytes = [System.Text.Encoding]::ASCII.GetBytes($cabecalho)
  $fluxo.Write($bytes, 0, $bytes.Length)
  if ($corpo.Length -gt 0) { $fluxo.Write($corpo, 0, $corpo.Length) }
}

$escuta = New-Object System.Net.Sockets.TcpListener ([System.Net.IPAddress]::Loopback, $porta)
try { $escuta.Start() } catch {
  Write-Host "Não consegui usar a porta $porta. O ajudante já está aberto em outra janela?" -ForegroundColor Red
  return
}
Write-Host ''
Write-Host "Ajudante de envio ligado (http://127.0.0.1:$porta)." -ForegroundColor Green
Write-Host 'Volte para a árvore: o botão "Enviar ao GRP" já está liberado.'
Write-Host 'Deixe esta janela aberta enquanto usa a árvore. Para desligar, feche a janela.'
Write-Host 'Não clique dentro desta janela: o Windows pausa o PowerShell. Se clicar, tecle Esc.' -ForegroundColor Yellow
Write-Host ''

while ($true) {
  $cliente = $escuta.AcceptTcpClient()
  try {
    $fluxo = $cliente.GetStream()
    # O navegador às vezes abre conexões de reserva sem mandar nada: não esperar por elas mais que 2 segundos.
    $fluxo.ReadTimeout = 2000
    $buffer = New-Object byte[] 65536
    $recebido = New-Object System.IO.MemoryStream
    $fimCabecalho = -1
    while ($fimCabecalho -lt 0) {
      $lidos = $fluxo.Read($buffer, 0, $buffer.Length)
      if ($lidos -le 0) { break }
      $recebido.Write($buffer, 0, $lidos)
      # ASCII: um caractere por byte, então a posição no texto é a posição nos bytes
      $texto = [System.Text.Encoding]::ASCII.GetString($recebido.ToArray())
      $fimCabecalho = $texto.IndexOf("`r`n`r`n")
    }
    if ($fimCabecalho -lt 0) { continue }
    $linhas = $texto.Substring(0, $fimCabecalho) -split "`r`n"
    $metodo, $alvo = ($linhas[0] -split ' ')[0, 1]
    $tamanho = 0
    $chaveRecebida = ''
    foreach ($linha in $linhas) {
      if ($linha -match '^Content-Length:\s*(\d+)') { $tamanho = [int]$Matches[1] }
      if ($linha -match '^X-Chave:\s*(\S+)') { $chaveRecebida = $Matches[1] }
    }
    while ($recebido.Length - ($fimCabecalho + 4) -lt $tamanho) {
      $lidos = $fluxo.Read($buffer, 0, $buffer.Length)
      if ($lidos -le 0) { break }
      $recebido.Write($buffer, 0, $lidos)
    }
    $tudo = $recebido.ToArray()
    $corpo = New-Object byte[] $tamanho
    [Array]::Copy($tudo, $fimCabecalho + 4, $corpo, 0, [Math]::Min($tamanho, $tudo.Length - $fimCabecalho - 4))

    if ($metodo -eq 'OPTIONS') { Responder $fluxo 204 'No Content' (New-Object byte[] 0) ''; continue }
    if ($chaveRecebida -ne $chave) { Responder $fluxo 403 'Forbidden' ($utf8.GetBytes('chave errada: copie o ajudante de novo da página')) ''; continue }
    if ($metodo -eq 'GET' -and $alvo -like '/status*') { Responder $fluxo 200 'OK' ($utf8.GetBytes('ajudante-grp-ok')) ''; continue }
    if ($metodo -ne 'POST' -or $alvo -notlike '/enviar?destino=*') { Responder $fluxo 404 'Not Found' ($utf8.GetBytes('pedido desconhecido')) ''; continue }

    $destino = [Uri]::UnescapeDataString($alvo.Substring('/enviar?destino='.Length))
    $uri = $null
    if (-not [Uri]::TryCreate($destino, [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -ne 'https' -or $hostsPermitidos -notcontains $uri.Host) {
      Responder $fluxo 403 'Forbidden' ($utf8.GetBytes("destino não permitido: $destino")) ''
      continue
    }
    $arquivoEnvio = Join-Path $pasta 'envio.xml'
    $arquivoResposta = Join-Path $pasta 'resposta.xml'
    [System.IO.File]::WriteAllBytes($arquivoEnvio, $corpo)
    if (Test-Path $arquivoResposta) { Remove-Item $arquivoResposta }
    Write-Host ('{0:HH:mm:ss}  enviando para {1}' -f (Get-Date), $uri.AbsoluteUri)
    $status = & curl.exe -s -S -o $arquivoResposta -w '%{http_code}' -X POST -H 'Content-Type: text/xml; charset=utf-8' -H 'SOAPAction:' --data-binary "@$arquivoEnvio" --max-time 90 $uri.AbsoluteUri 2>&1
    if ($LASTEXITCODE -ne 0) {
      Write-Host "          curl.exe falhou: $status" -ForegroundColor Yellow
      # 6, 7, 35, 60: não resolveu o nome, não conectou ou o TLS falhou - a chamada não chegou ao GRP.
      # Os outros (28 = tempo esgotado, 52/56 = conexão cortada...) podem ter acontecido depois do envio:
      # o resultado é indeterminado e a página pede para consultar o GRP antes de reenviar.
      if (@(6, 7, 35, 60) -contains $LASTEXITCODE) {
        Responder $fluxo 502 'Bad Gateway' ($utf8.GetBytes("a chamada não chegou ao GRP (curl.exe, código $LASTEXITCODE): $status")) ''
      } else {
        Responder $fluxo 504 'Gateway Timeout' ($utf8.GetBytes("o GRP não respondeu (curl.exe, código $LASTEXITCODE): $status")) ''
      }
      continue
    }
    $resposta = if (Test-Path $arquivoResposta) { [System.IO.File]::ReadAllBytes($arquivoResposta) } else { New-Object byte[] 0 }
    Write-Host ('          resposta HTTP {0} ({1} bytes)' -f $status, $resposta.Length)
    Responder $fluxo 200 'OK' $resposta "X-Grp-Status: $status`r`n"
  } catch [System.IO.IOException] {
    # conexão que não mandou nada a tempo (reserva do navegador): ignorar
  } catch {
    Write-Host "Erro no ajudante: $_" -ForegroundColor Yellow
  } finally {
    $cliente.Close()
  }
}
