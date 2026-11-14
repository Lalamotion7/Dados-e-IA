# Registro de uso de IA — Desafio AGV TechLab

**Ferramenta:** ChatGPT (OpenAI).

**Onde foi usada:** interpretação do enunciado; identificação de problemas de qualidade; desenho do fluxo; sugestões de scripts Python/Pandas; lógica de SLA e OTD; classificação de ocorrências; geração de alertas simulados; criação e revisão de testes e documentação.

## Pedidos relevantes (síntese das conversas)

1. "Analise o enunciado do desafio e os três CSVs. Proponha uma solução viável para Analista Júnior de Hiperautomação, contemplando diagnóstico, SLA, OTD, qualidade, classificação de OCO e alertas."
2. "Inicie pela leitura dos arquivos e pelo diagnóstico de qualidade, preservando entradas e explicando inconsistências."
3. "Crie a etapa de normalização, trilha de auditoria, consolidação por pedido e testes automatizados."
4. "Implemente as situações de SLA, cálculo de dias úteis e OTD geral e por transportadora; teste as fronteiras de prazo."
5. "Explique os avisos de depreciação e construa classificação de ocorrências por regras com alertas simulados, mantendo a execução reproduzível."

As frases acima **resumem os pedidos**, não pretendem representar uma transcrição literal de cada mensagem.

## Decisões técnicas validadas na construção

- Priorizar Pandas e arquivos locais em vez de nuvem/LLMs sem necessidade, pelo volume de 60 pedidos e 232 eventos.
- Manter todos os pedidos, mesmo sem rastreamento.
- Isolar eventos inválidos na auditoria em vez de excluí-los sem registro.
- Utilizar regras explícitas para dias úteis, OTD e classificação de textos; documentar dúvidas ao negócio.
- Tratar a hora de referência como fixa (24/09/2026 18:00).
- Não enviar alertas reais; gerar uma prévia como exigido pelo desafio.
- Adicionar testes automatizados para que a saída seja reproduzível em uma nova execução.

## Validação e responsabilidade

Os programas e relatórios podem ser reproduzidos com `python -m src.main` e os testes com `python -m unittest discover -s tests -v`. Como em qualquer código assistido por IA, é necessária revisão das premissas, dos resultados e das implicações de uso antes da entrega e de uma eventual implementação real.

A descrição final do processo de revisão e de eventuais alterações feitas pelo candidato deve ser complementada antes do envio à AGV.

## Etapa 5 — Interface gráfica

O ChatGPT também auxiliou na proposta visual do dashboard Streamlit em estilo
*glassmorphism*, no desenho de um mapa exclusivamente ilustrativo, na criação
de páginas e filtros operacionais, nos gráficos Plotly e na redação de testes
de consistência dos KPIs. Pedido relevante: "Desenvolva a versão local,
interativa, do dashboard AGV com identidade verde-petróleo e verde-lima,
preservando o pipeline e distinguindo mapas decorativos de rotas reais".

**Validação pendente pelo candidato:** navegar pelas seis telas no próprio
computador e registrar eventuais correções de layout ou usabilidade antes
da entrega. A interface não recebeu validação visual em navegador neste ambiente
de desenvolvimento.

## Etapas 6 e 7 — Identidade visual e seleção cruzada

O ChatGPT auxiliou na integração do SVG de marca fornecido pelo candidato, no refinamento do menu, na melhoria dos ícones dos KPIs e na implementação de seleção cruzada do OTD por transportadora. Foram discutidas a sincronização do gráfico Plotly com o filtro lateral do Streamlit, a preservação do contexto comparativo e a cobertura por testes de validação.

Pedido relevante: "Deixe a logo à esquerda, retire o fundo do menu e torne as barras de OTD clicáveis, filtrando os demais indicadores como em ferramentas de BI".

**Validação visual e de clique:** deverá ser realizada pelo candidato no navegador local. A lógica dos filtros foi coberta por testes de unidade, mas não houve automação de navegador neste ambiente.


## Etapa 8 — Detalhes por pedido e categorias clicáveis

O ChatGPT auxiliou a atualizar a tabela de rastreamento para seleção de linhas,
a remover o seletor redundante, a traduzir placeholders e a implementar filtros
por clique nas barras das categorias de ocorrência. Também auxiliou na
persistência/limpeza contextual das seleções e em testes de regressão para o
rótulo múltiplo `AVARIA|RECUSA`.

Pedido relevante (síntese): "Faça a tabela de rastreamento abrir os detalhes
quando eu clicar no pedido; mantenha só a busca superior, traduza Choose options
e torne as barras de ocorrências filtros, eliminando o seletor inferior".

Foi usada a documentação pública do Streamlit para conferir as interfaces de
seleção em `st.dataframe` e `st.plotly_chart`. Não foram adicionados novos
serviços externos nem processamento por IA no fluxo de dados.

### Etapa 9 — revisão com assistência de IA

Pedido: remover checkbox de seleção na tabela de rastreamento em favor do clique em célula/linha e eliminar títulos repetidos do topo. O ChatGPT auxiliou na alteração da interface, na adaptação da leitura do evento `cells` e em testes unitários. A seleção visual deve ser conferida localmente no navegador.


## Etapa 10 — Revisão de confiabilidade e usabilidade

Pedido do candidato (síntese): avaliar a automação como uma entrega técnica,
validar os arquivos antes do pipeline, impedir relatórios parcialmente
atualizados, informar o que mudou na atualização, testar arquivos modificados
e corrigir uma seleção visual de célula que se deslocava ao rolar a tabela
(teste enviado em vídeo).

O ChatGPT auxiliou no desenvolvimento do validador estrutural, no staging de
resultados, na lógica de publicação com restauração, no manifesto de execução,
no resumo visual e nos novos testes. Também sugeriu substituir o componente
de seleção de células por um grid de linha clicável (`streamlit-aggrid`) e
consultou documentação pública do AG Grid para conferir os parâmetros de
seleção sem checkbox.

Os dados fictícios e a data fixa de referência foram preservados. A bateria
de **71 testes automatizados** foi executada neste ambiente. A instalação do
componente AG Grid e a verificação visual em navegador **não** foram executadas
neste ambiente e permanecem a cargo do candidato.


## Etapa 11 — Correções de interação e apresentação responsiva

Pedido do candidato (síntese): "Faça observações longas caberem no histórico,
adapte o dashboard a tablet e celular e corrija o clique inconsistente em
gráficos após a rolagem, observado em vídeo".

O ChatGPT auxiliou a substituir a seleção de pontos do Plotly por barras
baseadas em botões nativos do Streamlit, mantendo o cross-filtering; a criar
um histórico HTML escapado com quebra de texto e cards responsivos; a revisar
CSS e a escrever testes unitários e uma verificação isolada da apresentação
HTML em múltiplas larguras de tela. A causa específica do comportamento do
Plotly não foi comprovada.

O pipeline e as métricas de negócio não foram alterados. Nesta etapa,
**77 testes Python** passaram e a tabela de histórico foi inspecionada no
Chromium em tamanhos de desktop e celular. A interação do aplicativo Streamlit
completo ainda precisa de teste local pelo candidato.


### Etapa 12
Assistência do ChatGPT para revisar vídeos de problemas de seleção/célula, substituir tabelas de consulta por HTML estático escapado, aplicar uma animação CSS apenas ao título da Visão geral e criar testes de segurança e apresentação. As mudanças devem ser conferidas visualmente no navegador pelo candidato.


### Etapa 14 — Refinamento de transições (13/11/2026)
O ChatGPT auxiliou na implementação de uma revelação circular CSS para a transição entre as páginas do Streamlit, usando uma revisão de chave de contêiner que só muda ao trocar de página, e na remoção da caixa visual da legenda Plotly. O vídeo de referência do Instagram não estava acessível para inspeção exata; o efeito foi aproximado conforme a descrição do candidato. Foram criados testes de regressão e a apresentação final continua sujeita à validação no navegador.


### Revisão de legenda (Etapa 14c)

O ChatGPT auxiliou na correção de uma duplicidade da legenda do gráfico de composição de entregas. Foi substituída a legenda HTML fora da figura por uma anotação única dentro do Plotly, com ordem e cores explícitas, e removida uma inclusão indevida no gráfico de situações. O candidato deve validar a renderização na aplicação local.
