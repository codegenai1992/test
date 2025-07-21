"""
Data normalization module for processing and standardizing data.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import pandas as pd

from config.settings import get_settings

logger = logging.getLogger(__name__)

class DataNormalizer:
    """
    Data normalization and standardization utilities.
    """
    
    def __init__(self):
        """Initialize the data normalizer."""
        self.settings = get_settings()
        self.config = self.settings.get_processing_config().get('data_normalization', {})
        
        # Configuration
        self.date_formats = self.config.get('date_formats', [
            '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d',
            '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S'
        ])
        self.numeric_precision = self.config.get('numeric_precision', 2)
        self.text_case = self.config.get('text_case', 'lower')
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text data.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Apply case normalization
        if self.text_case == 'lower':
            text = text.lower()
        elif self.text_case == 'upper':
            text = text.upper()
        elif self.text_case == 'title':
            text = text.title()
        
        return text
    
    def normalize_date(self, date_value: Union[str, datetime, date]) -> Optional[datetime]:
        """
        Normalize date values to datetime objects.
        
        Args:
            date_value: Input date in various formats
            
        Returns:
            Normalized datetime object or None if parsing fails
        """
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, date):
            return datetime.combine(date_value, datetime.min.time())
        
        if not isinstance(date_value, str):
            date_value = str(date_value)
        
        # Clean the date string
        date_value = date_value.strip()
        
        # Try parsing with different formats
        for fmt in self.date_formats:
            try:
                return datetime.strptime(date_value, fmt)
            except ValueError:
                continue
        
        # Try pandas date parsing as fallback
        try:
            return pd.to_datetime(date_value)
        except:
            logger.warning(f"Could not parse date: {date_value}")
            return None
    
    def normalize_numeric(self, value: Union[str, int, float, Decimal]) -> Optional[float]:
        """
        Normalize numeric values.
        
        Args:
            value: Input numeric value
            
        Returns:
            Normalized float value or None if parsing fails
        """
        if isinstance(value, (int, float)):
            return round(float(value), self.numeric_precision)
        
        if isinstance(value, Decimal):
            return round(float(value), self.numeric_precision)
        
        if not isinstance(value, str):
            value = str(value)
        
        # Clean numeric string
        value = value.strip()
        
        # Remove common formatting characters
        value = re.sub(r'[,$%]', '', value)
        
        # Handle negative numbers in parentheses
        if value.startswith('(') and value.endswith(')'):
            value = '-' + value[1:-1]
        
        try:
            return round(float(value), self.numeric_precision)
        except (ValueError, InvalidOperation):
            logger.warning(f"Could not parse numeric value: {value}")
            return None
    
    def normalize_boolean(self, value: Union[str, bool, int]) -> Optional[bool]:
        """
        Normalize boolean values.
        
        Args:
            value: Input boolean value
            
        Returns:
            Normalized boolean value or None if parsing fails
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, int):
            return bool(value)
        
        if not isinstance(value, str):
            value = str(value)
        
        value = value.strip().lower()
        
        true_values = {'true', 'yes', 'y', '1', 'on', 'enabled'}
        false_values = {'false', 'no', 'n', '0', 'off', 'disabled'}
        
        if value in true_values:
            return True
        elif value in false_values:
            return False
        else:
            logger.warning(f"Could not parse boolean value: {value}")
            return None
    
    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize an entire DataFrame.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Normalized DataFrame
        """
        if df.empty:
            return df
        
        normalized_df = df.copy()
        
        for column in normalized_df.columns:
            # Infer column type and apply appropriate normalization
            sample_values = normalized_df[column].dropna().head(10)
            
            if sample_values.empty:
                continue
            
            # Check if column contains dates
            if self._is_date_column(sample_values):
                normalized_df[column] = normalized_df[column].apply(
                    lambda x: self.normalize_date(x) if pd.notna(x) else None
                )
            
            # Check if column contains numbers
            elif self._is_numeric_column(sample_values):
                normalized_df[column] = normalized_df[column].apply(
                    lambda x: self.normalize_numeric(x) if pd.notna(x) else None
                )
            
            # Check if column contains booleans
            elif self._is_boolean_column(sample_values):
                normalized_df[column] = normalized_df[column].apply(
                    lambda x: self.normalize_boolean(x) if pd.notna(x) else None
                )
            
            # Default to text normalization
            else:
                normalized_df[column] = normalized_df[column].apply(
                    lambda x: self.normalize_text(str(x)) if pd.notna(x) else None
                )
        
        return normalized_df
    
    def _is_date_column(self, sample_values: pd.Series) -> bool:
        """Check if a column contains date values."""
        date_indicators = [
            'date', 'time', 'created', 'updated', 'modified', 'timestamp'
        ]
        
        # Check column name
        column_name = sample_values.name.lower() if sample_values.name else ''
        if any(indicator in column_name for indicator in date_indicators):
            return True
        
        # Check sample values
        for value in sample_values:
            if isinstance(value, (datetime, date)):
                return True
            
            if isinstance(value, str):
                # Look for date patterns
                date_patterns = [
                    r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                    r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
                    r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
                ]
                
                for pattern in date_patterns:
                    if re.search(pattern, str(value)):
                        return True
        
        return False
    
    def _is_numeric_column(self, sample_values: pd.Series) -> bool:
        """Check if a column contains numeric values."""
        numeric_count = 0
        total_count = 0
        
        for value in sample_values:
            total_count += 1
            
            if isinstance(value, (int, float, Decimal)):
                numeric_count += 1
            elif isinstance(value, str):
                # Try to parse as number
                cleaned_value = re.sub(r'[,$%()]', '', value.strip())
                try:
                    float(cleaned_value)
                    numeric_count += 1
                except ValueError:
                    pass
        
        # Consider numeric if more than 70% of values are numeric
        return total_count > 0 and (numeric_count / total_count) > 0.7
    
    def _is_boolean_column(self, sample_values: pd.Series) -> bool:
        """Check if a column contains boolean values."""
        boolean_values = {
            'true', 'false', 'yes', 'no', 'y', 'n', '1', '0', 
            'on', 'off', 'enabled', 'disabled'
        }
        
        for value in sample_values:
            if isinstance(value, bool):
                return True
            
            if isinstance(value, str) and value.lower().strip() in boolean_values:
                return True
        
        return False
    
    def normalize_query_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize query parameters.
        
        Args:
            params: Dictionary of query parameters
            
        Returns:
            Dictionary with normalized parameters
        """
        normalized_params = {}
        
        for key, value in params.items():
            if value is None:
                normalized_params[key] = None
                continue
            
            # Normalize based on parameter name patterns
            key_lower = key.lower()
            
            if 'date' in key_lower or 'time' in key_lower:
                normalized_params[key] = self.normalize_date(value)
            elif any(indicator in key_lower for indicator in ['count', 'amount', 'price', 'value', 'number']):
                normalized_params[key] = self.normalize_numeric(value)
            elif any(indicator in key_lower for indicator in ['flag', 'enabled', 'active', 'is_']):
                normalized_params[key] = self.normalize_boolean(value)
            else:
                # Default to text normalization for string values
                if isinstance(value, str):
                    normalized_params[key] = self.normalize_text(value)
                else:
                    normalized_params[key] = value
        
        return normalized_params
    
    def validate_data_types(self, data: Dict[str, Any], schema: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Validate data types against a schema.
        
        Args:
            data: Data to validate
            schema: Schema defining expected types
            
        Returns:
            Dictionary with validation errors
        """
        errors = {}
        
        for field, expected_type in schema.items():
            if field not in data:
                if field not in errors:
                    errors[field] = []
                errors[field].append(f"Missing required field: {field}")
                continue
            
            value = data[field]
            if value is None:
                continue  # Allow None values
            
            # Type validation
            type_valid = False
            
            if expected_type == 'string':
                type_valid = isinstance(value, str)
            elif expected_type == 'integer':
                type_valid = isinstance(value, int)
            elif expected_type == 'float':
                type_valid = isinstance(value, (int, float))
            elif expected_type == 'boolean':
                type_valid = isinstance(value, bool)
            elif expected_type == 'date':
                type_valid = isinstance(value, (datetime, date))
            elif expected_type == 'datetime':
                type_valid = isinstance(value, datetime)
            
            if not type_valid:
                if field not in errors:
                    errors[field] = []
                errors[field].append(f"Expected {expected_type}, got {type(value).__name__}")
        
        return errors
    
    def clean_column_names(self, columns: List[str]) -> List[str]:
        """
        Clean and normalize column names.
        
        Args:
            columns: List of column names
            
        Returns:
            List of cleaned column names
        """
        cleaned_columns = []
        
        for column in columns:
            # Convert to string and strip whitespace
            clean_name = str(column).strip()
            
            # Replace spaces and special characters with underscores
            clean_name = re.sub(r'[^\w]', '_', clean_name)
            
            # Remove multiple consecutive underscores
            clean_name = re.sub(r'_+', '_', clean_name)
            
            # Remove leading/trailing underscores
            clean_name = clean_name.strip('_')
            
            # Convert to lowercase
            clean_name = clean_name.lower()
            
            # Ensure it doesn't start with a number
            if clean_name and clean_name[0].isdigit():
                clean_name = f"col_{clean_name}"
            
            # Handle empty names
            if not clean_name:
                clean_name = f"column_{len(cleaned_columns)}"
            
            cleaned_columns.append(clean_name)
        
        return cleaned_columns

