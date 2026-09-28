"""End-to-end test of batch trade-file upload on the Backtest tab."""

import os

import pytest
from starlette.testclient import TestClient

import app.main as main
from tests.test_instruments import PRICES, _write_eod


@pytest.fixture
def client(tmp_dir, monkeypatch):
    eod = os.path.join(tmp_dir, "eod")
    out = os.path.join(tmp_dir, "out")
    up = os.path.join(tmp_dir, "up")
    for d in (eod, out, up):
        os.makedirs(d)
    for pair, level in PRICES.items():
        _write_eod(eod, pair, level)
    monkeypatch.setattr(main, "EOD_DIR", eod)
    monkeypatch.setattr(main, "OUTPUT_DIR", out)
    monkeypatch.setattr(main, "UPLOAD_DIR", up)
    c = TestClient(main.app)
    c.post("/login", data={"password": main.APP_PASSWORD})
    return c


def _trades(instrument, entry, exit_):
    return ("Instrument,Market.pos.,Entry.price,Exit.price,Entry.time,Exit.time,Quantity\n"
            f"{instrument},Long,{entry},{exit_},06/01/2020 10:00,06/01/2020 15:00,1\n"
            f"{instrument},Short,{exit_},{entry},08/01/2020 10:00,09/01/2020 15:00,1\n").encode()


def test_batch_processes_each_file_and_reports_failures(client):
    files = [
        ("tradefiles", ("BT_ESA.csv", _trades("$ESAUSD", 3200, 3210), "text/csv")),
        ("tradefiles", ("BT_AUDNZD.csv", _trades("$AUDNZD", 1.05, 1.06), "text/csv")),
        ("tradefiles", ("BT_BAD.csv", _trades("$FOOBAR", 1.0, 1.1), "text/csv")),
    ]
    data = {"timezone": "Europe/London", "aum": "100000000", "strategy": "T",
            "timeframe": "60 min"}
    r = client.post("/process/backtest", files=files, data=data)
    assert r.status_code == 200
    html = r.text
    assert "Batch results: 2/3 files processed" in html
    assert "ESAUSD" in html and "AUDNZD" in html
    assert "Failed: BT_BAD.csv" in html


def test_backtest_tab_shows_registry(client):
    html = client.get("/tab/backtest").text
    assert 'multiple' in html and 'name="tradefiles"' in html
    assert "XAUXAG" in html and "Multiply by EOD XAGUSD" in html
