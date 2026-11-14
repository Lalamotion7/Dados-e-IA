# AGV Tracking Intelligence — Desafio TechLab

Protótipo de hiperautomação para transformar eventos brutos de rastreio (TMS, aplicativo AGV GO e parceiro EDI) em informação confiável, indicadores e alertas de operação. **Os dados da AGV são fictícios.**

## Progresso

- [x] Etapa 1 — Diagnóstico de qualidade de dados
- [x] Etapa 2 — Normalização, auditoria e consolidação por pedido
- [x] Etapa 3 — Cálculo de SLA, OTD e desempenho por transportadora
- [x] Etapa 4 — Classificação de ocorrências e alertas simulados
- [x] Etapa 5 — Dashboard web interativo
- [x] Etapa 6 — Validação de entrada, staging, testes e documentação técnica
- [x] Etapa 11 — Histórico responsivo e filtros em barras nativas, sem seleção Plotly
- [ ] Revisão visual final no navegador, vídeo e entrega do candidato

## Instalação

Requer Python 3.10 ou superior. Na pasta raiz deste projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

> Se o PowerShell bloquear a ativação, use `.\.venv\Scripts\python.exe` no lugar de `python`.

## Como executar

**Uma única execução produz todos os relatórios a partir dos três CSVs originais, sem depender de resultados anteriores:**

```powershell
python -m src.main
```

Execute os testes automatizados:

```powershell
python -m unittest discover -s tests -v
```

Também é possível executar os módulos separadamente:

```powershell
python src/diagnostico.py
python -m src.rastreamento
python -m src.sla
python -m src.ocorrencias
```

## Fluxo de dados

```text
CSV: pedidos + eventos_rastreio + dicionario_codigos
     |
     +--> diagnostico.py --> qualidade e inconsistencias detectadas
     |
     +--> rastreamento.py --> normalizacao / auditoria / consolidacao
                                    |
                                    +--> sla.py --> prazos / OTD / indicadores
                                    |
                                    +--> ocorrencias.py --> categorias / alertas
                                                        |
                                                        +--> arquivos CSV / TXT / MD
```

**A entrada nunca é sobrescrita:** os dados são lidos de `dados/` e todas as saídas são escritas em `output/`.

## Arquivos de entrada

- `dados/pedidos.csv`: 60 pedidos, clientes, coletas, prazos, transportadoras e NF;
- `dados/eventos_rastreio.csv`: 232 eventos com código, data, origem e observação;
- `dados/dicionario_codigos.csv`: códigos oficiais `COL`, `TRF`, `ROT`, `OCO`, `ENT` e ordem de referência.

A data de referência **obrigatória para este exercício** é **24/09/2026 às 18h00**; a automação **não consulta o relógio atual** para avaliar SLA.

## Principais saídas

| Arquivo em `output/` | Finalidade |
|---|---|
| `diagnostico_qualidade.csv` | Cada inconsistência com tratamento proposto |
| `resumo_diagnostico.md` | Contagens de qualidade |
| `auditoria_eventos.csv` | Todas as 232 linhas originais com decisão e motivo |
| `eventos_validos.csv` | Apenas eventos aprovados na validação |
| `pedidos_consolidados.csv` | Uma linha por pedido, status e último evento válido |
| `pedidos_sla.csv` | Prazo, situação e horas restantes por pedido |
| `indicadores_gerais.csv` | Métricas consolidadas e OTD geral |
| `otd_transportadoras.csv` | Pontualidade por transportadora |
| `contagem_situacoes.csv` | Distribuição das cinco situações de prazo |
| `ocorrencias_classificadas.csv` | Eventos OCO e categorias identificadas |
| `frequencia_categorias.csv` | Quantidade por categoria de ocorrência |
| `alertas_operacionais.csv` | Pedidos em aberto atrasados ou em risco com ações sugeridas |
| `alerta_operacional.txt` | Mensagem operacional **simulada**, sem envio externo |
| `resumo_ocorrencias_alertas.md` | Detalhes da etapa 4 e limitações |
| `manifesto_execucao.json` | Data de execução, métricas, hashes de entrada e mudanças frente ao processamento anterior |

## Premissas adotadas e regras de negócio

1. **Normalização:** códigos com letras minúsculas e `ENTREGUE` são padronizados para os códigos oficiais, preservando a origem na auditoria.
2. **Datas:** aceitamos `AAAA-MM-DD HH:MM:SS` e `DD/MM/AAAA HH:MM`. Uma data ausente/inválida não deve determinar a situação temporal do pedido.
3. **Deduplicação:** a chave lógica considera pedido, código, timestamp, fonte e observação normalizados. Em repetições equivalentes, preserva-se o menor ID.
4. **Quarentena:** eventos sem pedido, sem data, anteriores à coleta, posteriores à referência, desconhecidos ou duplicados são mantidos na auditoria, mas não atualizam a visão operacional.
5. **Status:** último evento válido por timestamp; em empate, código oficial e ID definem ordem determinística. `ENT` é considerado terminal; a primeira entrega válida define a data de entrega.
6. **Pedido sem eventos:** deve continuar na base como `SEM_RASTREIO`.
7. **Dias úteis:** segunda a sexta, **sem feriados**, a partir da coleta; o horário da coleta é preservado na data-limite. O dia da coleta não conta para somar os dias úteis.
8. **SLA:** entrega até o instante do vencimento é pontual. Pedido em aberto após o vencimento está atrasado. Se o vencimento ocorrer entre a referência e as 24h seguintes (inclusive), está em risco.
9. **OTD:** entregas pontuais divididas pelas entregas válidas realizadas. Pedidos em aberto não entram no denominador.
10. **Ocorrências:** classificação por palavras-chave transparentes e determinísticas, sem API de LLM. Uma OCO pode ter mais de uma categoria; a primeira regra na ordem definida no código estabelece a categoria principal.
11. **Alertas:** somente pedidos em aberto atrasados ou com vencimento nas próximas 24h. Ações são *sugestões*, não tarefas já executadas. Nenhum envio real foi realizado.

## Resultado com a amostra fictícia

- 60 pedidos mantidos; 225 eventos validados e 7 em quarentena (4 duplicados, 1 órfão, 1 sem data e 1 anterior à coleta).
- Status: 48 `ENT`, 7 `TRF`, 3 `OCO` e 2 `SEM_RASTREIO`.
- OTD geral **81,25%** (39 pontuais / 48 entregues).
- SLA: 39 entregues no prazo; 9 entregues atrasados; 5 atrasados em aberto; 3 em risco; 4 no prazo em aberto.
- OTD por transportadora: PARCEIRO_C 95,24%; TRANSP_A 72,22%; TRANSP_B 66,67%.
- 10 ocorrências OCO classificadas; o rótulo duplo `AVARIA|RECUSA` conta uma vez em cada categoria no relatório de frequência.
- 8 alertas simulados: 5 atrasados em aberto e 3 em risco.

## Perguntas que faria ao negócio

- O SLA usa feriados da origem, do destino, da transportadora ou um calendário corporativo?
- O prazo vence no mesmo horário da coleta ou no final do dia útil?
- Como tratar reentregas, recusa parcial, devolução e eventos `ENT` que depois são retificados?
- A data de entrega válida é a primeira confirmação `ENT` ou exige validação por comprovante?
- OTD deve considerar apenas pedidos concluídos, todos os pedidos com prazo vencido, ou ambos como indicadores distintos?
- Ocorrências registradas em pedidos já entregues exigem atendimento adicional?
- Qual o canal e responsável por cada alerta, a frequência de atualização e o critério de escalonamento?

## Limitações e caminhos para produção

- As regras de qualidade, SLA e ações precisam de validação com a área de negócio antes de uso real.
- A deduplicação atual não elimina variantes semânticas distintas do mesmo evento.
- A classificação por palavras-chave pode falhar diante de sinônimos não mapeados; avaliar exemplos reais, métricas e, se necessário, classificador supervisionado ou LLM com revisão humana.
- O processamento é **batch local**, sem conexão com TMS, AGV GO, EDI ou serviços externos. Uma evolução real incluiria APIs/webhooks, execução agendada, logs, reprocessamento idempotente, permissões/LGPD, monitoramento e entrega confiável dos alertas.
- O dashboard web já está implementado como camada de consulta local; o pipeline continua independente dele.
- O envio de e-mail, Teams ou WhatsApp **não é realizado**; existe somente um arquivo de texto com a mensagem simulada.

## Testes

Na Etapa 11 executamos **77 testes** de regressão cobrindo normalização, perda zero de pedidos, quarentena auditável, deduplicação, limites do SLA, OTD, categorias múltiplas, tratamento de textos acentuados e alertas simulados. O comando acima reproduz esses testes localmente.

## Uso de IA

Foi utilizado ChatGPT (OpenAI) para discutir premissas, propor a arquitetura, auxiliar na implementação em Python, formular casos de teste e revisar avisos de compatibilidade. A revisão do candidato e a execução local são parte da validação. Um registro resumido do apoio está em [`USO_DE_IA.md`](USO_DE_IA.md).

---

## Etapa 5 — Dashboard web (Streamlit)

Uma interface **local e interativa** foi acrescentada ao pipeline, sem alterar as regras
já testadas. O painel usa os arquivos gerados em `output/` e mostra seis áreas:
Visão geral, Rastreamento, Transportadoras, Ocorrências, Qualidade e Alertas.

### Como abrir no navegador (Windows / PowerShell)

Na raiz `agv_tracking_intelligence`, com o ambiente virtual ativado:

```powershell
python -m pip install -r requirements.txt
python -m src.main
python -m streamlit run app.py
```

O Streamlit abre a aplicação automaticamente ou informa o endereço
**http://localhost:8501**. Para encerrar, pressione `Ctrl+C` no terminal.

Se tiver mais de um projeto Streamlit aberto, o número da porta pode mudar.

**Botão “Atualizar dados”:** valida e reexecuta o pipeline a partir de `dados/*.csv`,
recriando saídas, SLA, classificação e alertas numa pasta temporária; somente
após a validação final publica os resultados e mostra o resumo. Para demonstrar no processo
seletivo, mostre os dados de origem, aperte o botão e confira o resultado.

**Filtros:** a seleção de transportadora na barra lateral limita o escopo de
visualização. Os KPIs e gráficos de OTD são recalculados a partir dos pedidos
filtrados, em vez de exibir percentuais globais incongruentes.

**Mapa:** o recurso `assets/mapa_brasil_ilustrativo.svg` é decorativo, com
geometria simplificada do Brasil proveniente de dados de domínio público
Natural Earth; as linhas e pontos são **fictícios e não representam rastreio
geográfico, itinerários reais ou integrações com GPS**. Os arquivos recebidos
não fornecem localização da origem, posição do veículo ou rotas efetivas.

**Identidade visual:** protótipo inspirado na paleta verde da AGV; não é um
sistema institucional oficial nem utiliza integração com dados reais. Os dados
são os fictícios fornecidos no desafio.

### Limitações da interface

- O dashboard é local por padrão; não está publicado na internet.
- A data de referência do desafio permanece **24/09/2026 às 18h00**; não é um
  serviço de monitoramento em tempo real.
- Alertas são gerados em arquivo e exibidos na tela; nenhuma mensagem externa
  é transmitida.
- É necessário instalar Streamlit, Plotly, `streamlit-option-menu` e AG Grid via `requirements.txt`.
- A personalização CSS e o AG Grid são componentes visuais; realizar conferência
  final no navegador local e ajustar eventuais diferenças de versão.

### Revisão

Execute `python -m unittest discover -s tests -v` para validar o pipeline e as
funções de filtros/indicadores do dashboard. Para entrega final, confira
manualmente a interface no navegador e tire capturas com filtros diferentes.


### Interações na interface (Etapa 7)

- Clique em uma barra de **OTD por transportadora** na Visão geral ou em Transportadoras para filtrar os indicadores, pedidos, ocorrências e alertas para a transportadora selecionada.
- O gráfico comparativo mantém todas as transportadoras para permitir a troca do recorte sem limpar o filtro antes.
- O seletor lateral fica sincronizado com a barra clicada; use **Limpar filtro** ou selecione **Todas** para voltar ao conjunto completo.
- A visão Qualidade acompanha o filtro quando aplicado. Registros órfãos, cuja transportadora não é identificável, aparecem apenas com **Todas** selecionado.
- Na Etapa 11, os filtros das barras foram convertidos em botões nativos do Streamlit para evitar falhas do `st.plotly_chart(on_select=...)` após rolagem. O gráfico de rosca continua em Plotly, mas é apenas visual, sem captura de clique.


### Etapa 8 — Exploração por clique (Rastreamento e Ocorrências)

**Rastreamento**

- Na parte superior, utilize uma única busca por ID do pedido, cliente ou cidade;
  os filtros de SLA e status logístico exibem placeholders em português.
- Clique **em qualquer célula de uma linha** na tabela para carregar os dados
  e o histórico em “Detalhes e histórico de eventos” — não há seletor de pedido
  redundante na parte inferior.
- Antes do primeiro clique, a área de detalhes exibe uma instrução.
- O pedido selecionado fica salvo ao trocar de página. Se a nova busca, status,
  situação de SLA ou transportadora excluí-lo do recorte, o painel limpa o detalhe
  em vez de mostrar informação fora dos filtros.
- Observações ausentes aparecem como `—` apenas na visualização, preservando
  os arquivos de origem e os dados exportados.

**Ocorrências**

- Clique em uma barra de categoria no gráfico **Tipos de ocorrência** para ver
  somente as linhas daquela categoria na tabela; a seleção é visualmente
  destacada, com um botão **Limpar categoria**.
- As barras permanecem visíveis no escopo da transportadora ativa para facilitar
  a troca de categoria. Mudar a transportadora limpa a categoria anterior.
- O filtro considera *todas* as categorias de uma ocorrência. Assim,
  `PED1012` aparece tanto em `AVARIA` quanto em `RECUSA`.
- O botão de exportação baixa somente as ocorrências atualmente exibidas.

**Teste manual sugerido:** abra o Rastreamento, busque `PED1012` e clique na
linha; confirme o histórico. Depois teste com `PED1008`, que não tem rastreio.
Na aba Ocorrências, clique em `RECUSA`, confirme que `PED1012` aparece, e
pressione **Limpar categoria**. O teste automatizado de regressão totaliza
**55 casos** na Etapa 8 (histórico de desenvolvimento).

Na versão atual, o Rastreamento utiliza **AG Grid** para selecionar linhas;
as barras de OTD e ocorrências agora usam botões nativos com proporção visual no CSS. A seleção
visual precisa ser verificada no navegador onde o aplicativo estiver instalado.

## Ajustes de interface — Etapa 9 (histórico; seleção substituída na Etapa 10)

- Rastreamento: clique diretamente **em qualquer célula da linha de um pedido** para carregar detalhes e histórico. A seleção usa `single-cell` do `st.dataframe` para dispensar a coluna de checkbox de linha.
- Se aplicar uma busca ou um filtro que exclui o pedido selecionado, o detalhe é limpo automaticamente.
- O cabeçalho superior não repete mais `AGV TECHLAB / TRACKING INTELLIGENCE` nem `TORRE DE CONTROLE / TECHLAB`; a identidade já está na sidebar.
- Na Etapa 9 não foram adicionadas bibliotecas; a Etapa 10 substituiu esse recurso pela dependência `streamlit-aggrid`.


## Etapa 10 — Robustez, reprocessamento seguro e seleção sem efeito flutuante

### Validação estrutural (`src/validacao.py`)

Antes de processar, são verificados: presença e cabeçalhos obrigatórios dos três CSVs,
IDs únicos e não vazios dos pedidos, campos críticos preenchidos, datas de coleta
interpretáveis, prazos inteiros não negativos e códigos/ordens do dicionário válidos.
Mensagens de erro citam o arquivo, campo e exemplos de linhas problemáticas.

**Não se deve rejeitar a entrada por causa de inconsistências de rastreio**
que o exercício exige identificar: eventos com data inválida, duplicados lógicos,
associados a pedido inexistente, sem código reconhecido ou anteriores à coleta
continuam registrados e auditados no pipeline.

### Publicação protegida (`src/main.py`)

`python -m src.main`:

1. Valida os três arquivos de origem sem alterar seu conteúdo.
2. Executa os quatro módulos numa pasta temporária ao lado de `output/`.
3. Confere número de pedidos, cobertura de SLA, integridade da auditoria e alertas.
4. Salva `manifesto_execucao.json` (hora real do processamento, contagens, SHA-256
   de origem, e diferenças em relação ao manifesto anterior).
5. Publica a pasta de resultados por renomeação de diretórios e desfaz a
   substituição se a publicação falhar. Em falhas anteriores à publicação,
   mantém integralmente o último `output/`.

É uma **publicação recuperável para um protótipo local**, não uma transação
de banco de dados: não implementa locks interprocessos nem leitura simultânea
de versões. Em produção, seriam necessárias publicação versionada/atômica com
ponteiro de versão, controle de concorrência e orquestração externa.

Na primeira execução com manifesto, o sistema estabelece uma linha de base;
a partir da segunda, informa novos/removidos pedidos e novos eventos. Os números
no manifesto descrevem a execução real, enquanto **o SLA permanece ancorado
em 24/09/2026 às 18h**.

### Tabela de rastreamento — AG Grid

O seletor de células nativo causou deslocamento do destaque ao rolar
a grade, observado em vídeo durante os testes locais. A tela de Rastreamento
agora usa a biblioteca `streamlit-aggrid` com **seleção da linha toda via clique**,
**sem checkboxes**, e identifica o pedido pelo seu ID (não pelo índice visual).
O grid possui ordenação e paginação, e o histórico abaixo mantém o comportamento
anterior, respeitando os filtros. Instale as dependências com:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

### Como testar uma atualização com um pedido novo

1. Faça uma cópia de `dados/pedidos.csv`.
2. Adicione um pedido com ID **novo**, campos obrigatórios válidos, coleta
   dentro do período do exercício e prazo não negativo.
3. Clique **Atualizar dados**: o total deve subir, e sem evento relacionado
   o novo pedido ficará como `SEM_RASTREIO`.
4. Clique novamente: o resumo não deve indicar outro novo pedido.
5. Restaure a cópia original para a entrega.

**Testes da Etapa 10:** `python -m unittest discover -s tests -v`. Naquela etapa eram **71 testes**:
59 de regressão e 12 novos testes cobrindo entradas alteradas, falhas simuladas,
reprocessamento, preservação de relatórios e interpretação de seleção por ID.
Além dos testes automatizados, o efeito visual do AG Grid precisa ser conferido
no navegador do candidato; o componente não pôde ser instalado neste ambiente.

**Cuidados:** a demonstração usa dados fictícios e não deve ser apresentada
como monitoramento em tempo real ou como sistema oficial da AGV.


## Etapa 11 — Usabilidade, responsividade e cliques após rolagem

Motivação: testes em vídeo mostraram que o gráfico de ocorrências nem sempre
registrava um clique, especialmente após rolar a página. Não há prova de que
a causa tenha sido o CSS ou um overlay; a correção troca a dependência dos
eventos de seleção de pontos do Plotly por barras visuais construídas sobre
**botões nativos do Streamlit** nas telas OTD e Ocorrências. O comportamento
é determinístico: um clique aplica o recorte, outro clique na mesma barra
remove o filtro; as demais barras continuam disponíveis. Os dados, OTD e
classificações **não foram alterados**. A rosca de SLA continua sendo Plotly,
sem seleção interativa.

Na tela **Rastreamento**, o histórico de eventos é renderizado como tabela HTML
semântica com observações completas e quebra automática de linhas, por
`src/ui_helpers.py`. Cada campo é escapado contra HTML não confiável e os
valores vazios aparecem como `—`. Em celulares (até 640 px), cada evento
vira um cartão com rótulos; em tablets, os painéis passam a empilhar, com KPIs
adaptados a duas colunas quando houver espaço. Tabelas largas de outras telas
continuam com rolagem horizontal local. A navegação usa a sidebar recolhível
do próprio Streamlit.

**Validação realizada:** 77 testes Python aprovados, pipeline reprocessado
com os totais oficiais da amostra, verificação isolada de quebra de texto
em Chromium com CSS em 1440/1024/768/430/375 px (sem transbordo da página).
A verificação da aplicação Streamlit completa e dos cliques em navegador
local ainda é necessária.

**Roteiro manual de aceite (Etapa 11):**

1. Em Ocorrências, clique `RECUSA`, role para cima e para baixo e clique
   novamente; o filtro deve entrar e sair consistentemente. Depois clique
   em `AVARIA`, incluindo o pedido `PED1012` na categoria.
2. Na Visão geral, clique `TRANSP_A` e confira OTD do recorte de 72,22%;
   clique na mesma barra para remover. Navegue para outras páginas e volte.
3. Em Rastreamento, selecione `PED1012`, confirme que a observação de avaria
   e recusa é exibida integralmente sem truncamento.
4. Teste o menu, filtros, botões e histórico em desktop, tablet (~768 px) e
   celular (~390 px) usando o modo responsivo das Ferramentas do Desenvolvedor.
5. Execute `python -m unittest discover -s tests -v` e clique em **Atualizar
   dados** para confirmar que as contagens e o manifesto permanecem consistentes.


### Etapa 12 — tabelas estáveis e teste visual do título (85 testes)

- As tabelas **somente de consulta** de Transportadoras, Ocorrências, Qualidade, Alertas e auditoria de um pedido agora usam HTML semântico e rolagem local: não abrem o componente de seleção/edição de célula que gerava a caixa flutuante após duplo clique.
- O **Rastreamento** continua usando AG Grid com clique de linha e carregamento do histórico; não foi substituído.
- As tabelas de consulta preservam os filtros existentes e os arquivos exportados, mas **não oferecem mais a ordenação por clique no cabeçalho**. Os dados seguem a ordenação produzida em Python. Em produção, pode-se adicionar ordenação explícita se necessário.
- O título *Tracking Intelligence* na **Visão geral** recebeu uma animação de brilho verde-lima inspirada na referência enviada; as demais páginas mantêm títulos estáticos. A preferência de movimento reduzido do dispositivo desativa essa animação.
- O ícone da guia do navegador utiliza `assets/somosagvbrasil_logo.jpg` (imagem fornecida para o protótipo). A marca não implica produto oficial da AGV.
- **Validação visual necessária:** testar o duplo clique, rolagem e filtros de cada tela no navegador local; os testes automatizados conferem a geração e os dados, mas não reproduzem integralmente o navegador Streamlit.

**Conferência da Etapa 12:** 85 testes automatizados aprovados; tabelas HTML inspecionadas isoladamente no Chromium em 1440, 1024, 768, 430 e 375 px, com rolagem horizontal restrita à tabela nas telas pequenas. O navegador Streamlit completo ainda deve ser validado localmente.

### Ajuste de acabamento — Etapa 12b (botões de exportação)

- Incluído espaçamento visual adicional de 16 px entre as tabelas e os botões de exportação nas páginas **Ocorrências**, **Qualidade** (auditoria completa) e **Alertas** (alertas do recorte). Em telas pequenas, o respiro é de 12 px.
- Não foram alteradas as regras de processamento, o cálculo de indicadores, os dados ou o botão **Baixar mensagem simulada**.
- Validação de regressão: 85 testes automatizados aprovados; espaçamento final sujeito à conferência visual no Streamlit local.


### Ajuste visual — Etapa 13d

O gráfico **Composição das entregas** na página Transportadoras apresenta valores dentro das barras e uma legenda visível no canto inferior direito (verde-lima = **No prazo**; laranja = **Com atraso**). A rotina de tema desliga legendas por padrão; a legenda desse gráfico foi refinada novamente na Etapa 14c, com uma anotação interna ao Plotly, sem a moldura do componente nativo.


### Atualização visual — Etapa 14

- A navegação entre as seis páginas ganhou uma transição circular CSS de cerca de 0,6 segundo, inspirada em efeitos de troca de tema. A animação é disparada apenas quando o destino do menu muda, não quando filtros são recalculados. A preferência do sistema por movimento reduzido é respeitada.
- A legenda do gráfico **Composição das entregas** continua posicionada à direita, abaixo da área plotada, agora **sem caixa, borda ou fundo próprios**.
- O efeito implementado é uma adaptação visual (o Reel de referência não pôde ser reproduzido para uma comparação exata).

**Validação da Etapa 14:** 88 testes automatizados passaram, incluindo verificação de legenda sem moldura e de estados de página no código. Os efeitos no navegador precisam ser avaliados ao alternar o menu do Streamlit.


### Correção de legenda — Etapa 14c

- **Composição das entregas:** uma única legenda embutida no rodapé interno da figura Plotly, alinhada à direita, sem borda ou contêiner adicional. Ordem: **No prazo** (verde-lima), depois **Com atraso** (laranja).
- Desativadas tanto a legenda nativa quanto a legenda HTML externa; o mesmo HTML havia sido inserido por engano também no gráfico **Situação dos pedidos**, e foi removido.
- Valores numéricos dentro das barras e a transição de páginas foram preservados.
- Um teste de regressão verifica que há somente uma anotação de legenda, que ela não tem moldura e que não há mais HTML duplicado. Uma renderização isolada em Chromium confirmou a presença de uma legenda no rodapé e a ausência da legenda nativa; conferir no Streamlit local.
