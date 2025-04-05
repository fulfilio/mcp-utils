from typing import Any

from pydantic import BaseModel

from mcp_utils.utils import inspect_callable


def func_no_args() -> str:
    return "hello"


def func_with_args(name: str, age: int) -> str:
    return f"{name} is {age} years old"


def func_with_default_args(name: str, age: int = 30) -> str:
    return f"{name} is {age} years old"


def func_with_optional(name: str | None = None) -> str:
    return f"Hello {name or 'anonymous'}"


def func_with_complex_types(
    items: list[dict[str, Any]], config: dict[str, str] | None = None
) -> list[str]:
    return []


class DemoClass:
    def method_with_self(self, name: str) -> str:
        return f"Hello {name}"

    @classmethod
    def class_method(cls, value: int) -> int:
        return value * 2

    @staticmethod
    def static_method(value: float) -> float:
        return value / 2


def test_inspect_no_args():
    metadata = inspect_callable(func_no_args)
    assert isinstance(metadata.arg_model, type)
    assert issubclass(metadata.arg_model, BaseModel)
    assert len(metadata.arg_model.model_fields) == 0
    assert metadata.return_type is str


def test_inspect_with_args():
    metadata = inspect_callable(func_with_args)
    assert isinstance(metadata.arg_model, type)
    assert issubclass(metadata.arg_model, BaseModel)
    assert set(metadata.arg_model.model_fields.keys()) == {"name", "age"}
    fields = metadata.arg_model.model_fields
    assert fields["name"].annotation is str
    assert fields["age"].annotation is int
    assert metadata.return_type is str


def test_inspect_with_default_args():
    metadata = inspect_callable(func_with_default_args)
    assert isinstance(metadata.arg_model, type)
    assert issubclass(metadata.arg_model, BaseModel)
    fields = metadata.arg_model.model_fields
    assert fields["name"].is_required()  # required field
    assert fields["age"].default == 30  # optional field with default
    assert metadata.return_type is str


def test_inspect_with_optional():
    metadata = inspect_callable(func_with_optional)
    assert isinstance(metadata.arg_model, type)
    assert issubclass(metadata.arg_model, BaseModel)
    fields = metadata.arg_model.model_fields
    assert fields["name"].default is None
    assert metadata.return_type is str


def test_inspect_with_complex_types():
    metadata = inspect_callable(func_with_complex_types)
    assert isinstance(metadata.arg_model, type)
    assert issubclass(metadata.arg_model, BaseModel)
    fields = metadata.arg_model.model_fields
    assert fields["items"].is_required()  # required field
    assert fields["config"].default is None  # optional field


def test_inspect_method():
    demo = DemoClass()
    metadata = inspect_callable(demo.method_with_self)
    assert isinstance(metadata.arg_model, type)
    assert issubclass(metadata.arg_model, BaseModel)
    assert set(metadata.arg_model.model_fields.keys()) == {"name"}
    assert metadata.return_type is str


def test_inspect_classmethod():
    metadata = inspect_callable(DemoClass.class_method)
    assert isinstance(metadata.arg_model, type)
    assert issubclass(metadata.arg_model, BaseModel)
    assert set(metadata.arg_model.model_fields.keys()) == {"value"}
    fields = metadata.arg_model.model_fields
    assert fields["value"].annotation is int
    assert metadata.return_type is int


def test_inspect_staticmethod():
    metadata = inspect_callable(DemoClass.static_method)
    assert isinstance(metadata.arg_model, type)
    assert issubclass(metadata.arg_model, BaseModel)
    assert set(metadata.arg_model.model_fields.keys()) == {"value"}
    fields = metadata.arg_model.model_fields
    assert fields["value"].annotation is float
    assert metadata.return_type is float


def test_inspect_with_skip_names():
    metadata = inspect_callable(func_with_args, skip_names=["age"])
    assert isinstance(metadata.arg_model, type)
    assert issubclass(metadata.arg_model, BaseModel)
    assert set(metadata.arg_model.model_fields.keys()) == {"name"}
    assert metadata.return_type is str
