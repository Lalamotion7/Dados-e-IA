"""Pipeline completo com validação, staging e publicação recuperável.

Executar na raiz: python -m src.main
A referência do SLA permanece 24/09/2026 18:00; o timestamp do manifesto
refere-se somente ao momento real da execução do processamento.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.diagnostico import analisar, REFERENCIA
from src.rastreamento import executar as executar_rastreamento
from src.sla import executar as executar_sla
from src.ocorrencias import executar as executar_ocorrencias
from src.validacao import validar_entradas, EntradaInvalida

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dados"
OUTPUT = ROOT / "output"
MANIFEST = "manifesto_execucao.json"
SAIDAS_OBRIGATORIAS = [
    "diagnostico_qualidade.csv", "resumo_diagnostico.md", "pedidos_consolidados.csv",
    "auditoria_eventos.csv", "eventos_validos.csv", "pedidos_sla.csv",
    "indicadores_gerais.csv", "otd_transportadoras.csv", "contagem_situacoes.csv",
    "resumo_sla.md", "ocorrencias_classificadas.csv", "frequencia_categorias.csv",
    "alertas_operacionais.csv", "alerta_operacional.txt", "resumo_ocorrencias_alertas.md",
]


def ler_manifesto(output_dir: Path) -> dict | None:
    path = Path(output_dir) / MANIFEST
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError, OSError):
        return None


def validar_saidas(staging: Path, pedidos_esperados: int, eventos_esperados: int) -> dict:
    ausentes = [name for name in SAIDAS_OBRIGATORIAS if not (staging / name).is_file()]
    if ausentes:
        raise RuntimeError(f"Saídas não geradas: {', '.join(ausentes)}")
    read = lambda name: pd.read_csv(staging / name, sep=";", encoding="utf-8-sig")
    pedidos = read("pedidos_sla.csv")
    consolidados = read("pedidos_consolidados.csv")
    auditoria = read("auditoria_eventos.csv")
    validos = read("eventos_validos.csv")
    alerts = read("alertas_operacionais.csv")
    situacoes = read("contagem_situacoes.csv")
    otd = read("indicadores_gerais.csv")
    if len(pedidos) != pedidos_esperados or len(consolidados) != pedidos_esperados:
        raise RuntimeError("Conferência falhou: total de pedidos de saída difere do total de entrada.")
    if pedidos["id_pedido"].duplicated().any():
        raise RuntimeError("Conferência falhou: pedido duplicado na saída consolidada.")
    if pedidos["situacao_sla"].isna().any() or int(situacoes["quantidade"].sum()) != pedidos_esperados:
        raise RuntimeError("Conferência falhou: existem pedidos sem classificação de SLA.")
    if len(auditoria) != eventos_esperados:
        raise RuntimeError("Conferência falhou: auditoria não preserva todos os eventos originais.")
    utilizados = int((auditoria["decisao"] == "UTILIZADO").sum())
    quarentena = int((auditoria["decisao"] == "QUARENTENA").sum())
    if len(validos) != utilizados or utilizados + quarentena != eventos_esperados:
        raise RuntimeError("Conferência falhou: soma de eventos válidos e em quarentena não fecha.")
    if len(alerts) != int(pedidos["situacao_sla"].isin(["ATRASADO_EM_ABERTO", "EM_RISCO"]).sum()):
        raise RuntimeError("Conferência falhou: alertas não correspondem aos pedidos prioritários.")
    if len(otd) != 1:
        raise RuntimeError("Conferência falhou: indicadores gerais inválidos.")
    return {
        "pedidos": len(pedidos),
        "eventos": eventos_esperados,
        "eventos_validos": utilizados,
        "eventos_quarentena": quarentena,
        "entregues": int(pedidos["situacao_sla"].isin(["ENTREGUE_NO_PRAZO", "ENTREGUE_COM_ATRASO"]).sum()),
        "alertas": len(alerts),
        "otd_pct": float(otd.iloc[0]["otd_pct"]),
    }


def publicar(staging: Path, output_dir: Path) -> None:
    """Swap de diretórios no mesmo volume; se falhar, restaura saída anterior.

    Publicação simplificada, com janela muito curta entre renomeações;
    não equivale a transação de banco de dados ou garantia multiusuário.
    """
    output_dir = Path(output_dir)
    old = output_dir.with_name(output_dir.name + "_backup_publicacao")
    if old.exists():
        raise RuntimeError(f"Backup de execução anterior existente: {old}. Verifique antes de continuar.")
    tinha_output = output_dir.exists()
    if tinha_output:
        output_dir.rename(old)
    try:
        staging.rename(output_dir)
    except Exception:
        if tinha_output:
            old.rename(output_dir)
        raise
    if tinha_output:
        # Falha na limpeza não invalida a publicação; evita falso erro pós-sucesso.
        try:
            shutil.rmtree(old)
        except OSError:
            print(f"Aviso: backup de execução anterior mantido em {old}")


def main(dados_dir: Path = DATA, output_dir: Path = OUTPUT) -> dict:
    dados_dir, output_dir = Path(dados_dir), Path(output_dir)
    inicio = time.monotonic()
    print("[Pré-processamento] Validando arquivos de entrada...")
    arquivos = validar_entradas(dados_dir)
    anterior = ler_manifesto(output_dir)
    ids_pedidos = set(arquivos["pedidos.csv"]["id_pedido"].astype(str).tolist())
    ids_eventos = set(arquivos["eventos_rastreio.csv"]["id_evento"].astype(str).tolist())
    hash_entradas = {
        filename: hashlib.sha256((dados_dir / filename).read_bytes()).hexdigest()
        for filename in arquivos
    }
    # Staging criado no mesmo diretório pai para preservar os renames locais.
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".agv_staging_", dir=output_dir.parent) as temporary:
        staging = Path(temporary) / "resultado"
        staging.mkdir()
        print("[1/4] Diagnóstico de qualidade")
        analisar(dados_dir, staging)
        print("[2/4] Consolidação e auditoria")
        executar_rastreamento(dados_dir, staging)
        print("[3/4] Cálculo de SLA e indicadores")
        executar_sla(dados_dir, staging)
        print("[4/4] Ocorrências e alertas simulados")
        executar_ocorrencias(dados_dir, staging)
        metricas = validar_saidas(staging, len(ids_pedidos), len(ids_eventos))

        if anterior is None:
            alteracoes = {"comparacao_disponivel": False, "novos_pedidos": None,
                          "pedidos_removidos": None, "novos_eventos": None}
        else:
            alteracoes = {
                "comparacao_disponivel": True,
                "novos_pedidos": len(ids_pedidos - set(anterior.get("ids_pedidos", []))),
                "pedidos_removidos": len(set(anterior.get("ids_pedidos", [])) - ids_pedidos),
                "novos_eventos": len(ids_eventos - set(anterior.get("ids_eventos", []))),
            }
        manifesto = {
            "executado_em": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "referencia_sla": REFERENCIA.isoformat(),
            "duracao_segundos": round(time.monotonic() - inicio, 2),
            "metricas": metricas,
            "alteracoes": alteracoes,
            "hash_sha256_entradas": hash_entradas,
            "ids_pedidos": sorted(ids_pedidos),
            "ids_eventos": sorted(ids_eventos),
        }
        (staging / MANIFEST).write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")
        publicar(staging, output_dir)
    print(f"Processamento concluído e publicado com segurança em {output_dir}/")
    return manifesto


if __name__ == "__main__":
    try:
        main()
    except (EntradaInvalida, RuntimeError) as exc:
        print(f"Falha controlada: {exc}")
        raise SystemExit(1) from exc
