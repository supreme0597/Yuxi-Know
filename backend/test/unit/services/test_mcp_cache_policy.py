from types import SimpleNamespace

from yuxi.services.mcp.cache_policy import build_cache_policy


def test_static_policy_is_global_and_shareable():
    policy = build_cache_policy(None, None)

    assert policy.partition == "global"
    assert policy.cache_tool_objects is True
    assert policy.shared_across_users is True


def test_bound_policy_is_partitioned_by_connection():
    connection = SimpleNamespace(id=11, scope_type="department")
    policy = build_cache_policy("bound_secret", connection)

    assert policy.partition == "connection:11"
    assert policy.cache_tool_objects is True
    assert policy.shared_across_users is False


def test_system_bound_policy_can_share_only_inside_connection_partition():
    connection = SimpleNamespace(id=12, scope_type="system")
    policy = build_cache_policy("stdio_env", connection)

    assert policy.partition == "connection:12"
    assert policy.shared_across_users is True


def test_dynamic_policy_never_caches_token_bearing_tool_objects():
    connection = SimpleNamespace(id=21, scope_type="user")
    policy = build_cache_policy("client_credentials", connection)

    assert policy.partition == "connection:21"
    assert policy.cache_tool_objects is False
    assert policy.cache_manifest is True
