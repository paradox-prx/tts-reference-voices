"""Harness hook: registers the `higgs_gguf` vLLM load format in every Python process of the engine.

vLLM-Omni spawns its API server and each stage as fresh processes ('spawn'), so registering the loader in the
launcher alone is not enough. Python imports `sitecustomize` at start-up from the first sys.path entry that has one;
scripts/run_gguf_engine.sh puts this directory on PYTHONPATH, and the spawned processes inherit it. Nothing is
installed into the engine venv.

Inert unless HIGGS_GGUF_HARNESS=1. When active it adds the higgs-gguf folder to sys.path and, the moment
`vllm.model_executor.model_loader` finishes importing, calls higgs_gguf.vllm_loader.register(). It does not import
vLLM itself, so unrelated helper processes stay cheap.
"""

import os
import sys

if os.environ.get("HIGGS_GGUF_HARNESS") == "1":
    import importlib.abc
    import importlib.util

    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _ROOT not in sys.path:
        sys.path.append(_ROOT)
    _TARGET = "vllm.model_executor.model_loader"

    def _register() -> None:
        try:
            from higgs_gguf.vllm_loader import register
            register()
        except Exception as e:  # never break the engine import; the missing format will be reported by vLLM
            print(f"[higgs_gguf harness] registration failed in pid {os.getpid()}: {e!r}", file=sys.stderr)

    class _PostImportHook(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname != _TARGET:
                return None
            sys.meta_path.remove(self)
            spec = importlib.util.find_spec(fullname)
            if spec is None or spec.loader is None:
                return spec
            exec_module = spec.loader.exec_module

            def exec_and_register(module):
                exec_module(module)
                _register()

            spec.loader.exec_module = exec_and_register
            return spec

    sys.meta_path.insert(0, _PostImportHook())
