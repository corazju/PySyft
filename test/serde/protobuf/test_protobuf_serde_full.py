from collections import OrderedDict
import pytest
import numpy
import torch
from functools import partial
import traceback
import io

import syft
from syft.serde import protobuf
from test.serde.serde_helpers import *

# Dictionary containing test samples functions
samples = OrderedDict()

# Native
samples[type(None)] = make_none

# PyTorch
samples[torch.device] = make_torch_device
samples[torch.jit.ScriptModule] = make_torch_scriptmodule
samples[torch._C.Function] = make_torch_cfunction
samples[torch.jit.TopLevelTracedModule] = make_torch_topleveltracedmodule
samples[torch.nn.Parameter] = make_torch_parameter
samples[torch.Tensor] = make_torch_tensor
samples[torch.Size] = make_torch_size


def test_serde_coverage():
    """Checks all types in serde are tested"""
    for cls, _ in protobuf.serde.bufferizers.items():
        has_sample = cls in samples
        assert has_sample is True, "Serde for %s is not tested" % cls


@pytest.mark.parametrize("cls", samples)
def test_serde_roundtrip_protobuf(cls, workers):
    """Checks that values passed through serialization-deserialization stay same"""
    serde_worker = syft.hook.local_worker
    original_framework = serde_worker.framework
    _samples = samples[cls](workers=workers)
    for sample in _samples:
        _to_protobuf = (
            protobuf.serde._bufferize
            if not sample.get("forced", False)
            else protobuf.serde._force_full_bufferize
        )
        serde_worker.framework = sample.get("framework", torch)
        obj = sample.get("value")
        protobuf_obj = _to_protobuf(serde_worker, obj)
        roundtrip_obj = None
        if not isinstance(obj, Exception):
            roundtrip_obj = protobuf.serde._unbufferize(serde_worker, protobuf_obj)

        serde_worker.framework = original_framework

        if sample.get("cmp_detailed", None):
            # Custom detailed objects comparison function.
            assert sample.get("cmp_detailed")(roundtrip_obj, obj) is True
        else:
            assert type(roundtrip_obj) == type(obj)
            assert roundtrip_obj == obj
