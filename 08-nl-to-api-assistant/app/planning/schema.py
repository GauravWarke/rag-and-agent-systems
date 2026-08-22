"""Parses a FastAPI-generated OpenAPI schema into a flat list of
`EndpointSpec`s: names, descriptions, parameters, request/response
schemas, and the `x-risk-level` / `x-required-roles` extensions the
business API attaches to every route.
"""
from __future__ import annotations

from typing import Any

from app.planning.models import EndpointParam, EndpointSpec

_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _resolve_schema(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not ref:
        return schema
    name = ref.rsplit("/", 1)[-1]
    return components.get(name, {})


def parse_openapi_schema(openapi_schema: dict[str, Any]) -> list[EndpointSpec]:
    endpoints: list[EndpointSpec] = []
    paths = openapi_schema.get("paths", {})
    components = openapi_schema.get("components", {}).get("schemas", {})

    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.lower() not in _HTTP_METHODS:
                continue

            operation_id = operation.get("operationId") or f"{method}_{path}"
            parameters: list[EndpointParam] = []
            for param in operation.get("parameters", []):
                parameters.append(
                    EndpointParam(
                        name=param["name"],
                        location=param.get("in", "query"),
                        required=param.get("required", False),
                        param_schema=param.get("schema", {}),
                    )
                )

            request_body_schema: dict[str, Any] | None = None
            request_body = operation.get("requestBody")
            if request_body:
                body_schema = request_body.get("content", {}).get("application/json", {}).get("schema", {})
                request_body_schema = _resolve_schema(body_schema, components)
                required_props = set(request_body_schema.get("required", []))
                for name, prop_schema in request_body_schema.get("properties", {}).items():
                    parameters.append(
                        EndpointParam(
                            name=name,
                            location="body",
                            required=name in required_props,
                            param_schema=prop_schema,
                        )
                    )

            response_schema: dict[str, Any] | None = None
            success_response = operation.get("responses", {}).get("200") or operation.get(
                "responses", {}
            ).get("201")
            if success_response:
                response_schema = success_response.get("content", {}).get("application/json", {}).get(
                    "schema"
                )

            endpoints.append(
                EndpointSpec(
                    operation_id=operation_id,
                    method=method.upper(),
                    path=path,
                    summary=operation.get("summary", ""),
                    description=operation.get("description", ""),
                    parameters=parameters,
                    request_body_schema=request_body_schema,
                    response_schema=response_schema,
                    risk_level=operation.get("x-risk-level", "read_only"),
                    required_roles=operation.get("x-required-roles", []),
                )
            )

    return endpoints
