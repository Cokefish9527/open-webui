#!/usr/bin/env python3
"""
Patch openapi.json to reflect external admin company/user interface changes.
Intended as a temporary helper until automated OpenAPI generation is wired up.
"""

import json
from pathlib import Path

OPENAPI_PATH = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> None:
    data = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    paths = data.setdefault("paths", {})
    components = data.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    security_schemes = components.setdefault("securitySchemes", {})

    security_schemes.setdefault(
        "ExternalAdminBearer",
        {"type": "http", "scheme": "bearer", "bearerFormat": "Bearer"},
    )

    schemas["ResetPasswordRequest"] = {
        "type": "object",
        "properties": {
            "new_password": {
                "type": "string",
                "minLength": 6,
                "description": "新密码，需至少 6 位",
            }
        },
        "required": ["new_password"],
    }

    schemas["OperationResponse"] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "default": True},
            "message": {"type": "string"},
            "active": {"type": "boolean", "nullable": True},
        },
    }

    bearer_security = [{"ExternalAdminBearer": []}]

    paths["/external/admin/users/{user_id}/reset-password"] = {
        "post": {
            "summary": "重置用户密码",
            "operationId": "reset_external_admin_user_password",
            "parameters": [
                {
                    "name": "user_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ResetPasswordRequest"}
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "密码重置成功",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OperationResponse"}
                        }
                    },
                },
                "404": {"description": "用户不存在"},
            },
            "security": bearer_security,
        }
    }

    paths["/external/admin/users/{user_id}/enable"] = {
        "post": {
            "summary": "启用用户账号",
            "operationId": "enable_external_admin_user",
            "parameters": [
                {
                    "name": "user_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "responses": {
                "200": {
                    "description": "启用成功",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OperationResponse"}
                        }
                    },
                },
                "404": {"description": "用户不存在"},
            },
            "security": bearer_security,
        }
    }

    paths["/external/admin/users/{user_id}/disable"] = {
        "post": {
            "summary": "禁用用户账号",
            "operationId": "disable_external_admin_user",
            "parameters": [
                {
                    "name": "user_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "responses": {
                "200": {
                    "description": "禁用成功",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OperationResponse"}
                        }
                    },
                },
                "404": {"description": "用户不存在"},
            },
            "security": bearer_security,
        }
    }

    OPENAPI_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
