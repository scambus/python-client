"""Admin methods for persona VMs, browser profiles and OAuth apps."""

from typing import Any, Dict, List, Optional
from urllib.parse import quote


def _set_fields(**fields: Any) -> Dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


class AdminInfraMixin:
    """Infrastructure administration for ScambusClient."""

    def list_persona_vms(self) -> List[Dict[str, Any]]:
        """List the persona VMs whose persona the caller may view."""
        return self._request("GET", "/vms/persona")

    def list_vm_sessions(self) -> List[Dict[str, Any]]:
        """List the VM dispenser's embed sessions with the SCAMBUS user of each."""
        return self._request("GET", "/admin/vms/sessions")

    def drop_vm_session(self, user_id: str) -> Dict[str, Any]:
        """Delete a user's embed session and its VM on the dispenser."""
        return self._request("DELETE", f"/admin/vms/sessions/{quote(user_id, safe='')}")

    def get_vm_capacity(self) -> Dict[str, Any]:
        """Get the running and maximum VM counts for each dispenser node."""
        return self._request("GET", "/admin/vms/capacity")

    def list_admin_vms(self) -> Dict[str, Any]:
        """List every persona VM with its live Proxmox status and the orphans on each side."""
        return self._request("GET", "/admin/vms")

    def create_vm(
        self, slug: str, persona_id: Optional[str] = None, node: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clone a new persona VM and register it as suspended."""
        body = _set_fields(slug=slug, persona_id=persona_id, node=node)
        return self._request("POST", "/admin/vms", json_data=body)

    def update_vm(
        self,
        vm_id: str,
        name: Optional[str] = None,
        persona_id: Optional[str] = None,
        clear_persona: bool = False,
    ) -> Dict[str, Any]:
        """Rename an unleased persona VM or change its persona."""
        body = _set_fields(name=name, persona_id=persona_id)
        if clear_persona:
            body["persona_id"] = None
        return self._request("PATCH", f"/admin/vms/{vm_id}", json_data=body)

    def delete_vm(self, vm_id: str) -> Dict[str, Any]:
        """Delete a suspended or failed persona VM from Proxmox and the registry."""
        return self._request("DELETE", f"/admin/vms/{vm_id}")

    def release_vm(self, vm_id: str) -> Dict[str, Any]:
        """Force-release a persona VM lease, or recover a VM in error."""
        return self._request("POST", f"/admin/vms/{vm_id}/release")

    def maintain_vm(self, vm_id: str) -> Dict[str, Any]:
        """Lease a persona VM to the caller for maintenance and return its embed URL."""
        return self._request("POST", f"/admin/vms/{vm_id}/maintain")

    def apply_vm_retention(self, vm_id: str) -> Dict[str, Any]:
        """Prune a persona VM's snapshots and return the deleted snapshot ids."""
        return self._request("POST", f"/admin/vms/{vm_id}/retention")

    def list_browser_profiles(self, persona_id: Optional[str] = None) -> Dict[str, Any]:
        """List the browser profiles of the caller's orgs, optionally of one persona."""
        return self._request("GET", "/browser-profiles", params=_set_fields(persona_id=persona_id))

    def get_browser_profile(self, profile_id: str) -> Dict[str, Any]:
        """Get one browser profile and, while it is leased, its live browser status."""
        return self._request("GET", f"/browser-profiles/{profile_id}")

    def list_browser_profile_egresses(self) -> Any:
        """List the egresses that the research browser offers for a profile."""
        return self._request("GET", "/admin/browser-profiles/egresses")

    def create_browser_profile(
        self,
        name: str,
        egress: str,
        description: Optional[str] = None,
        persona_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        locale: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a browser profile, owned by its persona's org or else by the caller's org."""
        body = _set_fields(
            name=name,
            egress=egress,
            description=description,
            persona_id=persona_id,
            user_agent=user_agent,
            locale=locale,
            timezone=timezone,
        )
        return self._request("POST", "/admin/browser-profiles", json_data=body)

    def update_browser_profile(
        self,
        profile_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        persona_id: Optional[str] = None,
        egress: Optional[str] = None,
        user_agent: Optional[str] = None,
        locale: Optional[str] = None,
        timezone: Optional[str] = None,
        clear_persona: bool = False,
    ) -> Dict[str, Any]:
        """Change the given fields of a browser profile; an empty string clears a text field."""
        body = _set_fields(
            name=name,
            description=description,
            persona_id=persona_id,
            egress=egress,
            user_agent=user_agent,
            locale=locale,
            timezone=timezone,
        )
        if clear_persona:
            body["persona_id"] = None
        return self._request("PATCH", f"/admin/browser-profiles/{profile_id}", json_data=body)

    def delete_browser_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete an unleased browser profile and its data on the research browser."""
        return self._request("DELETE", f"/admin/browser-profiles/{profile_id}")

    def force_release_browser_profile(self, profile_id: str) -> Dict[str, Any]:
        """End any lease on a browser profile."""
        return self._request("POST", f"/admin/browser-profiles/{profile_id}/force-release")

    def wipe_browser_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete the browser data of an unleased browser profile."""
        return self._request("POST", f"/admin/browser-profiles/{profile_id}/wipe")

    def list_oauth_apps(self) -> Dict[str, Any]:
        """List every OAuth app with its SCAMBUS access policy."""
        return self._request("GET", "/admin/oauth-apps")

    def create_oauth_app(
        self,
        name: str,
        callback_url: str,
        scopes: str = "",
        public: bool = False,
        enabled: bool = True,
        allowed_group_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create an OAuth app; the response holds a client secret that is shown only once."""
        body = {
            "name": name,
            "callback_url": callback_url,
            "scopes": scopes,
            "public": public,
            "enabled": enabled,
            "allowed_group_ids": allowed_group_ids or [],
        }
        return self._request("POST", "/admin/oauth-apps", json_data=body)

    def update_oauth_app(
        self,
        client_id: str,
        name: str,
        callback_url: str,
        scopes: str,
        enabled: bool,
        allowed_group_ids: List[str],
    ) -> Dict[str, Any]:
        """Replace every setting of an OAuth app; the server reads a missing field as empty."""
        body = {
            "name": name,
            "callback_url": callback_url,
            "scopes": scopes,
            "enabled": enabled,
            "allowed_group_ids": allowed_group_ids,
        }
        return self._request("PUT", f"/admin/oauth-apps/{client_id}", json_data=body)

    def rotate_oauth_app_secret(self, client_id: str) -> Dict[str, Any]:
        """Replace an OAuth app's client secret; the response holds the new secret only once."""
        return self._request("POST", f"/admin/oauth-apps/{client_id}/rotate-secret")

    def delete_oauth_app(self, client_id: str) -> Dict[str, Any]:
        """Delete an OAuth app and its SCAMBUS access policy."""
        return self._request("DELETE", f"/admin/oauth-apps/{client_id}")
