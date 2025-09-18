import os
import json
import re
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any, Optional, Tuple
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsClient:
    """
    A client for interacting with Google Sheets API.

    Supports both OAuth2 and service account authentication methods.
    """

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def __init__(self):
        """
        Initialize the Google Sheets client.

        Authentication is attempted in the following order:
        1. Service account credentials from GOOGLE_SERVICE_ACCOUNT_JSON env var or file
        2. OAuth2 credentials with token refresh
        """
        self.service = None
        self.service_account_email = None
        print("Starting GoogleSheetsClient initialization...")
        try:
            self._authenticate()
            print("GoogleSheetsClient authentication completed successfully")
            if self.service_account_email:
                print(f"Service Account Email: {self.service_account_email}")
                print("IMPORTANT: Make sure this email has access to your Google Sheet!")
        except Exception as e:
            print(f"GoogleSheetsClient initialization failed: {e}")
            raise

    def _authenticate(self):
        """
        Authenticate with Google Sheets API using available credentials.
        """
        creds = None

        # Try service account authentication first
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        print(f"service_account_json = {service_account_json}")
        if service_account_json:
            try:
                creds = ServiceAccountCredentials.from_service_account_file(
                    service_account_json, scopes=self.SCOPES
                )
                # Extract the service account email for display
                with open(service_account_json, 'r') as f:
                    service_data = json.load(f)
                    self.service_account_email = service_data.get('client_email')
            except Exception as e:
                print(f"Service account authentication failed: {e}")

        if not creds:
            raise ValueError(
                "No valid authentication method found. Please set up :\n"
                "Service account: Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable\n"
            )

        try:
            self.service = build('sheets', 'v4', credentials=creds)
        except Exception as e:
            raise ValueError(f"Failed to build Google Sheets service: {e}")

    def parse_sheets_url(self, url: str) -> Tuple[str, Optional[str]]:
        """
        Parse a Google Sheets URL to extract spreadsheet ID and sheet GID.
        
        Args:
            url: Google Sheets URL (e.g., https://docs.google.com/spreadsheets/d/ID/edit#gid=123)
            
        Returns:
            Tuple of (spreadsheet_id, sheet_gid) where sheet_gid may be None
            
        Raises:
            ValueError: If URL format is invalid
        """
        # Extract spreadsheet ID using regex
        spreadsheet_pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(spreadsheet_pattern, url)
        
        if not match:
            raise ValueError(f"Invalid Google Sheets URL. Cannot extract spreadsheet ID from: {url}")
        
        spreadsheet_id = match.group(1)
        
        # Extract sheet GID from URL fragment (after #)
        sheet_gid = None
        if '#gid=' in url:
            gid_match = re.search(r'#gid=(\d+)', url)
            if gid_match:
                sheet_gid = gid_match.group(1)
        
        return spreadsheet_id, sheet_gid

    def get_sheet_name_from_gid(self, spreadsheet_id: str, sheet_gid: str) -> Optional[str]:
        """
        Get sheet name from sheet GID using Google Sheets API.
        
        Args:
            spreadsheet_id: The spreadsheet ID
            sheet_gid: The sheet GID (numeric ID)
            
        Returns:
            Sheet name or None if not found
        """
        try:
            # Get spreadsheet metadata
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            # Find sheet with matching GID
            for sheet in spreadsheet.get('sheets', []):
                sheet_props = sheet.get('properties', {})
                if str(sheet_props.get('sheetId', '')) == str(sheet_gid):
                    return sheet_props.get('title')
            
            return None
            
        except HttpError as e:
            print(f"Error getting sheet name from GID: {e}")
            return None

    def extract_sheet_data_from_url(
            self,
            url: str,
            range_name: str = "A:Z"
    ) -> Dict[str, Any]:
        """
        Extract data from a Google Sheet using a complete URL (including specific sheet tab).
        
        Args:
            url: Complete Google Sheets URL with sheet tab (e.g., https://docs.google.com/spreadsheets/d/ID/edit#gid=123)
            range_name: Cell range to extract (default: "A:Z")
            
        Returns:
            Dictionary containing extracted data with headers, rows, and metadata
            
        Examples:
            # Extract data from specific sheet tab via URL
            extract_sheet_data_from_url("https://docs.google.com/spreadsheets/d/1S7-Uryb.../edit#gid=123456")
        """
        try:
            # Parse the URL to get spreadsheet ID and sheet GID
            spreadsheet_id, sheet_gid = self.parse_sheets_url(url)
            print(f"Extracted spreadsheet ID: {spreadsheet_id}")
            print(f"Extracted sheet GID: {sheet_gid}")
            
            # Get sheet name from GID if available
            sheet_name = None
            if sheet_gid:
                sheet_name = self.get_sheet_name_from_gid(spreadsheet_id, sheet_gid)
                print(f"Sheet name for GID {sheet_gid}: {sheet_name}")
            
            # Use existing extract_sheet_data method
            return self.extract_sheet_data(spreadsheet_id, range_name, sheet_name)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to extract data from URL: {str(e)}"
            }


    def extract_sheet_data(
            self,
            spreadsheet_id: str,
            range_name: str = "A:Z",
            sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract data from a Google Sheet.

        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The range to extract (default: "A:Z")
            sheet_name: Optional sheet name. If provided, will be prepended to range

        Returns:
            Dictionary containing the extracted data and metadata

        Raises:
            ValueError: If the spreadsheet cannot be accessed
            HttpError: If there's an API error
        """
        if not self.service:
            raise ValueError("Google Sheets service not initialized")

        try:
            # Construct the full range if sheet name is provided
            full_range = f"{sheet_name}!{range_name}" if sheet_name else range_name

            # Get the spreadsheet metadata
            print("Making API call to get spreadsheet metadata...")
            spreadsheet_request = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id)
            spreadsheet = spreadsheet_request.execute()

            # Get the data
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=full_range,
                valueRenderOption='FORMATTED_VALUE',
                dateTimeRenderOption='FORMATTED_STRING'
            ).execute()

            values = result.get('values', [])

            return {
                "success": True,
                "spreadsheet_title": spreadsheet.get('properties', {}).get('title', 'Unknown'),
                "sheet_name": sheet_name or "Default",
                "range": full_range,
                "data": values
            }

        except HttpError as error:
            error_details = error.error_details[0] if error.error_details else {}
            error_message = error_details.get('message', str(error))
            
            # Provide specific help for permission errors
            if error.resp.status == 403:
                permission_help = (
                    f"\n\nPERMISSION FIX NEEDED:\n"
                    f"The service account doesn't have access to this Google Sheet.\n"
                    f"Service Account Email: {self.service_account_email or 'Unknown'}\n\n"
                    f"To fix this:\n"
                    f"1. Open your Google Sheet in a browser\n"
                    f"2. Click 'Share' (top right)\n"
                    f"3. Add this email: {self.service_account_email or 'Check your google.json file for client_email'}\n"
                    f"4. Give it at least 'Viewer' permission\n"
                    f"5. Click 'Send'"
                )
                error_message += permission_help
            
            return {
                "success": False,
                "error": f"HTTP Error {error.resp.status}: {error_message}",
                "error_code": error.resp.status
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_sheet_info(self, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Get basic information about a Google Sheet.

        Args:
            spreadsheet_id: The ID of the Google Sheet

        Returns:
            Dictionary containing sheet metadata
        """
        if not self.service:
            raise ValueError("Google Sheets service not initialized")

        try:
            print(f"Getting spreadsheet info for ID: {spreadsheet_id}")
            print(f"Service object type: {type(self.service)}")
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            sheets_info = []
            for sheet in spreadsheet.get('sheets', []):
                sheet_props = sheet.get('properties', {})
                sheets_info.append({
                    'sheet_id': sheet_props.get('sheetId'),
                    'title': sheet_props.get('title'),
                    'index': sheet_props.get('index'),
                    'sheet_type': sheet_props.get('sheetType'),
                    'row_count': sheet_props.get('gridProperties', {}).get('rowCount'),
                    'column_count': sheet_props.get('gridProperties', {}).get('columnCount')
                })

            return {
                "success": True,
                "spreadsheet_id": spreadsheet.get('spreadsheetId'),
                "title": spreadsheet.get('properties', {}).get('title'),
                "locale": spreadsheet.get('properties', {}).get('locale'),
                "sheets": sheets_info
            }

        except HttpError as error:
            error_details = error.error_details[0] if error.error_details else {}
            return {
                "success": False,
                "error": f"HTTP Error {error.resp.status}: {error_details.get('message', str(error))}",
                "error_code": error.resp.status
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
