🇬🇧 [English](README.md) · 🇨🇳 [中文](README.zh.md) · 🇪🇸 [Español](README.es.md) · 🇮🇳 [हिन्दी](README.hi.md) · 🇸🇦 [العربية](README.ar.md) · 🇵🇹 [Português](README.pt.md) · 🇷🇺 [Русский](README.ru.md) · 🇫🇷 [Français](README.fr.md) · 🇯🇵 [日本語](README.ja.md) · 🇩🇪 [Deutsch](README.de.md)

# Gazette Drouot watcher

Vigia uma ou várias páginas de rubrica (listas de artigos) do gazette-drouot.com e mostra uma notificação do Windows para cada artigo novo ou atualizado — clique numa notificação para o abrir no seu navegador predefinido.

## Como funciona

- A cada execução, as primeiras `MAX_PAGES` páginas de listagem de cada rubrica configurada são totalmente analisadas (não apenas até encontrar um artigo "conhecido" — os testes mostraram que a paginação do site não é fiavelmente cronológica, por isso parar cedo poderia perder novidades reais em silêncio).
- Cada artigo encontrado é comparado com o estado guardado (`state/<rubrique-key>.json`, sob `%LOCALAPPDATA%\GazetteDrouotWatcher\`) pelo seu id numérico **e** pela sua data de publicação. Id novo → notifica. Id conhecido mas com data diferente da anterior → notifica novamente (o artigo foi provavelmente republicado/editado). Um artigo sem data apresentada só é notificado uma vez e nunca mais é verificado.
- A primeira execução para uma rubrica apenas regista o que existe atualmente como base, em silêncio — sem avalanche de notificações para artigos pré-existentes na instalação.
- Se aparecerem mais de `FLOOD_CAP` artigos novos/atualizados numa rubrica numa única execução, só os primeiros têm notificação própria — o resto é agrupado numa notificação-resumo de "mais N".

## Configuração inicial

- **A VPN tem de estar desligada** enquanto isto corre — o Cloudflare força um desafio interativo em IPs de VPN que a automação não consegue resolver. Um IP doméstico normal passa sem problemas.
- Requer o Microsoft Edge instalado (usa o seu Edge do sistema através do `channel="msedge"` do Playwright, sem necessidade de transferir um navegador à parte).
- `pip install -r requirements.txt`

## Configuração

**`config.py` é o único ficheiro a editar** para tudo: que páginas vigiar, com que frequência verificar, que profundidade analisar, limites de notificação, tempos de espera de alertas, etc. — cada definição tem um comentário explicativo (ou edite-as no separador Definições do painel de controlo, ver abaixo). Fica em `%LOCALAPPDATA%\GazetteDrouotWatcher\config.py` (criado automaticamente aí na primeira execução — não junto ao `.exe`), pelo que sobrevive a mover ou substituir o próprio `.exe`. Após qualquer alteração aí, o efeito surge na próxima execução, **exceto** `POLL_INTERVAL_MINUTES`, que também requer clicar novamente em **Instalar** no painel de controlo para atualizar a tarefa real do Agendador de Tarefas do Windows com o novo intervalo.

## Painel de controlo (GUI)

**Esta é a aplicação** — um único `.exe` autónomo, sem necessidade de instalação separada do Python nem de ficheiros de script na máquina que o executa. Uma janela de ambiente de trabalho para tudo: instalar / ativar / desativar / desinstalar a tarefa agendada (diretamente através da API nativa do Agendador de Tarefas, sem PowerShell), e um painel de definições (com "Repor predefinições" caso algo corra mal) em vez de editar o ficheiro de configuração à mão. O ícone da bandeira muda o idioma da interface (inglês, 中文, español, हिन्दी, العربية, português, русский, français, 日本語, alemão — segue por defeito o idioma do Windows, recorrendo ao inglês caso não seja suportado); o ícone sol/lua alterna entre claro/escuro (segue por defeito o tema do Windows). Ambas as escolhas persistem em `%LOCALAPPDATA%\GazetteDrouotWatcher\gui_prefs.json`.

**Se só tem o `.exe`:** faça duplo clique em `GazetteDrouotWatcher.exe` — nada mais a instalar, e nada mais necessário ao lado. É totalmente autónomo: `config.py`, `gui_prefs.json`, `state/` e `logs/` são todos criados sob `%LOCALAPPDATA%\GazetteDrouotWatcher\` na primeira execução, não junto ao próprio `.exe`, pelo que nunca espalha ficheiros pela pasta a partir da qual é executado. Clique em **Instalar** na janela para registar a tarefa agendada — a partir daí, a verificação acontece automaticamente em segundo plano, no intervalo definido em `config.py`, sem que esta janela (nem a aplicação) precise de ficar aberta, e reinicia-se sozinha após cada reinício do PC.

**A executar a partir do código-fonte:** faça duplo clique em `main.pyw` (o Windows executa ficheiros `.pyw` através do `pythonw.exe`, sem janela de consola), ou:
```
pythonw.exe main.pyw
```

**Para compilar o `.exe` você mesmo** (está excluído pelo gitignore — não é submetido ao repositório, recompile-o ou obtenha-o de uma Release):
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name GazetteDrouotWatcher --icon icon.ico main.pyw
```
Depois copie `dist/GazetteDrouotWatcher.exe` para a raiz do projeto (junto a `main.pyw`) e apague os restos de `build/`, `dist/` e `*.spec`.

## Execução manual

`main.pyw --watch` (ou o equivalente `GazetteDrouotWatcher.exe --watch`) é o que a tarefa agendada realmente chama — executa uma verificação e termina, sem interface. Também equivale a:
```
python -m gazette_watcher.watcher
```

## Se algo correr mal

Existem duas notificações de alerta distintas, cada uma limitada a no máximo uma por `ALERT_COOLDOWN_HOURS` (config.py) para que um problema contínuo não sature com uma notificação a cada execução:

- **"blocked by Cloudflare"** — a proteção anti-bot do site interceptou o pedido. Quase sempre resolvido desligando uma VPN.
- **"needs an update"** — uma página carregou bem mas o seu HTML já não corresponde ao que este script espera. É mais provável que o gazette-drouot.com tenha mudado o esquema das suas páginas e os seletores do scraper (`gazette_watcher/scraper.py`) precisem de ser atualizados para corresponder.

`%LOCALAPPDATA%\GazetteDrouotWatcher\logs\watcher.log` tem o detalhe completo de cada execução — consulte primeiro aqui se as notificações deixarem de aparecer.

## Testar sem tocar no site real

`test/` contém um pequeno ambiente de teste com um site falso local, para testar a lógica de scraping/notificação isoladamente, sem sobrecarregar o site real nem depender do seu conteúdo ao vivo. Veja `test/README.md`.

## Adicionar outra página a vigiar

Adicione outra entrada a `RUBRIQUES` em `config.py` — desde que a página use a mesma estrutura de cartão `div.articleResume`, mais nada precisa de mudar.
