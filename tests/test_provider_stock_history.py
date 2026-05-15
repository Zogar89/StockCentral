import json

from stockcentral.build_data import (
    load_provider_stock_history,
    maybe_update_provider_stock_history,
    write_public_provider_stock_history,
)


def payload_with_sources(generated_at, totals):
    return {
        "generated_at": generated_at,
        "sources": [
            {
                "id": source_id,
                "name": name,
                "zone": zone,
                "stats": {"total_stock_units": total, "product_count": 1},
            }
            for source_id, name, zone, total in totals
        ],
    }


def test_maybe_update_provider_stock_history_appends_daily_baseline_and_trims_to_30_days(tmp_path):
    history_path = tmp_path / "provider_stock_history.json"
    days = [
            {
                "date": f"2026-04-{day:02d}",
                "captured_at": f"2026-04-{day:02d}T09:00:00-03:00",
                "providers": {"mundoinsumos": day},
                "checks": [
                    {
                        "captured_at": f"2026-04-{day:02d}T09:00:00-03:00",
                        "providers": {"mundoinsumos": day},
                    }
                ],
            }
            for day in range(1, 31)
    ]
    history_path.write_text(json.dumps({"days": days}), encoding="utf-8")
    payload = payload_with_sources(
        "2026-05-01T09:04:00-03:00",
        [("mundoinsumos", "MundoInsumos", "Zona Norte", 120)],
    )

    updated = maybe_update_provider_stock_history(payload, history_path, snapshot_hour=9, max_days=30)

    assert updated is True
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert len(history["days"]) == 30
    assert history["days"][0]["date"] == "2026-04-02"
    assert history["days"][-1] == {
        "date": "2026-05-01",
        "captured_at": "2026-05-01T09:04:00-03:00",
        "providers": {"mundoinsumos": 120},
        "checks": [
            {
                "captured_at": "2026-05-01T09:04:00-03:00",
                "providers": {"mundoinsumos": 120},
            }
        ],
    }


def test_maybe_update_provider_stock_history_replaces_same_day_baseline_and_same_hour_check(tmp_path):
    history_path = tmp_path / "provider_stock_history.json"
    history_path.write_text(
        json.dumps(
            {
                "days": [
                    {
                        "date": "2026-05-01",
                        "captured_at": "2026-05-01T09:01:00-03:00",
                        "providers": {"mundoinsumos": 100},
                        "checks": [
                            {
                                "captured_at": "2026-05-01T09:01:00-03:00",
                                "providers": {"mundoinsumos": 100},
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    payload = payload_with_sources(
        "2026-05-01T09:10:00-03:00",
        [("mundoinsumos", "MundoInsumos", "Zona Norte", 130)],
    )

    updated = maybe_update_provider_stock_history(payload, history_path, snapshot_hour=9, max_days=30)

    assert updated is True
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history["days"] == [
        {
            "date": "2026-05-01",
            "captured_at": "2026-05-01T09:10:00-03:00",
            "providers": {"mundoinsumos": 130},
            "checks": [
                {
                    "captured_at": "2026-05-01T09:10:00-03:00",
                    "providers": {"mundoinsumos": 130},
                }
            ],
        }
    ]


def test_maybe_update_provider_stock_history_appends_intraday_check_without_changing_baseline(tmp_path):
    history_path = tmp_path / "provider_stock_history.json"
    history_path.write_text(
        json.dumps(
            {
                "days": [
                    {
                        "date": "2026-05-01",
                        "captured_at": "2026-05-01T09:00:00-03:00",
                        "providers": {"mundoinsumos": 100},
                        "checks": [
                            {
                                "captured_at": "2026-05-01T09:00:00-03:00",
                                "providers": {"mundoinsumos": 100},
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    payload = payload_with_sources(
        "2026-05-01T12:10:00-03:00",
        [("mundoinsumos", "MundoInsumos", "Zona Norte", 130)],
    )

    updated = maybe_update_provider_stock_history(payload, history_path, snapshot_hour=9, max_days=30)

    assert updated is True
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history["days"] == [
        {
            "date": "2026-05-01",
            "captured_at": "2026-05-01T09:00:00-03:00",
            "providers": {"mundoinsumos": 100},
            "checks": [
                {
                    "captured_at": "2026-05-01T09:00:00-03:00",
                    "providers": {"mundoinsumos": 100},
                },
                {
                    "captured_at": "2026-05-01T12:10:00-03:00",
                    "providers": {"mundoinsumos": 130},
                },
            ],
        }
    ]


def test_maybe_update_provider_stock_history_replaces_intraday_check_for_same_hour(tmp_path):
    history_path = tmp_path / "provider_stock_history.json"
    history_path.write_text(
        json.dumps(
            {
                "days": [
                    {
                        "date": "2026-05-01",
                        "captured_at": "2026-05-01T09:00:00-03:00",
                        "providers": {"mundoinsumos": 100},
                        "checks": [
                            {
                                "captured_at": "2026-05-01T09:00:00-03:00",
                                "providers": {"mundoinsumos": 100},
                            },
                            {
                                "captured_at": "2026-05-01T12:01:00-03:00",
                                "providers": {"mundoinsumos": 125},
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    payload = payload_with_sources(
        "2026-05-01T12:10:00-03:00",
        [("mundoinsumos", "MundoInsumos", "Zona Norte", 130)],
    )

    updated = maybe_update_provider_stock_history(payload, history_path, snapshot_hour=9, max_days=30)

    assert updated is True
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history["days"][0]["checks"] == [
        {
            "captured_at": "2026-05-01T09:00:00-03:00",
            "providers": {"mundoinsumos": 100},
        },
        {
            "captured_at": "2026-05-01T12:10:00-03:00",
            "providers": {"mundoinsumos": 130},
        },
    ]


def test_write_public_provider_stock_history_includes_provider_names_and_last_30_days(tmp_path):
    output_path = tmp_path / "provider_stock_history.json"
    history = {
        "days": [
            {
                "date": f"2026-04-{day:02d}",
                "captured_at": f"2026-04-{day:02d}T09:00:00-03:00",
                "providers": {"mundoinsumos": day, "filamentos3d": day + 10},
                "checks": [
                    {
                        "captured_at": f"2026-04-{day:02d}T09:00:00-03:00",
                        "providers": {"mundoinsumos": day, "filamentos3d": day + 10},
                    },
                    {
                        "captured_at": f"2026-04-{day:02d}T12:00:00-03:00",
                        "providers": {"mundoinsumos": day + 1, "filamentos3d": day + 11},
                    },
                ],
            }
            for day in range(1, 32)
        ]
    }
    payload = payload_with_sources(
        "2026-05-01T12:10:00-03:00",
        [
            ("mundoinsumos", "MundoInsumos", "Zona Norte", 130),
            ("filamentos3d", "Filamentos3D", "Zona Sur", 140),
        ],
    )

    write_public_provider_stock_history(history, payload, output_path, max_days=30)

    public_history = json.loads(output_path.read_text(encoding="utf-8"))
    assert public_history["generated_at"] == "2026-05-01T12:10:00-03:00"
    assert public_history["providers"] == [
        {"id": "mundoinsumos", "name": "MundoInsumos", "zone": "Zona Norte"},
        {"id": "filamentos3d", "name": "Filamentos3D", "zone": "Zona Sur"},
    ]
    assert len(public_history["days"]) == 30
    assert public_history["days"][0]["date"] == "2026-04-02"
    assert public_history["days"][-1]["date"] == "2026-04-31"
    assert public_history["days"][-1]["checks"] == [
        {
            "captured_at": "2026-04-31T09:00:00-03:00",
            "providers": {"mundoinsumos": 31, "filamentos3d": 41},
        },
        {
            "captured_at": "2026-04-31T12:00:00-03:00",
            "providers": {"mundoinsumos": 32, "filamentos3d": 42},
        },
    ]


def test_load_provider_stock_history_accepts_missing_file(tmp_path):
    assert load_provider_stock_history(tmp_path / "missing.json") == {"days": []}
