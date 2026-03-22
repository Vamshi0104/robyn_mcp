
from robyn_mcp.core.config import RobynMCPConfig
from robyn_mcp.core.introspect import extract_routes
from robyn_mcp.security.auth import HeaderPrincipalResolver


class FakeRoute:
    def __init__(self, path, method, handler, auth_required=False):
        self.route = path
        self.route_type = method
        self.handler = handler
        self.auth_required = auth_required


class FakeIdentity:
    def __init__(self):
        self.sub = 'user-123'
        self.tenant_id = 'tenant-7'


class FakeRequest:
    def __init__(self):
        self.identity = FakeIdentity()
        self.claims = {'azp': 'client-9', 'scp': 'read write'}


def create_app():
    class App:
        routes = []

        @staticmethod
        def openapi():
            return {
                'components': {
                    'schemas': {
                        'ItemBody': {
                            'type': 'object',
                            'properties': {
                                'name': {'type': 'string'},
                                'metadata': {'$ref': '#/components/schemas/Meta'},
                            },
                            'required': ['name'],
                        },
                        'Meta': {
                            'type': 'object',
                            'properties': {'active': {'type': 'boolean'}},
                        },
                    }
                },
                'paths': {
                    '/items/{item_id}': {
                        'post': {
                            'operationId': 'create_item',
                            'summary': 'Create item',
                            'security': [{'oauth': ['items.write']}],
                            'parameters': [
                                {'name': 'item_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
                                {'name': 'verbose', 'in': 'query', 'required': False, 'schema': {'type': 'boolean'}},
                            ],
                            'requestBody': {
                                'required': True,
                                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ItemBody'}}},
                            },
                            'responses': {
                                '200': {'content': {'application/json': {'schema': {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}}}}}
                            },
                        }
                    }
                }
            }

    def handler(item_id: int, verbose: bool = False):
        return {'ok': True}

    App.routes.append(FakeRoute('/items/{item_id}', 'POST', handler))
    return App()


def test_openapi_harvesting_merges_params_and_body():
    app = create_app()
    routes = extract_routes(app, RobynMCPConfig())
    route = routes[0]
    props = route.request_body_schema['properties']
    assert 'item_id' in props
    assert 'verbose' in props
    assert 'name' in props
    assert props['metadata']['properties']['active']['type'] == 'boolean'
    assert route.requires_auth is True
    assert route.auth_scopes == ['items.write']
    assert route.response_schema['properties']['ok']['type'] == 'boolean'


def test_claim_aware_auth_resolution():
    resolver = HeaderPrincipalResolver()
    ctx = resolver.resolve(FakeRequest(), {'x-auth-scopes': 'admin'}, RobynMCPConfig())
    assert ctx.principal_id == 'user-123'
    assert ctx.tenant_id == 'tenant-7'
    assert ctx.client_id == 'client-9'
    assert 'read' in ctx.scopes and 'write' in ctx.scopes and 'admin' in ctx.scopes
