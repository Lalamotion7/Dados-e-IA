# Etapa 4 — Ocorrencias e alertas (AGV TechLab)

- Data de referencia: 24/09/2026 18:00
- Eventos OCO validos classificados: 10
- Classificador: palavras-chave deterministicas, sem APIs ou LLM; multirrotulo possivel.
- Uma observacao pode entrar em mais de uma categoria; totais por categoria podem superar o numero de OCOs.
- OCOs em pedidos ja entregues entram no historico, mas nao geram alertas de SLA.
- Pedidos que exigem acao: 8
- Atrasados em aberto: 5
- Em risco: 3

## Frequencia de categorias

- AVARIA: 6
- RECUSA: 2
- ACESSO_IMPEDIDO: 1
- AUSENCIA: 1
- ENDERECO: 1

## Limites e decisoes pendentes

- As regras usam palavras-chave; sinonimos nao previstos podem ser classificados como OUTROS.
- Acoes sugeridas sao orientacoes, nao confirmacao de contato ou reentrega.
- Os oito alertas cobrem somente pedidos abertos atrasados ou em risco nas 24h da referencia.
- Uma ocorrencia historica nao prova que ainda esta pendente; sua presenca deve ser validada.
- Confirmar com a operacao criterios de prioridade e prazos de SLA.
