🇬🇧 [English](README.md) · 🇨🇳 [中文](README.zh.md) · 🇪🇸 [Español](README.es.md) · 🇮🇳 [हिन्दी](README.hi.md) · 🇸🇦 [العربية](README.ar.md) · 🇵🇹 [Português](README.pt.md) · 🇷🇺 [Русский](README.ru.md) · 🇫🇷 [Français](README.fr.md) · 🇯🇵 [日本語](README.ja.md) · 🇩🇪 [Deutsch](README.de.md)

# Gazette Drouot watcher

Vigia uma ou várias páginas de rubrica (listas de artigos) do gazette-drouot.com e mostra uma notificação do Windows para cada artigo novo ou atualizado — clique numa notificação para o abrir no seu navegador predefinido.

## Como funciona

- A cada execução, as primeiras `MAX_PAGES` páginas de listagem de cada rubrica configurada são totalmente analisadas (não apenas até encontrar um artigo "conhecido" — os testes mostraram que a paginação do site não é fiavelmente cronológica, por isso parar cedo poderia perder novidades reais em silêncio).
- Cada artigo encontrado é comparado com o estado guardado (`state/<rubrique-key>.json`) pelo seu id numérico **e** pela sua data de publicação. Id novo → notifica. Id conhecido mas com data diferente da anterior → notifica novamente (o artigo foi provavelmente republicado/editado). Um artigo sem data apresentada só é notificado uma vez e nunca mais é verificado.
- A primeira execução para uma rubrica apenas regista o que existe atualmente como base, em silêncio — sem avalanche de notificações para artigos pré-existentes na instalação.
- Se aparecerem mais de `FLOOD_CAP` artigos novos/atualizados numa rubrica numa única execução, só os primeiros têm notificação própria — o resto é agrupado numa notificação-resumo de "mais N".

## Configuração inicial

- **A VPN tem de estar desligada** enquanto isto corre — o Cloudflare força um desafio interativo em IPs de VPN que a automação não consegue resolver. Um IP doméstico normal passa sem problemas.
- Requer o Microsoft Edge instalado (usa o seu Edge do sistema através do `channel="msedge"` do Playwright, sem necessidade de transferir um navegador à parte).
- `pip install -r requirements.txt`

## Configuração

**`gazette_watcher/config.py` é o único ficheiro a editar** para tudo: que páginas vigiar, com que frequência verificar, que profundidade analisar, limites de notificação, tempos de espera de alertas, etc. — cada definição tem um comentário explicativo. Após qualquer alteração aí, o efeito surge na próxima execução, **exceto** `POLL_INTERVAL_MINUTES`, que também requer voltar a executar `install_task.ps1` uma vez para atualizar a tarefa real do Agendador de Tarefas do Windows.

## Painel de controlo (GUI)

Uma janela de ambiente de trabalho para tudo o que se segue sem tocar diretamente no PowerShell ou no config.py: instalar / ativar / desativar / desinstalar a tarefa agendada, e um painel de definições (com "Repor predefinições" caso algo corra mal) em vez de editar o ficheiro de configuração à mão. O ícone da bandeira muda o idioma da interface (inglês, 中文, español, हिन्दी, العربية, português, русский, français, 日本語, alemão — segue por defeito o idioma do Windows, recorrendo ao inglês caso não seja suportado); o ícone sol/lua alterna entre claro/escuro (segue por defeito o tema do Windows). Ambas as escolhas persistem em `gui_prefs.json`.

**Se só tem o `.exe`:** faça duplo clique em `GazetteDrouotWatcherGUI.exe` — nada mais a instalar. Deve estar diretamente nesta pasta do projeto, junto a `gazette_watcher/`, `install_task.ps1`, etc.

**A executar a partir do código-fonte:** faça duplo clique em `gui.pyw` (o Windows executa ficheiros `.pyw` através do `pythonw.exe`, sem janela de consola), ou:
```
pythonw.exe gui.pyw
```

**Para compilar o `.exe` você mesmo** (está excluído pelo gitignore — não é submetido ao repositório, recompile-o ou obtenha-o de uma Release):
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name GazetteDrouotWatcherGUI --icon icon.ico gui.pyw
```
Depois copie `dist/GazetteDrouotWatcherGUI.exe` para a raiz do projeto (junto a `gui.pyw`) e apague os restos de `build/`, `dist/` e `*.spec`.

## Execução manual

```
python -m gazette_watcher.watcher
```

## Agendamento

Execute `install_task.ps1` para registar uma tarefa "GazetteDrouotWatcher" no Agendador de Tarefas, que corre no intervalo definido em `config.py`, enquanto estiver com sessão iniciada. Volte a executá-lo a qualquer momento (por exemplo, após alterar `POLL_INTERVAL_MINUTES`) para atualizar a tarefa já registada.

```
powershell -ExecutionPolicy Bypass -File install_task.ps1
```

Para a executar uma vez de imediato, para testes:
```
powershell -Command "Start-ScheduledTask -TaskName GazetteDrouotWatcher"
```

Remova-a com `uninstall_task.ps1`:
```
powershell -ExecutionPolicy Bypass -File uninstall_task.ps1
```

## Se algo correr mal

Existem duas notificações de alerta distintas, cada uma limitada a no máximo uma por `ALERT_COOLDOWN_HOURS` (config.py) para que um problema contínuo não sature com uma notificação a cada execução:

- **"blocked by Cloudflare"** — a proteção anti-bot do site interceptou o pedido. Quase sempre resolvido desligando uma VPN.
- **"needs an update"** — uma página carregou bem mas o seu HTML já não corresponde ao que este script espera. É mais provável que o gazette-drouot.com tenha mudado o esquema das suas páginas e os seletores do scraper (`gazette_watcher/scraper.py`) precisem de ser atualizados para corresponder.

`logs/watcher.log` tem o detalhe completo de cada execução — consulte primeiro aqui se as notificações deixarem de aparecer.

## Testar sem tocar no site real

`test/` contém um pequeno ambiente de teste com um site falso local, para testar a lógica de scraping/notificação isoladamente, sem sobrecarregar o site real nem depender do seu conteúdo ao vivo. Veja `test/README.md`.

## Adicionar outra página a vigiar

Adicione outra entrada a `RUBRIQUES` em `config.py` — desde que a página use a mesma estrutura de cartão `div.articleResume`, mais nada precisa de mudar.
