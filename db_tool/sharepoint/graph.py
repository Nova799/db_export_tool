"""SharePoint integration via Microsoft Graph API."""

import os
import requests


class SharePointError(Exception):
    pass


class GraphSharePointClient:
    """Client for SharePoint using Microsoft Graph (app registration / client credentials)."""

    def __init__(self, site_url, drive_id=None, folder_path="/",
                 tenant_id=None, client_id=None, client_secret=None):
        self.site_url = site_url.rstrip("/")
        self.drive_id = drive_id
        self.folder_path = folder_path.strip("/") 
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None

    def _token_url(self):
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

    def authenticate(self):
        if not (self.tenant_id and self.client_id and self.client_secret):
            raise SharePointError("Informations d'authentification manquantes (tenant/client/secret).")
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        r = requests.post(self._token_url(), data=data, timeout=30)
        if r.status_code != 200:
            raise SharePointError(f"Échec authentification : {r.status_code} {r.text}")
        self._token = r.json().get("access_token")
        if not self._token:
            raise SharePointError("Token d'accès absent dans la réponse.")
        return self._token

    def _headers(self):
        if not self._token:
            self.authenticate()
        return {"Authorization": f"Bearer {self._token}"}

    def _resolve_drive_id(self):
        if self.drive_id:
            return self.drive_id
        # Resolve from site URL: https://tenant.sharepoint.com/sites/SiteName
        # Use Graph: GET /sites/{hostname}:/{path}
        from urllib.parse import urlparse
        u = urlparse(self.site_url)
        hostname = u.netloc
        path = u.path.strip("/")
        if path:
            url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{path}"
        else:
            url = f"https://graph.microsoft.com/v1.0/sites/{hostname}"
        r = requests.get(url, headers=self._headers(), timeout=30)
        if r.status_code != 200:
            raise SharePointError(f"Impossible de résoudre le site : {r.status_code} {r.text}")
        site_id = r.json().get("id")
        # default drive
        r2 = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive", headers=self._headers(), timeout=30)
        if r2.status_code != 200:
            raise SharePointError(f"Impossible de récupérer le drive : {r2.status_code} {r2.text}")
        self.drive_id = r2.json().get("id")
        return self.drive_id

    def test(self):
        try:
            self.authenticate()
            did = self._resolve_drive_id()
            r = requests.get(f"https://graph.microsoft.com/v1.0/drives/{did}/root", headers=self._headers(), timeout=30)
            if r.status_code == 200:
                return True, "Connexion SharePoint réussie"
            return False, f"Erreur drive : {r.status_code} {r.text}"
        except Exception as e:
            return False, str(e)

    def upload_file(self, local_path, filename=None):
        """Upload a local file to the configured folder. Returns webUrl or None."""
        if filename is None:
            filename = os.path.basename(local_path)
        drive_id = self._resolve_drive_id()
        folder = self.folder_path.strip("/")
        if folder:
            remote_path = f"{folder}/{filename}"
        else:
            remote_path = filename
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{remote_path}:/content"
        with open(local_path, "rb") as f:
            r = requests.put(url, headers=self._headers(), data=f, timeout=120)
        if r.status_code not in (200, 201):
            raise SharePointError(f"Échec upload : {r.status_code} {r.text}")
        return r.json().get("webUrl")


def build_client(folder_row, client_secret_plain=None):
    """Build a GraphSharePointClient from a DB row (dict)."""
    secret = client_secret_plain
    if secret is None:
        # cannot recover hashed secret; caller must pass plain
        secret = None
    return GraphSharePointClient(
        site_url=folder_row.get("site_url", ""),
        drive_id=folder_row.get("drive_id"),
        folder_path=folder_row.get("folder_path", "/"),
        tenant_id=folder_row.get("tenant_id"),
        client_id=folder_row.get("client_id"),
        client_secret=secret,
    )
