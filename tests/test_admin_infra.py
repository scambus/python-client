"""Tests for persona VM, browser profile and OAuth app admin methods."""

import pytest

VM = "11111111-1111-1111-1111-111111111111"
PERSONA = "22222222-2222-2222-2222-222222222222"
PROFILE = "33333333-3333-3333-3333-333333333333"
GROUP = "44444444-4444-4444-4444-444444444444"

CASES = [
    ("list_persona_vms", (), {}, "GET", "vms/persona", None, None),
    ("list_vm_sessions", (), {}, "GET", "admin/vms/sessions", None, None),
    (
        "drop_vm_session",
        ("ops@example.com",),
        {},
        "DELETE",
        "admin/vms/sessions/ops%40example.com",
        None,
        None,
    ),
    ("get_vm_capacity", (), {}, "GET", "admin/vms/capacity", None, None),
    ("list_admin_vms", (), {}, "GET", "admin/vms", None, None),
    ("create_vm", ("alice",), {}, "POST", "admin/vms", {"slug": "alice"}, None),
    (
        "create_vm",
        ("alice",),
        {"persona_id": PERSONA, "node": "pve1"},
        "POST",
        "admin/vms",
        {"slug": "alice", "persona_id": PERSONA, "node": "pve1"},
        None,
    ),
    ("update_vm", (VM,), {"name": "new"}, "PATCH", f"admin/vms/{VM}", {"name": "new"}, None),
    (
        "update_vm",
        (VM,),
        {"persona_id": PERSONA},
        "PATCH",
        f"admin/vms/{VM}",
        {"persona_id": PERSONA},
        None,
    ),
    (
        "update_vm",
        (VM,),
        {"clear_persona": True},
        "PATCH",
        f"admin/vms/{VM}",
        {"persona_id": None},
        None,
    ),
    ("delete_vm", (VM,), {}, "DELETE", f"admin/vms/{VM}", None, None),
    ("release_vm", (VM,), {}, "POST", f"admin/vms/{VM}/release", None, None),
    ("maintain_vm", (VM,), {}, "POST", f"admin/vms/{VM}/maintain", None, None),
    ("apply_vm_retention", (VM,), {}, "POST", f"admin/vms/{VM}/retention", None, None),
    ("list_browser_profiles", (), {}, "GET", "browser-profiles", None, {}),
    (
        "list_browser_profiles",
        (),
        {"persona_id": PERSONA},
        "GET",
        "browser-profiles",
        None,
        {"persona_id": PERSONA},
    ),
    ("get_browser_profile", (PROFILE,), {}, "GET", f"browser-profiles/{PROFILE}", None, None),
    (
        "list_browser_profile_egresses",
        (),
        {},
        "GET",
        "admin/browser-profiles/egresses",
        None,
        None,
    ),
    (
        "create_browser_profile",
        ("Shopper", "uk-1"),
        {},
        "POST",
        "admin/browser-profiles",
        {"name": "Shopper", "egress": "uk-1"},
        None,
    ),
    (
        "create_browser_profile",
        ("Shopper", "uk-1"),
        {
            "description": "d",
            "persona_id": PERSONA,
            "user_agent": "ua",
            "locale": "en-GB",
            "timezone": "Europe/London",
        },
        "POST",
        "admin/browser-profiles",
        {
            "name": "Shopper",
            "egress": "uk-1",
            "description": "d",
            "persona_id": PERSONA,
            "user_agent": "ua",
            "locale": "en-GB",
            "timezone": "Europe/London",
        },
        None,
    ),
    (
        "update_browser_profile",
        (PROFILE,),
        {"locale": "", "egress": "us-1"},
        "PATCH",
        f"admin/browser-profiles/{PROFILE}",
        {"locale": "", "egress": "us-1"},
        None,
    ),
    (
        "update_browser_profile",
        (PROFILE,),
        {"clear_persona": True},
        "PATCH",
        f"admin/browser-profiles/{PROFILE}",
        {"persona_id": None},
        None,
    ),
    (
        "delete_browser_profile",
        (PROFILE,),
        {},
        "DELETE",
        f"admin/browser-profiles/{PROFILE}",
        None,
        None,
    ),
    (
        "force_release_browser_profile",
        (PROFILE,),
        {},
        "POST",
        f"admin/browser-profiles/{PROFILE}/force-release",
        None,
        None,
    ),
    (
        "wipe_browser_profile",
        (PROFILE,),
        {},
        "POST",
        f"admin/browser-profiles/{PROFILE}/wipe",
        None,
        None,
    ),
    ("list_oauth_apps", (), {}, "GET", "admin/oauth-apps", None, None),
    (
        "create_oauth_app",
        ("Tool", "https://tool.example/cb"),
        {},
        "POST",
        "admin/oauth-apps",
        {
            "name": "Tool",
            "callback_url": "https://tool.example/cb",
            "scopes": "",
            "public": False,
            "enabled": True,
            "allowed_group_ids": [],
        },
        None,
    ),
    (
        "create_oauth_app",
        ("Tool", "https://tool.example/cb"),
        {"scopes": "openid", "public": True, "enabled": False, "allowed_group_ids": [GROUP]},
        "POST",
        "admin/oauth-apps",
        {
            "name": "Tool",
            "callback_url": "https://tool.example/cb",
            "scopes": "openid",
            "public": True,
            "enabled": False,
            "allowed_group_ids": [GROUP],
        },
        None,
    ),
    (
        "update_oauth_app",
        ("abc123",),
        {
            "name": "Tool",
            "callback_url": "https://tool.example/cb",
            "scopes": "openid email",
            "enabled": True,
            "allowed_group_ids": [GROUP],
        },
        "PUT",
        "admin/oauth-apps/abc123",
        {
            "name": "Tool",
            "callback_url": "https://tool.example/cb",
            "scopes": "openid email",
            "enabled": True,
            "allowed_group_ids": [GROUP],
        },
        None,
    ),
    (
        "rotate_oauth_app_secret",
        ("abc123",),
        {},
        "POST",
        "admin/oauth-apps/abc123/rotate-secret",
        None,
        None,
    ),
    ("delete_oauth_app", ("abc123",), {}, "DELETE", "admin/oauth-apps/abc123", None, None),
]


@pytest.mark.parametrize("name,args,kwargs,method,path,body,params", CASES)
def test_admin_infra_request(client, mock_response, name, args, kwargs, method, path, body, params):
    mock_response.json.return_value = {"ok": True}
    client.session.request.return_value = mock_response

    result = getattr(client, name)(*args, **kwargs)

    call = client.session.request.call_args.kwargs
    assert call["method"] == method
    assert call["url"] == f"{client.api_url}/{path}"
    assert call["json"] == body
    assert call["params"] == params
    assert result == {"ok": True}


def test_no_content_returns_empty_dict(client, mock_response):
    mock_response.status_code = 204
    client.session.request.return_value = mock_response

    assert client.wipe_browser_profile(PROFILE) == {}
