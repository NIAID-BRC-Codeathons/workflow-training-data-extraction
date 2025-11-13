"""
Data Repository Writer Module

This module provides functionality to save Python objects to the outbreak_data folder
with unique filenames and automatically update the catalog.
"""

import json
import csv
import os
from datetime import datetime
from typing import Any, Optional
import hashlib
import uuid
import sys

# Add scripts directory to path to import ARGO
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
from ARGO import ArgoWrapper


def write_to_repository(data_object: Any, description: Optional[str] = None, base_name: Optional[str] = None) -> str:
    """
    Write a Python object to the outbreak_data repository with a unique filename
    and update the catalog.
    
    Args:
        data_object: The Python object to save (must be JSON serializable)
        description: Optional description for the catalog entry
        base_name: Optional base name for the file (default: "data")
    
    Returns:
        str: The path to the saved file
    
    Raises:
        TypeError: If the data_object is not JSON serializable
        IOError: If there are issues writing to the file or catalog
    """
    
    # Ensure the outbreak_data directory exists
    os.makedirs("outbreak_data", exist_ok=True)
    
    # Generate a unique filename
    if base_name is None:
        base_name = "data"
    
    # Create unique identifier using timestamp and UUID
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]  # Use first 8 characters of UUID
    
    # Also create a content hash for additional uniqueness verification
    try:
        content_str = json.dumps(data_object, sort_keys=True)
        content_hash = hashlib.md5(content_str.encode()).hexdigest()[:6]
    except (TypeError, ValueError) as e:
        raise TypeError(f"Data object is not JSON serializable: {e}")
    
    # Construct the filename
    filename = f"{base_name}_{timestamp}_{unique_id}_{content_hash}.json"
    filepath = os.path.join("outbreak_data", filename)
    
    # Check if file already exists (extremely unlikely with UUID + timestamp + hash)
    counter = 1
    while os.path.exists(filepath):
        filename = f"{base_name}_{timestamp}_{unique_id}_{content_hash}_{counter}.json"
        filepath = os.path.join("outbreak_data", filename)
        counter += 1
    
    # Write the data to the file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_object, f, indent=2, ensure_ascii=False)
    except IOError as e:
        raise IOError(f"Failed to write data to {filepath}: {e}")
    
    # Update the catalog
    catalog_path = os.path.join("outbreak_data", "catalog.csv")
    
    # Generate description if not provided
    if description is None:
        # Auto-generate description based on data structure
        description = _generate_description(data_object, filename)
    
    # Check if catalog exists and has headers
    catalog_exists = os.path.exists(catalog_path)
    
    try:
        # Read existing catalog to check headers
        if catalog_exists:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers != ['filename', 'description']:
                    catalog_exists = False  # Treat as non-existent if headers are wrong
        
        # Write to catalog
        with open(catalog_path, 'a' if catalog_exists else 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write headers if catalog doesn't exist or is being recreated
            if not catalog_exists:
                writer.writerow(['filename', 'description'])
            
            # Write the new entry
            writer.writerow([filename, description])
    
    except IOError as e:
        # If catalog update fails, still return the filepath but warn
        print(f"Warning: Failed to update catalog: {e}")
    
    print(f"Successfully saved data to: {filepath}")
    return filepath


def _generate_description(data_object: Any, filename: str) -> str:
    """
    Generate an automatic description based on the data structure using ARGO LLM.
    
    Args:
        data_object: The data object to describe
        filename: The filename being used
    
    Returns:
        str: Auto-generated description
    
    Raises:
        Exception: If ARGO fails to generate a description
    """
    
    # Initialize ARGO wrapper
    argo = ArgoWrapper(model="gpt4o")
    
    # System prompt for ARGO
    system_prompt = """You are a data analyst helping to catalog outbreak data.
    Generate a concise, informative description (max 100 words) for a data file based on its content.
    Include the disease, location, time of outbreak"""
    
    # User prompt with data structure
    user_prompt = f"""Generate a catalog description for this data file:
    
    Data Structure Summary:
    {data_object}
    """
    
    # Call ARGO
    response = argo.invoke(system_prompt, user_prompt, temperature=0.3)
    
    if response and 'response' in response:
        # Extract the response text
        description = response['response']
        # Clean up the description (remove extra whitespace, ensure single line)
        description = ' '.join(description.split())
        return description
    else:
        raise Exception("Invalid response from ARGO")


# Example usage and testing
if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        "outbreak_id": "TEST001",
        "disease": "Test Disease",
        "location": "Test Location",
        "date": datetime.utcnow().isoformat(),
        "cases": 100,
        "details": {
            "severity": "moderate",
            "spread_rate": "low"
        }
    }
    
    # Test the function
    try:
        saved_path = write_to_repository(
            sample_data,
            description="Test outbreak data for demonstration purposes",
            base_name="test_outbreak"
        )
        print(f"Test successful! File saved to: {saved_path}")
        
        # Test with auto-generated description
        saved_path2 = write_to_repository(
            {"auto": "test", "data": [1, 2, 3]},
            base_name="auto_desc_test"
        )
        print(f"Auto-description test successful! File saved to: {saved_path2}")
        
    except Exception as e:
        print(f"Test failed: {e}")
