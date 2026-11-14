"""Etapa 1 do desafio AGV: leitura e diagnostico da qualidade dos CSVs.

Uso: python src/diagnostico.py
Este script NAO altera os arquivos originais.
"""
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / 'dados'
SAIDAS = RAIZ / 'output'
REFERENCIA = pd.Timestamp('2026-09-24 18:00:00')


def converter_datas(coluna: pd.Series) -> pd.Series:
    """Aceita timestamps ISO e no formato brasileiro DD/MM/AAAA HH:MM."""
    texto = coluna.astype('string').str.strip()
    iso = pd.to_datetime(texto, format='%Y-%m-%d %H:%M:%S', errors='coerce')
    brasileiro = pd.to_datetime(texto, format='%d/%m/%Y %H:%M', errors='coerce')
    return iso.fillna(brasileiro)


def analisar(dados_dir: Path = DADOS, saidas_dir: Path = SAIDAS) -> pd.DataFrame:
    dados_dir, saidas_dir = Path(dados_dir), Path(saidas_dir)
    saidas_dir.mkdir(parents=True, exist_ok=True)
    pedidos = pd.read_csv(dados_dir / 'pedidos.csv', sep=';', encoding='utf-8-sig', dtype=str)
    eventos = pd.read_csv(dados_dir / 'eventos_rastreio.csv', sep=';', encoding='utf-8-sig', dtype=str)
    dicionario = pd.read_csv(dados_dir / 'dicionario_codigos.csv', sep=';', encoding='utf-8-sig', dtype=str)

    eventos['codigo_normalizado'] = (
        eventos['codigo_evento'].str.strip().str.upper().replace({'ENTREGUE': 'ENT'})
    )
    eventos['data_convertida'] = converter_datas(eventos['data_hora'])
    pedidos['coleta_convertida'] = converter_datas(pedidos['data_coleta'])

    registros = []

    def registrar(problema: str, linhas: pd.DataFrame, tratamento: str, valor_coluna: str = ''):
        for _, r in linhas.iterrows():
            registros.append({
                'problema': problema,
                'tipo_registro': 'pedido' if 'id_evento' not in linhas.columns else 'evento',
                'id_pedido': r.get('id_pedido', ''),
                'id_evento': r.get('id_evento', ''),
                'valor_original': r.get(valor_coluna, '') if valor_coluna else '',
                'tratamento_proposto': tratamento,
            })

    codigos_validos = set(dicionario['codigo'].str.strip().str.upper())
    codigos_alterados = eventos[eventos['codigo_evento'] != eventos['codigo_normalizado']]
    registrar('codigo_nao_padronizado', codigos_alterados, 'Normalizar maiusculas e mapear ENTREGUE para ENT', 'codigo_evento')

    codigos_desconhecidos = eventos[~eventos['codigo_normalizado'].isin(codigos_validos)]
    registrar('codigo_desconhecido', codigos_desconhecidos, 'Revisar com o negocio; nao presumir novo status', 'codigo_evento')

    formatos_br = eventos[eventos['data_hora'].fillna('').str.match(r'^\d{2}/\d{2}/\d{4}')]
    registrar('data_formato_brasileiro', formatos_br, 'Converter para timestamp padrao ISO', 'data_hora')

    datas_invalidas = eventos[eventos['data_convertida'].isna()]
    registrar('data_hora_ausente_ou_invalida', datas_invalidas, 'Retirar do ordenamento temporal e reportar', 'data_hora')

    # Duplicatas LOGICAS podem possuir IDs diferentes; preservamos o menor ID.
    eventos_ordenados = eventos.assign(
        id_evento_numerico=pd.to_numeric(eventos['id_evento'], errors='coerce'),
        observacao_chave=eventos['observacao'].fillna('').str.strip().str.lower(),
        fonte_chave=eventos['fonte'].fillna('').str.strip().str.upper(),
    ).sort_values('id_evento_numerico', kind='stable')
    chave = ['id_pedido', 'codigo_normalizado', 'data_convertida', 'fonte_chave', 'observacao_chave']
    duplicados = eventos_ordenados[eventos_ordenados.duplicated(subset=chave, keep='first')]
    registrar('evento_duplicado', duplicados, 'Preservar o evento de menor ID e isolar as repeticoes')

    orfaos = eventos[~eventos['id_pedido'].isin(pedidos['id_pedido'])]
    registrar('evento_sem_pedido', orfaos, 'Colocar em quarentena sem inventar pedido')

    sem_eventos = pedidos[~pedidos['id_pedido'].isin(eventos['id_pedido'])]
    registrar('pedido_sem_eventos', sem_eventos, 'Manter o pedido na consolidacao e sinalizar ausencia')

    datas_coleta = pedidos[['id_pedido', 'coleta_convertida']]
    linha_tempo = eventos.merge(datas_coleta, on='id_pedido', how='left')
    anteriores = linha_tempo[linha_tempo['data_convertida'] < linha_tempo['coleta_convertida']]
    registrar('evento_anterior_coleta', anteriores, 'Desconsiderar como evidência valida de status/SLA; registrar anomalia', 'data_hora')

    futuros = eventos[eventos['data_convertida'] > REFERENCIA]
    registrar('evento_posterior_referencia', futuros, 'Excluir do estado na data de referencia; conservar para auditoria', 'data_hora')

    relatorio = pd.DataFrame(registros, columns=[
        'problema','tipo_registro','id_pedido','id_evento','valor_original','tratamento_proposto'
    ])
    relatorio.to_csv(saidas_dir / 'diagnostico_qualidade.csv', sep=';', index=False, encoding='utf-8-sig')

    contagens = relatorio['problema'].value_counts().sort_index()
    linhas = [
        '# Diagnostico inicial — AGV TechLab',
        '',
        f'- Data de referencia fixa: {REFERENCIA:%d/%m/%Y %H:%M}',
        f'- Pedidos: {len(pedidos)}',
        f'- Eventos: {len(eventos)}',
        f'- Codigos oficiais: {len(dicionario)}',
        '',
        '## Ocorrencias de qualidade (categorias podem se sobrepor)',
        '',
    ]
    linhas += [f'- {problema}: {qtde}' for problema, qtde in contagens.items()]
    linhas += [
        '',
        'Observacao: este diagnostico apenas identifica anomalias. A limpeza, consolidacao,',
        'calculo do SLA, indicadores e alertas serao implementados nas proximas etapas.',
        'Eventos sem data e anomalias nao devem ser simplesmente apagados da trilha de auditoria.',
        '',
    ]
    (saidas_dir / 'resumo_diagnostico.md').write_text('\n'.join(linhas), encoding='utf-8')

    print(f'Pedidos: {len(pedidos)} | Eventos: {len(eventos)} | Codigos oficiais: {len(dicionario)}')
    print('\nProblemas identificados:')
    print(contagens.to_string())
    print('\nRelatorios gerados na pasta output/.')
    return relatorio


if __name__ == '__main__':
    analisar()
