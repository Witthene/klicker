# Klicker

Auto clicker de código aberto para Windows, inspirado no GS Auto Clicker, com interface
no estilo **Liquid Glass**: vidro translúcido com desfoque real do fundo, controles com
brilho especular, seletor deslizante "líquido" e um botão-orbe que pulsa enquanto clica.

## Recursos

| | GS Auto Clicker 3.1.4 | Klicker |
|---|---|---|
| Botão esquerdo / meio / direito | ✓ | ✓ |
| Clique simples / duplo | ✓ | ✓ + triplo |
| Intervalo h / min / s / ms | ✓ | ✓ + variação aleatória (± ms) |
| Repetir N vezes ou até parar | ✓ | ✓ + por duração |
| Clicar na posição do cursor ou em pontos gravados | ✓ | ✓ com seletor em tela cheia (multi-monitor) |
| Atalho global (F8) | ✓ | ✓ qualquer combinação (Ctrl/Alt/Shift/Win) |
| Contador de cliques, tempo e cliques/s ao vivo | – | ✓ |
| Nunca clicar sobre a própria janela | – | ✓ |
| Devolver o cursor após clicar em pontos fixos | – | ✓ |
| Sempre no topo, ícone na bandeja | parcial | ✓ |
| Tema claro / escuro (segue o Windows) | – | ✓ |
| Respeita "inverter botões do mouse" | ✓ | ✓ |
| Configurações salvas | registro | JSON em `%APPDATA%\Klicker` |

## Gravador de macros (estilo TinyTask)

Na aba **Macro**, grave tudo o que você faz com mouse e teclado e reproduza depois.

| | TinyTask 1.77 | Klicker |
|---|---|---|
| Gravar / reproduzir mouse e teclado | ✓ | ✓ (também roda do mouse e botões laterais) |
| Atalhos Ctrl+Shift+Alt+R / Ctrl+Shift+Alt+P | ✓ | ✓ configuráveis |
| Pause ou Scroll Lock param a reprodução | ✓ | ✓ |
| Velocidade 1x, 2x, 100x ou personalizada (1–100) | ✓ | ✓ |
| Repetir N vezes ou contínuo | ✓ | ✓ |
| Salvar / abrir gravações | `.rec` | `.kmacro` (JSON legível) |
| Compilar a macro em um `.exe` independente | ✓ | ✓ |
| Última gravação mantida entre sessões | – | ✓ |
| Libera teclas/botões presos se a reprodução for interrompida | – | ✓ |
| Ignora cliques na própria janela e o atalho usado para parar | – | ✓ |

A gravação usa ganchos de baixo nível do Windows (`WH_MOUSE_LL` / `WH_KEYBOARD_LL`) e
ignora entradas sintéticas, então a reprodução nunca é regravada por engano.

## Calculadora de drops (aba Drops)

Para jogos de farm (Roblox e afins): informe a chance do item (em `%` ou `1 em N`), o
multiplicador de sorte, quantos itens vêm por drop, o tempo de uma fase (ou cronometre
uma) e o pity, se houver. O Klicker mostra:

- tempo e número de fases **em média** até o drop;
- até quando você pega em **50%, 90% e 99%** das vezes (sorte normal, azar, azar extremo);
- o **pior cenário** garantido pelo pity (ou quanto leva o 1 em 1.000 mais azarado, sem pity);
- quanto tempo para juntar **N itens**;
- quantos itens você farma em **X horas** e a chance de vir pelo menos um.

O pity considera que o contador zera a cada drop e aceita o progresso que você já tem.
Antigas configurações e macros `.gcmacro` do Glass Clicker continuam funcionando.

## Temas

Sistema, Escuro, Claro e **Anime**: um céu de entardecer com lua, estrelas, montanhas e
pétalas de sakura caindo atrás do vidro, tudo desenhado por código. Qualquer tema aceita
uma **imagem de fundo** própria (um wallpaper de anime, por exemplo).

## Executar a partir do código

Requer Windows 10/11 e Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m klicker
```

## Gerar o .exe

```powershell
.\build.ps1        # gera dist\Klicker.exe
```

## Testes

```powershell
.\.venv\Scripts\python -m unittest discover -s tests
```

O motor de cliques (`klicker/engine.py`) recebe o backend de entrada por injeção,
então os testes rodam sem mover o mouse de verdade.

## Estrutura

```
klicker/
  engine.py    laço de cliques numa thread (temporização precisa, sem rajadas)
  odds.py      calculadora de drops (média, percentis, pity, farm)
  macro.py     gravador/reprodutor de macros, arquivos .kmacro e compilação para .exe
  headless.py  modo só-reprodução usado pelos .exe compilados
  scene.py     cenário anime animado (céu, lua, pétalas de sakura)
  winapi.py    SendInput, hooks, RegisterHotKey, acrylic/DWM via ctypes
  window.py    janela principal
  widgets.py   controles Liquid Glass desenhados à mão (card, segmented, toggle, orbe)
  picker.py    sobreposição em tela cheia para escolher pontos
  theme.py     paletas clara/escura e stylesheet
  settings.py  preferências em JSON
  icon.py      ícone gerado por código
```

## Licença

MIT — veja [LICENSE](LICENSE).
