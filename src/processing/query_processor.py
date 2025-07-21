"""
Query processing module that combines keyword extraction and data normalization.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .keyword_extractor import KeywordExtractor, ExtractedKeywords
from .data_normalizer import DataNormalizer
from ..database.query_builder import QueryBuilder, build_table_discovery_query

logger = logging.getLogger(__name__)

@dataclass
class ProcessedQuery:
    """Container for processed query information."""
    original_query: str
    keywords: ExtractedKeywords
    intent: str
    suggested_tables: List[str]
    query_parameters: Dict[str, Any]
    confidence: float
    processing_metadata: Dict[str, Any]

class QueryProcessor:
    """
    Main query processor that orchestrates keyword extraction and data normalization.
    """
    
    def __init__(self):
        """Initialize the query processor."""
        self.keyword_extractor = KeywordExtractor()
        self.data_normalizer = DataNormalizer()
        self.query_builder = QueryBuilder()
    
    def process_user_query(self, query: str) -> ProcessedQuery:
        """
        Process a user query through the complete pipeline.
        
        Args:
            query: Raw user query string
            
        Returns:
            ProcessedQuery object with all processed information
        """
        logger.info(f"Processing user query: {query}")
        
        # Extract keywords and determine intent
        keywords = self.keyword_extractor.extract_keywords(query)
        
        # Extract time period information
        time_period = self.keyword_extractor.extract_time_period(query)
        
        # Extract table references
        table_refs = self.keyword_extractor.extract_table_references(query)
        
        # Build query parameters
        query_parameters = self._build_query_parameters(keywords, time_period, table_refs)
        
        # Normalize parameters
        normalized_parameters = self.data_normalizer.normalize_query_parameters(query_parameters)
        
        # Generate suggested tables based on keywords
        suggested_tables = self._suggest_tables(keywords)
        
        # Calculate overall confidence
        confidence = self._calculate_overall_confidence(keywords, time_period, table_refs)
        
        # Build processing metadata
        metadata = {
            'time_period': time_period,
            'table_references': table_refs,
            'processing_steps': [
                'keyword_extraction',
                'intent_detection', 
                'parameter_normalization',
                'table_suggestion'
            ]
        }
        
        return ProcessedQuery(
            original_query=query,
            keywords=keywords,
            intent=keywords.intent,
            suggested_tables=suggested_tables,
            query_parameters=normalized_parameters,
            confidence=confidence,
            processing_metadata=metadata
        )
    
    def _build_query_parameters(self, keywords: ExtractedKeywords, 
                               time_period: Optional[Dict[str, str]],
                               table_refs: List[str]) -> Dict[str, Any]:
        """Build query parameters from extracted information."""
        parameters = {
            'keywords': self.keyword_extractor.get_search_terms(keywords),
            'primary_keywords': keywords.primary_keywords,
            'secondary_keywords': keywords.secondary_keywords,
            'entities': keywords.entities
        }
        
        if time_period:
            parameters['time_period'] = time_period
        
        if table_refs:
            parameters['table_references'] = table_refs
        
        return parameters
    
    def _suggest_tables(self, keywords: ExtractedKeywords) -> List[str]:
        """Suggest relevant tables based on extracted keywords."""
        suggestions = []
        
        # Use primary keywords for table suggestions
        search_terms = self.keyword_extractor.get_search_terms(keywords)
        
        # Add domain-specific table suggestions based on intent
        if keywords.intent == 'table_discovery':
            # For table discovery, suggest based on keywords
            for keyword in search_terms:
                suggestions.extend(self._get_table_suggestions_for_keyword(keyword))
        
        elif keywords.intent == 'trend_analysis':
            # For trend analysis, suggest tables that might contain time series data
            suggestions.extend([
                'production_data',
                'sales_data', 
                'performance_metrics',
                'financial_data',
                'operational_metrics'
            ])
        
        # Remove duplicates while preserving order
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:10]  # Limit to top 10 suggestions
    
    def _get_table_suggestions_for_keyword(self, keyword: str) -> List[str]:
        """Get table suggestions for a specific keyword."""
        # This could be enhanced with a more sophisticated mapping
        keyword_table_map = {
            'train': ['train_data', 'training_records', 'locomotive_data'],
            'production': ['production_data', 'manufacturing_data', 'output_metrics'],
            'sales': ['sales_data', 'revenue_data', 'customer_transactions'],
            'employee': ['employee_data', 'hr_records', 'staff_info'],
            'inventory': ['inventory_data', 'stock_levels', 'warehouse_data'],
            'customer': ['customer_data', 'client_info', 'user_records'],
            'order': ['order_data', 'purchase_orders', 'transaction_records'],
            'product': ['product_data', 'item_catalog', 'merchandise_info']
        }
        
        return keyword_table_map.get(keyword.lower(), [])
    
    def _calculate_overall_confidence(self, keywords: ExtractedKeywords,
                                    time_period: Optional[Dict[str, str]],
                                    table_refs: List[str]) -> float:
        """Calculate overall confidence for the processed query."""
        base_confidence = keywords.confidence
        
        # Boost confidence if time period is detected
        if time_period:
            base_confidence += 0.1
        
        # Boost confidence if table references are found
        if table_refs:
            base_confidence += 0.1
        
        # Boost confidence based on number of entities
        if keywords.entities:
            base_confidence += min(len(keywords.entities) * 0.05, 0.15)
        
        return min(base_confidence, 1.0)
    
    def generate_database_query(self, processed_query: ProcessedQuery) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a database query based on processed query information.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            Tuple of (SQL query string, parameters dictionary)
        """
        intent = processed_query.intent
        keywords = processed_query.keywords
        
        if intent == 'table_discovery':
            return self._generate_table_discovery_query(processed_query)
        elif intent == 'trend_analysis':
            return self._generate_trend_analysis_query(processed_query)
        else:
            return self._generate_general_query(processed_query)
    
    def _generate_table_discovery_query(self, processed_query: ProcessedQuery) -> Tuple[str, Dict[str, Any]]:
        """Generate query for table discovery."""
        search_terms = self.keyword_extractor.get_search_terms(processed_query.keywords)
        
        if not search_terms:
            # Fallback to show all tables
            query = """
            SELECT 
                table_catalog as database_name,
                table_schema as schema_name,
                table_name,
                table_type,
                row_count,
                comment
            FROM information_schema.tables
            ORDER BY table_name
            LIMIT 50
            """
            return query, {}
        
        # Use the query builder for table discovery
        return build_table_discovery_query(search_terms, limit=50)
    
    def _generate_trend_analysis_query(self, processed_query: ProcessedQuery) -> Tuple[str, Dict[str, Any]]:
        """Generate query for trend analysis."""
        # This is a template - would need actual table and column names
        time_period = processed_query.processing_metadata.get('time_period')
        period = '1Y'  # Default period
        
        if time_period:
            period_value = time_period.get('value', '1Y')
            if 'year' in period_value.lower():
                period = '1Y'
            elif 'month' in period_value.lower():
                period = '1M'
            elif 'quarter' in period_value.lower():
                period = '3M'
        
        # Template query - would need to be customized based on actual schema
        query = """
        SELECT 
            'trend_analysis' as query_type,
            'Please specify table and date column for trend analysis' as message,
            %(period)s as requested_period
        """
        
        return query, {'period': period}
    
    def _generate_general_query(self, processed_query: ProcessedQuery) -> Tuple[str, Dict[str, Any]]:
        """Generate general query based on keywords."""
        # For general queries, return information about the query processing
        query = """
        SELECT 
            'general_query' as query_type,
            %(original_query)s as original_query,
            %(intent)s as detected_intent,
            %(confidence)s as confidence_score
        """
        
        return query, {
            'original_query': processed_query.original_query,
            'intent': processed_query.intent,
            'confidence': processed_query.confidence
        }
    
    def extract_column_mappings(self, query: str) -> Dict[str, str]:
        """
        Extract potential column mappings from user query.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary mapping query terms to potential column names
        """
        mappings = {}
        
        # Common column name patterns
        column_patterns = {
            r'\b(?:date|time|created|updated|timestamp)\b': 'date_column',
            r'\b(?:amount|value|price|cost|revenue|sales)\b': 'value_column',
            r'\b(?:count|quantity|number|total)\b': 'count_column',
            r'\b(?:name|title|description)\b': 'name_column',
            r'\b(?:id|identifier|key)\b': 'id_column',
            r'\b(?:status|state|condition)\b': 'status_column'
        }
        
        query_lower = query.lower()
        
        for pattern, column_type in column_patterns.items():
            import re
            matches = re.findall(pattern, query_lower)
            if matches:
                mappings[column_type] = matches[0]
        
        return mappings
    
    def suggest_query_improvements(self, processed_query: ProcessedQuery) -> List[str]:
        """
        Suggest improvements to make the query more specific.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Low confidence suggestions
        if processed_query.confidence < 0.6:
            suggestions.append("Try to be more specific about what data you're looking for")
            suggestions.append("Include table names or column names if you know them")
        
        # Intent-specific suggestions
        if processed_query.intent == 'table_discovery':
            if not processed_query.keywords.primary_keywords:
                suggestions.append("Include keywords related to the data you're searching for")
        
        elif processed_query.intent == 'trend_analysis':
            time_period = processed_query.processing_metadata.get('time_period')
            if not time_period:
                suggestions.append("Specify a time period (e.g., 'last year', 'past 6 months')")
            
            if not processed_query.suggested_tables:
                suggestions.append("Mention the specific data or metrics you want to analyze")
        
        # General suggestions
        if len(processed_query.original_query.split()) < 3:
            suggestions.append("Provide more context about your data request")
        
        return suggestions

