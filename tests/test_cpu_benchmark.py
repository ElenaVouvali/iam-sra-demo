import time
import pytest
from iam_sra.cpu_benchmark import CPURuntime, CPUBaselineClient


@pytest.mark.parametrize('threads,seconds', [(0, 300), (17, 300), (4, 0), (4, 3601)])
def test_cpu_resource_bounds(threads, seconds):
    with pytest.raises(ValueError):
        CPURuntime(threads, seconds)


def test_cpu_lifecycle_records_distinct_deployment():
    runtime = CPURuntime(threads=2, generation_seconds=60)
    client = CPUBaselineClient(runtime)
    client._start()
    deployment = client.last_settings['expected_deployment']
    assert deployment['device'] == 'cpu'
    assert deployment['dtype'] == 'float32'
    assert deployment['model_loaded'] is False
    assert deployment['gpu_timing_comparable'] is False
    assert client.last_settings['backend'] == 'transformers_xgrammar_cpu'
    assert client._deadline > time.monotonic() + 180
    assert client.base_url == 'cpu-local'


def test_cpu_lifecycle_records_missing_optional_libraries(monkeypatch):
    from importlib.metadata import PackageNotFoundError

    def installed_version(name):
        if name in ('torch', 'xgrammar'):
            raise PackageNotFoundError(name)
        return '4.51.3'

    monkeypatch.setattr('importlib.metadata.version', installed_version)
    client = CPUBaselineClient(CPURuntime())
    client._start()
    deployment = client.last_settings['expected_deployment']
    assert deployment['libraries'] == {
        'torch': None, 'transformers': '4.51.3', 'xgrammar': None,
    }
    assert deployment['model_loaded'] is False
