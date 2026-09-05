from __future__ import annotations

import pytest

from nicegui_app.services.workflow_parts.persistence import PersistenceWorkflowMixin
from nicegui_app.services.workflow_types import WorkflowError


@pytest.mark.parametrize("raw", [
    None, {}, "", "[]", "null", '{"id":1,"id":1}',
    '{"nested":{"id":1,"id":2}}', '{"number":NaN}', '{"number":Infinity}', '{"number":-Infinity}',
])
def test_operation_receipt_reader_rejects_ambiguous_or_invalid_json(raw):
    with pytest.raises(WorkflowError, match="receipt is invalid"):
        PersistenceWorkflowMixin._decode_operation_receipt(raw)


def test_operation_receipt_reader_preserves_valid_existing_shapes():
    assert PersistenceWorkflowMixin._decode_operation_receipt(
        '{"id":1,"name":"示範","nested":{"id":2},"values":[true,null,1.5]}'
    ) == {"id": 1, "name": "示範", "nested": {"id": 2}, "values": [True, None, 1.5]}
