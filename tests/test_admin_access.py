"""Tests for the user and access admin methods."""

from unittest.mock import Mock

import pytest

API = "https://api.test.scambus.net/api"


def _respond(client, *bodies):
    responses = []
    for body in bodies:
        response = Mock()
        response.status_code = 200
        response.json.return_value = body
        responses.append(response)
    client.session.request.side_effect = responses


def _call(client, index=0):
    kwargs = client.session.request.call_args_list[index].kwargs
    return kwargs["method"], kwargs["url"], kwargs["json"], kwargs["params"]


CASES = [
    (lambda c: c.list_users(), "GET", "/users", None, None),
    (
        lambda c: c.list_users(active=False, org_id="org-1"),
        "GET",
        "/users",
        None,
        {"active": "false", "orgId": "org-1"},
    ),
    (lambda c: c.get_user("u-1"), "GET", "/users/u-1", None, None),
    (lambda c: c.list_clerk_users(), "GET", "/clerk/users", None, None),
    (
        lambda c: c.list_clerk_users(search="ann", organization_id="org_1", limit=10, offset=20),
        "GET",
        "/clerk/users",
        None,
        {"search": "ann", "organizationId": "org_1", "limit": 10, "offset": 20},
    ),
    (lambda c: c.get_clerk_user("user_1"), "GET", "/clerk/users/user_1", None, None),
    (
        lambda c: c.set_clerk_user_status("user_1", False),
        "PUT",
        "/clerk/users/user_1/status",
        {"active": False},
        None,
    ),
    (
        lambda c: c.set_clerk_user_role("user_1", "admin"),
        "PUT",
        "/clerk/users/user_1/role",
        {"role": "admin"},
        None,
    ),
    (
        lambda c: c.sync_clerk_user_profile("user_1"),
        "POST",
        "/clerk/users/user_1/sync-profile",
        None,
        None,
    ),
    (lambda c: c.delete_clerk_user("user_1"), "DELETE", "/clerk/users/user_1", None, None),
    (lambda c: c.list_all_sessions(), "GET", "/sessions/all", None, None),
    (
        lambda c: c.list_all_sessions(user_id="u-1", user_type="internal", revoked=True),
        "GET",
        "/sessions/all",
        None,
        {"user_id": "u-1", "user_type": "internal", "revoked": "true"},
    ),
    (
        lambda c: c.revoke_all_user_sessions("u-1"),
        "POST",
        "/sessions/users/u-1/revoke-all",
        None,
        None,
    ),
    (
        lambda c: c.revoke_all_user_sessions("u-1", reason="left"),
        "POST",
        "/sessions/users/u-1/revoke-all",
        {"reason": "left"},
        None,
    ),
    (lambda c: c.list_organizations(), "GET", "/clerk/organizations", None, None),
    (
        lambda c: c.list_organizations(include_system=True),
        "GET",
        "/clerk/organizations",
        None,
        {"include_system": "true"},
    ),
    (lambda c: c.get_organization("org_1"), "GET", "/clerk/organizations/org_1", None, None),
    (
        lambda c: c.list_organization_groups("org_1"),
        "GET",
        "/clerk/organizations/org_1/groups",
        None,
        None,
    ),
    (
        lambda c: c.create_personal_invitation("a@example.com"),
        "POST",
        "/clerk/invitations",
        {"emailAddress": "a@example.com"},
        None,
    ),
    (
        lambda c: c.create_organization_invitation("org_1", "a@example.com"),
        "POST",
        "/clerk/organizations/org_1/invitations",
        {"emailAddress": "a@example.com"},
        None,
    ),
    (
        lambda c: c.create_organization_invitation("org_1", "a@example.com", role="org:admin"),
        "POST",
        "/clerk/organizations/org_1/invitations",
        {"emailAddress": "a@example.com", "role": "org:admin"},
        None,
    ),
    (
        lambda c: c.list_organization_invitations("org_1"),
        "GET",
        "/clerk/organizations/org_1/invitations",
        None,
        None,
    ),
    (
        lambda c: c.get_organization_invitation("org_1", "inv_1"),
        "GET",
        "/clerk/organizations/org_1/invitations/inv_1",
        None,
        None,
    ),
    (
        lambda c: c.revoke_organization_invitation("org_1", "inv_1"),
        "POST",
        "/clerk/organizations/org_1/invitations/inv_1/revoke",
        None,
        None,
    ),
    (lambda c: c.list_groups(), "GET", "/groups", None, None),
    (
        lambda c: c.list_groups(page=2, page_size=50),
        "GET",
        "/groups",
        None,
        {"page": 2, "page_size": 50},
    ),
    (lambda c: c.get_group("g-1"), "GET", "/groups/g-1", None, None),
    (lambda c: c.create_group("Analysts"), "POST", "/groups", {"name": "Analysts"}, None),
    (
        lambda c: c.create_group(
            "Analysts",
            description="Desk",
            permissions=["case.view"],
            badge_type="staff_member",
            protect_display_names=True,
            default_route="/cases",
            priority=5,
        ),
        "POST",
        "/groups",
        {
            "name": "Analysts",
            "description": "Desk",
            "permissions": ["case.view"],
            "badge_type": "staff_member",
            "protect_display_names": True,
            "default_route": "/cases",
            "priority": 5,
        },
        None,
    ),
    (lambda c: c.delete_group("g-1"), "DELETE", "/groups/g-1", None, None),
    (
        lambda c: c.set_group_members("g-1", ["u-1", "u-2"], []),
        "PUT",
        "/groups/g-1/members",
        {"user_ids": ["u-1", "u-2"], "automation_ids": []},
        None,
    ),
    (
        lambda c: c.add_group_user("g-1", "u-1"),
        "POST",
        "/groups/g-1/users",
        {"user_id": "u-1"},
        None,
    ),
    (lambda c: c.remove_group_user("g-1", "u-1"), "DELETE", "/groups/g-1/users/u-1", None, None),
    (
        lambda c: c.add_group_automation("g-1", "a-1"),
        "POST",
        "/groups/g-1/automations",
        {"automation_id": "a-1"},
        None,
    ),
    (
        lambda c: c.remove_group_automation("g-1", "a-1"),
        "DELETE",
        "/groups/g-1/automations/a-1",
        None,
        None,
    ),
    (lambda c: c.list_permissions(), "GET", "/permissions", None, None),
    (
        lambda c: c.list_org_user_permissions("o-1"),
        "GET",
        "/orgs/o-1/user-permissions",
        None,
        None,
    ),
    (
        lambda c: c.list_user_permissions("o-1", "u-1"),
        "GET",
        "/orgs/o-1/users/u-1/permissions",
        None,
        None,
    ),
    (
        lambda c: c.grant_user_permission("o-1", "u-1", "case.view"),
        "POST",
        "/orgs/o-1/users/u-1/permissions",
        {"permission": "case.view"},
        None,
    ),
    (
        lambda c: c.grant_user_permission(
            "o-1",
            "u-1",
            "stream.view",
            resource_type="stream",
            resource_id="s-1",
            expires_at="2027-01-01T00:00:00Z",
        ),
        "POST",
        "/orgs/o-1/users/u-1/permissions",
        {
            "permission": "stream.view",
            "resourceType": "stream",
            "resourceId": "s-1",
            "expiresAt": "2027-01-01T00:00:00Z",
        },
        None,
    ),
    (lambda c: c.revoke_user_permission("p-1"), "DELETE", "/user-permissions/p-1", None, None),
    (
        lambda c: c.list_available_org_permissions(),
        "GET",
        "/org-permissions/available",
        None,
        None,
    ),
    (lambda c: c.list_org_permissions(), "GET", "/org-permissions", None, None),
    (lambda c: c.list_org_permissions("o-1"), "GET", "/org-permissions/org/o-1", None, None),
    (
        lambda c: c.grant_org_permission("o-1", "org.view_all_orgs"),
        "POST",
        "/org-permissions",
        {"orgId": "o-1", "permission": "org.view_all_orgs"},
        None,
    ),
    (
        lambda c: c.grant_org_permission(
            "o-1", "org.view_specific_org", resource_type="organization", resource_id="o-2"
        ),
        "POST",
        "/org-permissions",
        {
            "orgId": "o-1",
            "permission": "org.view_specific_org",
            "resourceType": "organization",
            "resourceId": "o-2",
        },
        None,
    ),
    (lambda c: c.revoke_org_permission("p-1"), "DELETE", "/org-permissions/p-1", None, None),
]


@pytest.mark.parametrize("call, method, path, body, params", CASES)
def test_request_shape(client, call, method, path, body, params):
    _respond(client, {"ok": True})

    result = call(client)

    assert _call(client) == (method, f"{API}{path}", body, params)
    assert result == {"ok": True}


def test_update_organization_keeps_settings_given_as_none(client):
    _respond(
        client,
        {
            "local_description": "Bank fraud desk",
            "local_contact_email": "desk@example.com",
            "local_default_group_ids": ["g-1"],
        },
        {"success": True, "orgId": "o-1"},
    )

    result = client.update_organization("org_1", allow_signups=False)

    assert _call(client, 0) == ("GET", f"{API}/clerk/organizations/org_1", None, None)
    assert _call(client, 1) == (
        "PUT",
        f"{API}/clerk/organizations/org_1",
        {
            "description": "Bank fraud desk",
            "contactEmail": "desk@example.com",
            "defaultGroupIds": ["g-1"],
            "allowSignups": False,
        },
        None,
    )
    assert result == {"success": True, "orgId": "o-1"}


def test_update_organization_sends_every_given_setting(client):
    _respond(client, {}, {"success": True})

    client.update_organization(
        "org_1",
        description="",
        contact_email="new@example.com",
        default_group_ids=[],
        active=True,
        allow_signups=True,
        require_journal_signing=True,
        require_passkeys=False,
    )

    assert _call(client, 1)[2] == {
        "description": "",
        "contactEmail": "new@example.com",
        "defaultGroupIds": [],
        "active": True,
        "allowSignups": True,
        "requireJournalSigning": True,
        "requirePasskeys": False,
    }


def test_update_organization_without_local_row_sends_empty_settings(client):
    _respond(client, {"id": "org_1"}, {"success": True})

    client.update_organization("org_1")

    assert _call(client, 1)[2] == {"description": "", "contactEmail": "", "defaultGroupIds": []}


def test_update_group_keeps_settings_given_as_none(client):
    _respond(
        client,
        {"name": "Analysts", "description": "Desk", "permissions": ["case.view", "tag.view"]},
        {"id": "g-1"},
    )

    result = client.update_group("g-1", priority=3)

    assert _call(client, 0) == ("GET", f"{API}/groups/g-1", None, None)
    assert _call(client, 1) == (
        "PUT",
        f"{API}/groups/g-1",
        {
            "name": "Analysts",
            "description": "Desk",
            "permissions": ["case.view", "tag.view"],
            "priority": 3,
        },
        None,
    )
    assert result == {"id": "g-1"}


def test_update_group_sends_every_given_setting(client):
    _respond(client, {"name": "Old", "description": "Old", "permissions": ["case.view"]}, {})

    client.update_group(
        "g-1",
        name="New",
        description="",
        permissions=[],
        badge_type="",
        protect_display_names=False,
        default_route="/home",
        priority=0,
    )

    assert _call(client, 1)[2] == {
        "name": "New",
        "description": "",
        "permissions": [],
        "badge_type": "",
        "protect_display_names": False,
        "default_route": "/home",
        "priority": 0,
    }
