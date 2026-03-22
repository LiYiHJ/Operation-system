from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.batch_service import BatchService


def test_normalize_mapping_items_assigns_unique_keys_for_duplicate_headers():
    payload = {
        'fieldMappings': [
            {
                'originalField': 'Динамика',
                'dynamicCompanion': True,
                'sampleValues': ['-0.5'],
            },
            {
                'originalField': 'Динамика',
                'dynamicCompanion': True,
                'sampleValues': ['0.08'],
            },
            {
                'originalField': 'Артикул',
                'standardField': 'sku',
                'confidence': 0.99,
                'sampleValues': ['HAA132-03-Y1'],
            },
        ]
    }

    normalized = BatchService._normalize_mapping_items(payload)

    assert len(normalized) == 3
    assert normalized[0]['sourceHeader'] == 'Динамика__dup1'
    assert normalized[1]['sourceHeader'] == 'Динамика__dup2'
    assert normalized[0]['sourceHeaderDisplay'] == 'Динамика'
    assert normalized[1]['sourceHeaderDisplay'] == 'Динамика'
    assert normalized[0]['mappingStatus'] == 'dynamic_companion'
    assert normalized[1]['mappingStatus'] == 'dynamic_companion'

    assert normalized[2]['sourceHeader'] == 'Артикул'
    assert normalized[2]['targetField'] == 'sku'
    assert normalized[2]['mappingStatus'] == 'mapped'
