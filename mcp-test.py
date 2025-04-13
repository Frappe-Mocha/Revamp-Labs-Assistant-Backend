import requests
import json
import time
import uuid
import sseclient  # You may need to install this: pip install sseclient-py

def connect_to_mcp_server(url="http://localhost:8931/sse"):
    """Connect to the MCP server and establish a session."""
    print(f"Connecting to MCP server at {url}...")
    
    # Create a unique client ID
    client_id = str(uuid.uuid4())
    
    # Create connection parameters
    params = {
        "clientId": client_id
    }
    
    # Connect to the SSE stream
    headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
    
    response = requests.get(url, params=params, headers=headers, stream=True)
    client = sseclient.SSEClient(response)
    
    # Process initial connection messages
    session_id = None
    for event in client.events():
        data = json.loads(event.data)
        if "sessionId" in data:
            session_id = data["sessionId"]
            print(f"Session established with ID: {session_id}")
            break
    
    if not session_id:
        raise Exception("Failed to establish session with MCP server")
    
    return session_id, client

def send_command(session_id, command, params=None):
    """Send a command to the MCP server."""
    if params is None:
        params = {}
    
    url = f"http://localhost:8931/command"
    
    payload = {
        "sessionId": session_id,
        "id": str(uuid.uuid4()),
        "method": command,
        "params": params
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def main():
    try:
        # Connect to the MCP server and get a session ID
        session_id, client = connect_to_mcp_server()
        
        # Navigate to a website
        print("\nOpening a website...")
        result = send_command(session_id, "browser_navigate", {"url": "https://www.example.com"})
        print(f"Navigation result: {result}")
        
        # Wait for the page to load
        time.sleep(3)
        
        # Take a snapshot of the page
        print("\nTaking a snapshot of the page...")
        snapshot = send_command(session_id, "browser_snapshot")
        print("Snapshot received!")
        
        # Print some information about the page
        if snapshot and 'result' in snapshot:
            page_title = snapshot['result'].get('title', 'No title')
            print(f"Page title: {page_title}")
            
            # Count the number of elements in the snapshot
            elements = snapshot['result'].get('elements', [])
            print(f"Found {len(elements)} elements on the page")
            
            # Display some key elements
            for element in elements[:5]:  # Show first 5 elements
                if 'name' in element and 'attributes' in element:
                    text = element.get('attributes', {}).get('innerText', 'No text')
                    print(f"Element: {element.get('name')} - {text[:50]}...")
        
        # Take a screenshot
        print("\nTaking a screenshot...")
        screenshot = send_command(session_id, "browser_take_screenshot")
        if screenshot and 'result' in screenshot:
            # Save the screenshot
            with open("example_screenshot.jpg", "wb") as f:
                import base64
                image_data = base64.b64decode(screenshot['result'])
                f.write(image_data)
            print("Screenshot saved as example_screenshot.jpg")
        
        # Navigate to another page
        print("\nNavigating to another website...")
        result = send_command(session_id, "browser_navigate", {"url": "https://news.ycombinator.com"})
        print(f"Navigation result: {result}")
        
        # Wait for the page to load
        time.sleep(3)
        
        # Take another snapshot
        print("\nTaking a snapshot of the second page...")
        snapshot = send_command(session_id, "browser_snapshot")
        
        # Find and click on a link (for example, the first link we find)
        if snapshot and 'result' in snapshot:
            elements = snapshot['result'].get('elements', [])
            link_element = None
            
            # Find a link element
            for element in elements:
                if element.get('name') == 'a' and 'ref' in element:
                    link_element = element
                    break
            
            if link_element:
                text = link_element.get('attributes', {}).get('innerText', 'No text')
                print(f"\nFound a link: {text[:50]}...")
                print("Clicking on the link...")
                
                # Click on the link
                click_result = send_command(session_id, "browser_click", {
                    "element": text,
                    "ref": link_element.get('ref')
                })
                print(f"Click result: {click_result}")
                
                # Wait for navigation
                time.sleep(3)
        
        print("\nDemo completed!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()