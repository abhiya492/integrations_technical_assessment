# hubspot.py

import datetime
import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import urllib.parse
import requests
from typing import List, Dict, Any, Optional

from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# Replace with your HubSpot client credentials
CLIENT_ID = 'cda04b60-7518-4835-aa1a-c50c7fe2bd61'
CLIENT_SECRET = '53064b73-827a-4840-a4e5-6c92cad1df3b'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
AUTHORIZATION_URL = f'https://app.hubspot.com/oauth/authorize'
TOKEN_URL = 'https://api.hubspot.com/oauth/v1/token'

async def authorize_hubspot(user_id: str, org_id: str) -> str:
    """
    Generate an authorization URL for HubSpot OAuth flow.
    
    Args:
        user_id: The ID of the user initiating the OAuth flow
        org_id: The organization ID
        
    Returns:
        str: The authorization URL for HubSpot
    """
    # Generate secure state token with user and org info
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')
    
    # Store state in Redis for verification when callback occurs
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', json.dumps(state_data), expire=600)
    
    # Define OAuth scopes
    scopes = [
        'crm.objects.contacts.read',
        'crm.objects.companies.read',
        'crm.objects.deals.read',
        'content'
    ]
    
    # Construct authorization URL with required parameters
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(scopes),
        'state': encoded_state,
    }
    
    auth_url = f"{AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"
    return auth_url

async def oauth2callback_hubspot(request: Request) -> HTMLResponse:
    """
    Handle the OAuth2 callback from HubSpot.
    
    Args:
        request: The FastAPI request object containing OAuth callback parameters
        
    Returns:
        HTMLResponse: Response to close the OAuth window
    """
    # Check for error in callback
    if request.query_params.get('error'):
        raise HTTPException(
            status_code=400, 
            detail=request.query_params.get('error_description', 'OAuth error')
        )
    
    # Extract parameters from callback
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")
        
    encoded_state = request.query_params.get('state')
    if not encoded_state:
        raise HTTPException(status_code=400, detail="State parameter missing")
    
    # Decode and validate state
    try:
        state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode('utf-8'))
        original_state = state_data.get('state')
        user_id = state_data.get('user_id')
        org_id = state_data.get('org_id')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid state parameter: {str(e)}")
    
    # Verify state from Redis
    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    if not saved_state:
        raise HTTPException(status_code=400, detail="State expired or not found")
    
    if original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail="State validation failed")
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        try:
            response, _ = await asyncio.gather(
                client.post(
                    TOKEN_URL,
                    data={
                        'grant_type': 'authorization_code',
                        'client_id': CLIENT_ID,
                        'client_secret': CLIENT_SECRET,
                        'redirect_uri': REDIRECT_URI,
                        'code': code
                    },
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                ),
                delete_key_redis(f'hubspot_state:{org_id}:{user_id}')
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"HubSpot token error: {response.text}"
                )
                
            token_data = response.json()
            
            # Add expiration timestamp for easier management
            if 'expires_in' in token_data:
                expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=token_data['expires_in'])
                token_data['expires_at'] = expiry_time.timestamp()
            
            # Store credentials in Redis
            await add_key_value_redis(
                f'hubspot_credentials:{org_id}:{user_id}',
                json.dumps(token_data),
                expire=token_data.get('expires_in', 3600)
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")
    
    # Return HTML to close the window
    close_window_script = """
    <html>
        <head>
            <title>Authorization Successful</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
                .success { color: green; font-size: 24px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div class="success">HubSpot Connected Successfully!</div>
            <p>You can close this window now.</p>
            <script>
                setTimeout(function() {
                    window.close();
                }, 2000);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id: str, org_id: str) -> dict:
    """
    Retrieve HubSpot credentials from Redis.
    
    Args:
        user_id: The user ID
        org_id: The organization ID
        
    Returns:
        dict: The HubSpot credentials
    """
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail="HubSpot credentials not found or expired")
    
    credentials_dict = json.loads(credentials)
    
    # Remove credentials from Redis to avoid potential security issues
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')
    
    return credentials_dict

def create_integration_item_from_hubspot_object(item: Dict[Any, Any], item_type: str, parent_id: Optional[str] = None) -> IntegrationItem:
    """
    Convert a HubSpot object to an IntegrationItem.
    
    Args:
        item: The HubSpot object data
        item_type: The type of HubSpot object
        parent_id: Optional parent ID for hierarchical items
        
    Returns:
        IntegrationItem: The converted integration item
    """
    # Extract properties based on item type
    if item_type == "contact":
        name = f"{item.get('properties', {}).get('firstname', '')} {item.get('properties', {}).get('lastname', '')}"
        name = name.strip() or f"Contact {item.get('id', 'Unknown')}"
        creation_time = item.get('properties', {}).get('createdate')
        last_modified = item.get('properties', {}).get('lastmodifieddate')
    elif item_type == "company":
        name = item.get('properties', {}).get('name', f"Company {item.get('id', 'Unknown')}")
        creation_time = item.get('properties', {}).get('createdate')
        last_modified = item.get('properties', {}).get('hs_lastmodifieddate')
    elif item_type == "deal":
        name = item.get('properties', {}).get('dealname', f"Deal {item.get('id', 'Unknown')}")
        creation_time = item.get('properties', {}).get('createdate')
        last_modified = item.get('properties', {}).get('hs_lastmodifieddate')
    else:
        name = f"{item_type.capitalize()} {item.get('id', 'Unknown')}"
        creation_time = None
        last_modified = None
    
    # Parse dates if available
    created_datetime = None
    modified_datetime = None
    
    if creation_time:
        try:
            created_datetime = datetime.datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
            
    if last_modified:
        try:
            modified_datetime = datetime.datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
    
    return IntegrationItem(
        id=str(item.get('id', '')),
        type=item_type,
        name=name,
        parent_id=parent_id,
        creation_time=created_datetime,
        last_modified_time=modified_datetime,
        url=f"https://app.hubspot.com/{item_type}s/{item.get('id')}",
        visibility=True
    )

async def fetch_hubspot_objects(access_token: str, endpoint: str) -> List[Dict[Any, Any]]:
    """
    Fetch objects from HubSpot API with pagination.
    
    Args:
        access_token: The OAuth access token
        endpoint: The API endpoint to call
        
    Returns:
        List[Dict[Any, Any]]: The fetched objects
    """
    all_results = []
    next_after = None
    
    while True:
        url = f"https://api.hubapi.com{endpoint}"
        params = {"limit": 100}
        
        if next_after:
            params["after"] = next_after
            
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"HubSpot API error: {response.text}")
            
        data = response.json()
        results = data.get("results", [])
        all_results.extend(results)
        
        # Check for pagination
        next_after = data.get("paging", {}).get("next", {}).get("after")
        if not next_after:
            break
            
    return all_results

async def get_items_hubspot(credentials: str) -> List[IntegrationItem]:
    """
    Get HubSpot items from the API using OAuth credentials.
    
    Args:
        credentials: JSON string containing OAuth credentials
        
    Returns:
        List[IntegrationItem]: List of integration items from HubSpot
    """
    credentials_dict = json.loads(credentials)
    access_token = credentials_dict.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=400, detail="Invalid HubSpot credentials")
    
    # Define endpoints to fetch
    endpoints = [
        ("/crm/v3/objects/contacts", "contact"),
        ("/crm/v3/objects/companies", "company"),
        ("/crm/v3/objects/deals", "deal")
    ]
    
    all_items = []
    
    try:
        # Create parent categories
        contacts_category = IntegrationItem(
            id="hubspot_contacts_category",
            name="Contacts",
            type="category",
            directory=True
        )
        
        companies_category = IntegrationItem(
            id="hubspot_companies_category",
            name="Companies",
            type="category",
            directory=True
        )
        
        deals_category = IntegrationItem(
            id="hubspot_deals_category",
            name="Deals",
            type="category",
            directory=True
        )
        
        all_items.extend([contacts_category, companies_category, deals_category])
        
        # Fetch different object types
        for endpoint, item_type in endpoints:
            objects = await fetch_hubspot_objects(access_token, endpoint)
            
            parent_id = None
            if item_type == "contact":
                parent_id = "hubspot_contacts_category"
            elif item_type == "company":
                parent_id = "hubspot_companies_category"
            elif item_type == "deal":
                parent_id = "hubspot_deals_category"
            
            for obj in objects:
                integration_item = create_integration_item_from_hubspot_object(obj, item_type, parent_id)
                all_items.append(integration_item)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching HubSpot items: {str(e)}")
    
    print(f"HubSpot items: {all_items}")
    return all_items