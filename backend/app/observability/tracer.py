"""
Codex One v2 — Langfuse Tracer Integration

Provides decorators and context managers to automatically trace
every LangGraph node, LLM call, and embedding operation.

When Langfuse is not configured, all tracing is a no-op.
"""

import time
import functools
from typing import Optional, Any
from app.config import settings

# Langfuse client singleton
_langfuse = None


def get_langfuse():
    """Get or create the Langfuse client singleton."""
    global _langfuse
    if _langfuse is not None:
        return _langfuse

    if not settings.LANGFUSE_ENABLED or not settings.LANGFUSE_PUBLIC_KEY:
        return None

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        print("[Langfuse] Connected successfully")
        return _langfuse
    except Exception as e:
        print(f"[Langfuse] Init failed: {e}")
        return None


class TraceContext:
    """
    Context manager for creating a Langfuse trace with nested spans.
    
    Usage:
        with TraceContext("query", user_id="user1") as trace:
            with trace.span("embedding") as span:
                # do work
                span.end(output={"dim": 768}, metadata={"latency_ms": 45})
    """

    def __init__(self, name: str, user_id: str = "local", metadata: Optional[dict] = None):
        self.name = name
        self.user_id = user_id
        self.metadata = metadata or {}
        self.trace = None
        self._langfuse = get_langfuse()

    def __enter__(self):
        if self._langfuse:
            try:
                self.trace = self._langfuse.trace(
                    name=self.name,
                    user_id=self.user_id,
                    metadata=self.metadata,
                )
            except Exception as e:
                print(f"[Langfuse] Trace creation failed: {e}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._langfuse:
            try:
                self._langfuse.flush()
            except Exception:
                pass
        return False

    def span(self, name: str, input_data: Any = None) -> "SpanContext":
        """Create a child span within this trace."""
        return SpanContext(self, name, input_data)

    def generation(
        self,
        name: str,
        model: str,
        input_data: Any = None,
        model_parameters: Optional[dict] = None,
    ) -> "GenerationContext":
        """Create a generation span (for LLM calls) within this trace."""
        return GenerationContext(self, name, model, input_data, model_parameters)


class SpanContext:
    """Context manager for a Langfuse span."""

    def __init__(self, parent: TraceContext, name: str, input_data: Any = None):
        self.parent = parent
        self.name = name
        self.input_data = input_data
        self._span = None
        self._start_time = 0.0

    def __enter__(self):
        self._start_time = time.perf_counter()
        if self.parent.trace:
            try:
                self._span = self.parent.trace.span(
                    name=self.name,
                    input=self.input_data,
                )
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_ms = (time.perf_counter() - self._start_time) * 1000
        if self._span:
            try:
                self._span.end(
                    metadata={"latency_ms": round(elapsed_ms, 2)},
                    level="ERROR" if exc_type else "DEFAULT",
                )
            except Exception:
                pass
        return False

    def end(self, output: Any = None, metadata: Optional[dict] = None):
        """Manually end the span with output data."""
        if self._span:
            try:
                meta = metadata or {}
                meta["latency_ms"] = round((time.perf_counter() - self._start_time) * 1000, 2)
                self._span.end(output=output, metadata=meta)
            except Exception:
                pass


class GenerationContext:
    """Context manager for a Langfuse generation (LLM call tracking)."""

    def __init__(
        self,
        parent: TraceContext,
        name: str,
        model: str,
        input_data: Any = None,
        model_parameters: Optional[dict] = None,
    ):
        self.parent = parent
        self.name = name
        self.model = model
        self.input_data = input_data
        self.model_parameters = model_parameters
        self._generation = None
        self._start_time = 0.0

    def __enter__(self):
        self._start_time = time.perf_counter()
        if self.parent.trace:
            try:
                self._generation = self.parent.trace.generation(
                    name=self.name,
                    model=self.model,
                    input=self.input_data,
                    model_parameters=self.model_parameters or {},
                )
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def end(
        self,
        output: str = "",
        usage: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ):
        """End the generation with output and token usage."""
        if self._generation:
            try:
                elapsed_ms = (time.perf_counter() - self._start_time) * 1000
                meta = metadata or {}
                meta["latency_ms"] = round(elapsed_ms, 2)

                self._generation.end(
                    output=output,
                    usage=usage or {},
                    metadata=meta,
                )
            except Exception:
                pass


def trace_node(node_name: str):
    """
    Decorator to trace a LangGraph node function.
    
    Automatically creates a span for the node with input/output state.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(state, *args, **kwargs):
            langfuse = get_langfuse()
            if not langfuse:
                return func(state, *args, **kwargs)

            start = time.perf_counter()
            try:
                result = func(state, *args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000

                # Log node execution to in-memory store
                from app.observability.metrics_store import record_node_execution
                record_node_execution(node_name, elapsed, success=True)

                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                from app.observability.metrics_store import record_node_execution
                record_node_execution(node_name, elapsed, success=False)
                raise

        return wrapper
    return decorator
