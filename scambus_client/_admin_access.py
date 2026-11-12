"""Admin methods for users, organizations, invitations, groups and permissions."""

from typing import Any, Dict, List, Optional


def _without_none(values: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _bool_param(value: Optional[bool]) -> Optional[str]:
    if value is None:
        return None
    return "true" if value else "false"


class AdminAccessMixin:
    """User and access administration for ScambusClient."""

    def list_users(
        self, active: Optional[bool] = None, org_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List local users visible to the caller, optionally filtered by active state and org."""
        params = _without_none({"active": _bool_param(active), "orgId": org_id})
        return self._request("GET", "/users", params=params or None)

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get one local user by UUID."""
        return self._request("GET", f"/users/{user_id}")

    def list_clerk_users(
        self,
        search: Optional[str] = None,
        organization_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List Clerk users with their local sync state, as {users, total, limit, offset}."""
        params = _without_none(
            {
                "search": search,
                "organizationId": organization_id,
                "limit": limit,
                "offset": offset,
            }
        )
        return self._request("GET", "/clerk/users", params=params or None)

    def get_clerk_user(self, clerk_user_id: str) -> Dict[str, Any]:
        """Get one Clerk user and its local sync state by Clerk user ID."""
        return self._request("GET", f"/clerk/users/{clerk_user_id}")

    def set_clerk_user_status(self, clerk_user_id: str, active: bool) -> Dict[str, Any]:
        """Activate or deactivate the local user that belongs to a Clerk user."""
        return self._request(
            "PUT", f"/clerk/users/{clerk_user_id}/status", json_data={"active": active}
        )

    def set_clerk_user_role(self, clerk_user_id: str, role: str) -> Dict[str, Any]:
        """Set the role of a Clerk user to "admin" or "user" through the Admins group."""
        return self._request("PUT", f"/clerk/users/{clerk_user_id}/role", json_data={"role": role})

    def sync_clerk_user_profile(self, clerk_user_id: str) -> Dict[str, Any]:
        """Copy the email, name and image of a Clerk user into the local user."""
        return self._request("POST", f"/clerk/users/{clerk_user_id}/sync-profile")

    def delete_clerk_user(self, clerk_user_id: str) -> Dict[str, Any]:
        """Delete a user from Clerk."""
        return self._request("DELETE", f"/clerk/users/{clerk_user_id}")

    def list_all_sessions(
        self,
        user_id: Optional[str] = None,
        user_type: Optional[str] = None,
        revoked: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """List the sessions of all users, as {sessions, total}."""
        params = _without_none(
            {"user_id": user_id, "user_type": user_type, "revoked": _bool_param(revoked)}
        )
        return self._request("GET", "/sessions/all", params=params or None)

    def revoke_all_user_sessions(
        self, user_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Revoke every session and every device refresh token of a user."""
        body = _without_none({"reason": reason})
        return self._request(
            "POST", f"/sessions/users/{user_id}/revoke-all", json_data=body or None
        )

    def list_organizations(self, include_system: bool = False) -> Dict[str, Any]:
        """List Clerk organizations with their local settings, as {organizations, total}."""
        params = {"include_system": "true"} if include_system else None
        return self._request("GET", "/clerk/organizations", params=params)

    def get_organization(self, clerk_org_id: str) -> Dict[str, Any]:
        """Get one Clerk organization and its local settings by Clerk organization ID."""
        return self._request("GET", f"/clerk/organizations/{clerk_org_id}")

    def update_organization(
        self,
        clerk_org_id: str,
        description: Optional[str] = None,
        contact_email: Optional[str] = None,
        default_group_ids: Optional[List[str]] = None,
        active: Optional[bool] = None,
        allow_signups: Optional[bool] = None,
        require_journal_signing: Optional[bool] = None,
        require_passkeys: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update the local settings of an organization and keep each setting given as None."""
        current = self.get_organization(clerk_org_id)
        body = {
            "description": (
                current.get("local_description", "") if description is None else description
            ),
            "contactEmail": (
                current.get("local_contact_email", "") if contact_email is None else contact_email
            ),
            "defaultGroupIds": (
                current.get("local_default_group_ids") or []
                if default_group_ids is None
                else default_group_ids
            ),
            **_without_none(
                {
                    "active": active,
                    "allowSignups": allow_signups,
                    "requireJournalSigning": require_journal_signing,
                    "requirePasskeys": require_passkeys,
                }
            ),
        }
        return self._request("PUT", f"/clerk/organizations/{clerk_org_id}", json_data=body)

    def list_organization_groups(self, clerk_org_id: str) -> Dict[str, Any]:
        """List the groups that an organization owns, as {groups}."""
        return self._request("GET", f"/clerk/organizations/{clerk_org_id}/groups")

    def create_personal_invitation(self, email_address: str) -> Dict[str, Any]:
        """Invite a person to SCAMBUS without an organization."""
        return self._request(
            "POST", "/clerk/invitations", json_data={"emailAddress": email_address}
        )

    def create_organization_invitation(
        self, clerk_org_id: str, email_address: str, role: Optional[str] = None
    ) -> Dict[str, Any]:
        """Invite a person to an organization; the server role default is "org:member"."""
        body = _without_none({"emailAddress": email_address, "role": role})
        return self._request(
            "POST", f"/clerk/organizations/{clerk_org_id}/invitations", json_data=body
        )

    def list_organization_invitations(self, clerk_org_id: str) -> Dict[str, Any]:
        """List the invitations of an organization, as {invitations, total}."""
        return self._request("GET", f"/clerk/organizations/{clerk_org_id}/invitations")

    def get_organization_invitation(self, clerk_org_id: str, invitation_id: str) -> Dict[str, Any]:
        """Get one invitation of an organization."""
        return self._request(
            "GET", f"/clerk/organizations/{clerk_org_id}/invitations/{invitation_id}"
        )

    def revoke_organization_invitation(
        self, clerk_org_id: str, invitation_id: str
    ) -> Dict[str, Any]:
        """Revoke one invitation of an organization."""
        return self._request(
            "POST", f"/clerk/organizations/{clerk_org_id}/invitations/{invitation_id}/revoke"
        )

    def list_groups(
        self, page: Optional[int] = None, page_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """List permission groups, as {data, pagination}."""
        params = _without_none({"page": page, "page_size": page_size})
        return self._request("GET", "/groups", params=params or None)

    def get_group(self, group_id: str) -> Dict[str, Any]:
        """Get one permission group with its user and automation members."""
        return self._request("GET", f"/groups/{group_id}")

    def create_group(
        self,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        badge_type: Optional[str] = None,
        protect_display_names: Optional[bool] = None,
        default_route: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a permission group owned by the caller's organization."""
        body = _without_none(
            {
                "name": name,
                "description": description,
                "permissions": permissions,
                "badge_type": badge_type,
                "protect_display_names": protect_display_names,
                "default_route": default_route,
                "priority": priority,
            }
        )
        return self._request("POST", "/groups", json_data=body)

    def update_group(
        self,
        group_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        badge_type: Optional[str] = None,
        protect_display_names: Optional[bool] = None,
        default_route: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update a permission group and keep each setting given as None."""
        current = self.get_group(group_id)
        body = {
            "name": current.get("name", "") if name is None else name,
            "description": current.get("description", "") if description is None else description,
            "permissions": (
                current.get("permissions") or [] if permissions is None else permissions
            ),
            **_without_none(
                {
                    "badge_type": badge_type,
                    "protect_display_names": protect_display_names,
                    "default_route": default_route,
                    "priority": priority,
                }
            ),
        }
        return self._request("PUT", f"/groups/{group_id}", json_data=body)

    def delete_group(self, group_id: str) -> Dict[str, Any]:
        """Delete a permission group and all of its memberships."""
        return self._request("DELETE", f"/groups/{group_id}")

    def set_group_members(
        self, group_id: str, user_ids: List[str], automation_ids: List[str]
    ) -> Dict[str, Any]:
        """Replace all user and automation members of a group."""
        return self._request(
            "PUT",
            f"/groups/{group_id}/members",
            json_data={"user_ids": user_ids, "automation_ids": automation_ids},
        )

    def add_group_user(self, group_id: str, user_id: str) -> Dict[str, Any]:
        """Add a user to a group."""
        return self._request("POST", f"/groups/{group_id}/users", json_data={"user_id": user_id})

    def remove_group_user(self, group_id: str, user_id: str) -> Dict[str, Any]:
        """Remove a user from a group."""
        return self._request("DELETE", f"/groups/{group_id}/users/{user_id}")

    def add_group_automation(self, group_id: str, automation_id: str) -> Dict[str, Any]:
        """Add an automation to a group."""
        return self._request(
            "POST", f"/groups/{group_id}/automations", json_data={"automation_id": automation_id}
        )

    def remove_group_automation(self, group_id: str, automation_id: str) -> Dict[str, Any]:
        """Remove an automation from a group."""
        return self._request("DELETE", f"/groups/{group_id}/automations/{automation_id}")

    def list_permissions(self) -> Dict[str, Any]:
        """List the permissions that a group can hold, keyed by category."""
        return self._request("GET", "/permissions")

    def list_org_user_permissions(self, org_id: str) -> List[Dict[str, Any]]:
        """List the direct user permissions in an organization."""
        return self._request("GET", f"/orgs/{org_id}/user-permissions")

    def list_user_permissions(self, org_id: str, user_id: str) -> List[Dict[str, Any]]:
        """List the direct permissions of one user in an organization."""
        return self._request("GET", f"/orgs/{org_id}/users/{user_id}/permissions")

    def grant_user_permission(
        self,
        org_id: str,
        user_id: str,
        permission: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Grant a permission to a user in an organization; expires_at is an RFC 3339 time."""
        body = _without_none(
            {
                "permission": permission,
                "resourceType": resource_type,
                "resourceId": resource_id,
                "expiresAt": expires_at,
            }
        )
        return self._request("POST", f"/orgs/{org_id}/users/{user_id}/permissions", json_data=body)

    def revoke_user_permission(self, permission_id: str) -> Dict[str, Any]:
        """Revoke a direct user permission."""
        return self._request("DELETE", f"/user-permissions/{permission_id}")

    def list_available_org_permissions(self) -> List[Dict[str, Any]]:
        """List the permissions that an organization can hold, with their resource needs."""
        return self._request("GET", "/org-permissions/available")

    def list_org_permissions(self, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List organization permissions, for all organizations or for one."""
        if org_id is None:
            return self._request("GET", "/org-permissions")
        return self._request("GET", f"/org-permissions/org/{org_id}")

    def grant_org_permission(
        self,
        org_id: str,
        permission: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Grant a permission to an organization."""
        body = _without_none(
            {
                "orgId": org_id,
                "permission": permission,
                "resourceType": resource_type,
                "resourceId": resource_id,
            }
        )
        return self._request("POST", "/org-permissions", json_data=body)

    def revoke_org_permission(self, permission_id: str) -> Dict[str, Any]:
        """Revoke an organization permission."""
        return self._request("DELETE", f"/org-permissions/{permission_id}")
