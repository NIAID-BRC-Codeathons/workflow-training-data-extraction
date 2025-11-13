

def format_response(query: str, search_response):
    # Handle different response structures
    data_items = []

    # Check if search_response is a list
    if isinstance(search_response, list):
        data_items = search_response
    # Check if it has a 'data' attribute or key
    elif hasattr(search_response, 'data'):
        data_items = search_response.data
    elif isinstance(search_response, dict) and 'data' in search_response:
        data_items = search_response['data']
    # Check for 'web' attribute (older API structure)
    elif hasattr(search_response, 'web'):
        data_items = search_response.web
    # Check for 'results' key
    elif isinstance(search_response, dict) and 'results' in search_response:
        data_items = search_response['results']
    else:
        # Try to use the response directly
        data_items = [search_response] if search_response else []
        
    # Check if we have results
    if not search_response or len(data_items) == 0:
        print(f"❌ No results found for query: {query}")
        return []

    # Process results
    formatted_results = []

    for item in data_items:
        # Handle both object and dict structures
        if hasattr(item, '__dict__'):
            # Convert object to dict for easier handling
            item_dict = item.__dict__
        elif isinstance(item, dict):
            item_dict = item
        else:
            continue
        
        # Extract content - try multiple possible field names
        content = ''
        for field in ['markdown', 'content', 'text', 'description', 'snippet']:
            if hasattr(item, field):
                content = getattr(item, field) or ''
                if content:
                    break
            elif isinstance(item_dict, dict) and field in item_dict:
                content = item_dict[field] or ''
                if content:
                    break
        
        formatted_results.append({
            "snippet": content[:500] + "..." if len(content) > 500 else content,
            "content": content,
            "query": query
        })
    return formatted_results