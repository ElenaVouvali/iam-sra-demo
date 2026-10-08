"""Calibration orchestration tests; no live model accuracy claim."""
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]


def runner(tmp_path,monkeypatch,statuses):
    module=runpy.run_path(str(ROOT/'scripts/run-calibration.py'))
    (tmp_path/'.runtime').mkdir()
    module['main'].__globals__['ROOT']=tmp_path
    calls=[]
    def run(args,**kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=statuses.pop(0))
    monkeypatch.setattr(module['subprocess'],'run',run)
    return module['main'],calls


def test_development_mismatch_keeps_validation_separate(tmp_path,monkeypatch):
    main,calls=runner(tmp_path,monkeypatch,[1,0,1,0])
    assert main()==1 and len(calls)==4
    assert 'fresh_validation' in calls[-1] and '--check-followups' in calls[-1]
    summary=json.loads((tmp_path/'.runtime/calibration-summary.json').read_text())
    assert summary['complete'] and not summary['all_passed']
    assert len({stage['report'] for stage in summary['stages']})==4


def test_unavailable_model_stops_without_claiming_complete(tmp_path,monkeypatch):
    main,calls=runner(tmp_path,monkeypatch,[2])
    assert main()==2 and len(calls)==1
    summary=json.loads((tmp_path/'.runtime/calibration-summary.json').read_text())
    assert not summary['complete'] and not summary['all_passed']
