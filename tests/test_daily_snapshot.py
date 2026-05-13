import json

from stockcentral.build_data import (
    apply_provider_stock_deltas,
    load_daily_provider_stock_snapshot,
    maybe_update_daily_provider_stock_snapshot,
)


def payload_with_sources(generated_at, totals):
    return {
        "generated_at": generated_at,
        "sources": [
            {
                "id": source_id,
                "stats": {
                    "total_stock_units": total,
                    "product_count": 1,
                    "total_stock_kg": float(total),
                    "in_stock_product_count": 1,
                    "out_of_stock_product_count": 0,
                },
            }
            for source_id, total in totals.items()
        ],
    }


def test_apply_provider_stock_deltas_compares_current_stock_against_previous_capture():
    payload = payload_with_sources(
        "2026-05-13T15:30:00-03:00",
        {"mundoinsumos": 110, "grupo_senz": 44, "filamentos3d": 75},
    )
    snapshot = {
        "captured_at": "2026-05-13T09:00:00-03:00",
        "providers": {"mundoinsumos": 104, "grupo_senz": 40, "filamentos3d": 70},
        "previous_captured_at": "2026-05-12T09:00:00-03:00",
        "previous_providers": {"mundoinsumos": 100, "grupo_senz": 100, "filamentos3d": 50},
    }

    apply_provider_stock_deltas(payload, snapshot)

    stats_by_id = {source["id"]: source["stats"] for source in payload["sources"]}
    assert stats_by_id["mundoinsumos"]["stock_delta_units"] == 10
    assert stats_by_id["grupo_senz"]["stock_delta_units"] == -56
    assert stats_by_id["filamentos3d"]["stock_delta_units"] == 25


def test_maybe_update_daily_provider_stock_snapshot_rotates_once_at_snapshot_hour(tmp_path):
    snapshot_path = tmp_path / "daily_provider_stock_snapshot.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "captured_at": "2026-05-12T09:00:00-03:00",
                "providers": {"mundoinsumos": 100},
                "previous_captured_at": "2026-05-11T09:00:00-03:00",
                "previous_providers": {"mundoinsumos": 95},
            }
        ),
        encoding="utf-8",
    )
    payload = payload_with_sources("2026-05-13T09:05:00-03:00", {"mundoinsumos": 125})

    updated = maybe_update_daily_provider_stock_snapshot(payload, snapshot_path, snapshot_hour=9)

    assert updated is True
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot == {
        "captured_at": "2026-05-13T09:05:00-03:00",
        "providers": {"mundoinsumos": 125},
        "previous_captured_at": "2026-05-12T09:00:00-03:00",
        "previous_providers": {"mundoinsumos": 100},
    }


def test_maybe_update_daily_provider_stock_snapshot_skips_other_hours(tmp_path):
    snapshot_path = tmp_path / "daily_provider_stock_snapshot.json"
    original = {
        "captured_at": "2026-05-12T09:00:00-03:00",
        "providers": {"mundoinsumos": 100},
        "previous_captured_at": "2026-05-11T09:00:00-03:00",
        "previous_providers": {"mundoinsumos": 95},
    }
    snapshot_path.write_text(json.dumps(original), encoding="utf-8")
    payload = payload_with_sources("2026-05-13T15:05:00-03:00", {"mundoinsumos": 125})

    updated = maybe_update_daily_provider_stock_snapshot(payload, snapshot_path, snapshot_hour=9)

    assert updated is False
    assert json.loads(snapshot_path.read_text(encoding="utf-8")) == original


def test_load_daily_provider_stock_snapshot_accepts_missing_file(tmp_path):
    assert load_daily_provider_stock_snapshot(tmp_path / "missing.json") == {}
