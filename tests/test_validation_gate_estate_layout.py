from pathlib import Path


def test_validation_gate_materializes_required_estate_neighbors():
    workflow = Path('.github/workflows/gate.yml').read_text(encoding='utf-8')
    assert 'path: estate/Sanctum' in workflow
    assert 'repository: izzy9118-blip/Horus' in workflow
    assert 'path: estate/Horus' in workflow
    assert 'repository: izzy9118-blip/Talleyrand' in workflow
    assert 'path: estate/Talleyrand' in workflow
    assert 'cat > estate/config.yaml' in workflow
    assert 'working-directory: estate/Sanctum' in workflow


def test_gate_does_not_skip_the_real_estate_tests():
    workflow = Path('.github/workflows/gate.yml').read_text(encoding='utf-8')
    assert 'python -m pytest -q' in workflow
    assert '-k' not in workflow
    assert '--ignore' not in workflow
