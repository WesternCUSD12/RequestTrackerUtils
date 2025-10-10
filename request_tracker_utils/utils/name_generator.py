"""
Internal Name Generator for Assets

Generates unique adjective-animal combinations for asset internal names.
Ensures uniqueness by checking against existing assets in Request Tracker.
"""

import csv
import random
import urllib.parse
from pathlib import Path
from typing import List, Tuple, Optional
from .rt_api import rt_api_request


class InternalNameGenerator:
    """Generate unique adjective-animal combinations for asset internal names."""
    
    def __init__(self, config, csv_path: Optional[str] = None):
        """
        Initialize the name generator.
        
        Args:
            config: Flask app config with RT credentials
            csv_path: Path to Adjective-Animal-List.csv (defaults to repo root)
        """
        self.config = config
        
        # Default to repo root if not specified
        if csv_path is None:
            csv_path = Path(__file__).parent.parent.parent / 'Adjective-Animal-List.csv'
        
        self.csv_path = Path(csv_path)
        self.animals = []
        self.adjectives = []
        self._load_combinations()
    
    def _load_combinations(self):
        """Load animals and adjectives from CSV file."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Adjective-Animal CSV not found at {self.csv_path}")
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                animal = row.get('animal', '').strip()
                adjective = row.get('adjective', '').strip()
                
                if animal:  # Only add if animal exists (some rows have only adjective)
                    self.animals.append(animal)
                if adjective:
                    self.adjectives.append(adjective)
        
        # Remove duplicates while preserving order
        self.animals = list(dict.fromkeys(self.animals))
        self.adjectives = list(dict.fromkeys(self.adjectives))
    
    def _check_internal_name_exists(self, internal_name: str) -> bool:
        """
        Check if an internal name already exists in RT.
        
        Args:
            internal_name: The internal name to check
            
        Returns:
            True if the name exists, False otherwise
        """
        try:
            # Query RT for assets with this Description (internal name)
            # Description field is used for internal name
            query = f'Description = "{internal_name}"'
            encoded_query = urllib.parse.quote(query)
            response = rt_api_request('GET', f'/assets?query={encoded_query}', config=self.config)
            
            items = response.get('items', [])
            return len(items) > 0
            
        except Exception as e:
            # If query fails, log and assume name might exist (safer)
            print(f"Error checking internal name: {e}")
            return True
    
    def generate_unique_name(self, max_attempts: int = 100) -> str:
        """
        Generate a unique adjective-animal combination.
        
        Args:
            max_attempts: Maximum number of attempts to find unique name
            
        Returns:
            A unique internal name in format "Adjective Animal"
            
        Raises:
            RuntimeError: If unable to generate unique name after max_attempts
        """
        if not self.animals or not self.adjectives:
            raise ValueError("No animals or adjectives loaded from CSV")
        
        attempts = 0
        while attempts < max_attempts:
            # Generate random combination
            adjective = random.choice(self.adjectives)
            animal = random.choice(self.animals)
            
            # Format: "Adjective Animal" (both capitalized)
            internal_name = f"{adjective.capitalize()} {animal.capitalize()}"
            
            # Check if unique
            if not self._check_internal_name_exists(internal_name):
                return internal_name
            
            attempts += 1
        
        # If we've exhausted attempts, raise error
        raise RuntimeError(
            f"Unable to generate unique internal name after {max_attempts} attempts. "
            f"Available combinations: {len(self.adjectives)} adjectives × {len(self.animals)} animals"
        )
    
    def get_stats(self) -> dict:
        """Get statistics about available combinations."""
        return {
            'total_adjectives': len(self.adjectives),
            'total_animals': len(self.animals),
            'total_combinations': len(self.adjectives) * len(self.animals)
        }
