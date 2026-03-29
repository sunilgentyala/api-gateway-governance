# Adapters

Each adapter in this folder takes one policy YAML file and produces gateway-native configuration for one specific gateway product.

## How adapters work

The adapter interface is simple. Every adapter is a Python script that:

1. Reads a policy YAML file (`--policy` argument)
2. Validates the policy has the required fields
3. Compiles it to the gateway's native format
4. Writes the output file (`--output` argument)

The output file should never be edited by hand. If you need to change the configuration, change the source policy and recompile.

## Supported adapters

| Gateway | Adapter | Output Format |
|---|---|---|
| Kong | `kong/compile.py` | YAML (plugin config) |
| AWS API Gateway | `aws-api-gateway/compile.py` | JSON (usage plan / authorizer) |
| Envoy | `envoy/compile.py` | YAML (filter chain) |

## Supported policy types

| Type | Kong | AWS | Envoy |
|---|---|---|---|
| `rate-limit` | rate-limiting plugin | Usage Plan + throttle | local_ratelimit filter |
| `authentication` | jwt plugin | JWT authorizer | jwt_authn filter |
| `workload-identity` | mtls-auth plugin | mTLS truststore | DownstreamTlsContext |

## Writing a new adapter

If you want to add support for a new gateway (Azure APIM, Apigee, Nginx, etc.):

1. Create a new folder: `adapters/your-gateway-name/`
2. Create `compile.py` following the same pattern as the existing adapters
3. Support at minimum `rate-limit`, `authentication`, and `workload-identity` policy types
4. Add tests in `tests/unit/test_your_gateway_adapter.py`
5. Open a pull request

The interface contract:

```python
# Every adapter must implement this function
def compile(policy: dict) -> dict:
    """
    Takes the loaded policy dict (from the 'policy' key of the YAML).
    Returns a dict that will be serialized to the output file.
    Must include _source_policy, _compiled_by, and _do_not_edit keys.
    """
    pass
```
