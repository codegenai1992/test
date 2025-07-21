"""
Keyword extraction module for processing user queries.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from textblob import TextBlob

from config.settings import get_settings

logger = logging.getLogger(__name__)

@dataclass
class ExtractedKeywords:
    """Container for extracted keywords and metadata."""
    primary_keywords: List[str]
    secondary_keywords: List[str]
    entities: List[str]
    intent: str
    confidence: float
    original_query: str

class KeywordExtractor:
    """
    Advanced keyword extraction for database queries and AI processing.
    """
    
    # Domain-specific keywords for different query types
    TABLE_DISCOVERY_KEYWORDS = {
        'table', 'tables', 'list', 'show', 'find', 'search', 'related', 'containing'
    }
    
    TREND_ANALYSIS_KEYWORDS = {
        'trend', 'trends', 'analysis', 'production', 'performance', 'over time',
        'last', 'past', 'previous', 'fy', 'year', 'month', 'quarter'
    }
    
    TIME_PERIOD_PATTERNS = {
        r'\b(?:last|past|previous)\s+(\d+)\s*(year|month|quarter|day)s?\b': 'relative_period',
        r'\bfy\s*(\d{4}|\d{2})\b': 'fiscal_year',
        r'\b(\d{4})\b': 'year',
        r'\b(q[1-4]|quarter\s*[1-4])\b': 'quarter'
    }
    
    def __init__(self):
        """Initialize the keyword extractor."""
        self.settings = get_settings()
        self.config = self.settings.get_processing_config().get('keyword_extraction', {})
        
        # Configuration
        self.min_keyword_length = self.config.get('min_keyword_length', 3)
        self.max_keywords = self.config.get('max_keywords', 10)
        self.stop_words_enabled = self.config.get('stop_words_enabled', True)
        self.stemming_enabled = self.config.get('stemming_enabled', True)
        
        # Initialize NLTK components
        self._initialize_nltk()
        
        # Initialize stemmer
        self.stemmer = PorterStemmer() if self.stemming_enabled else None
        
        # Load stop words
        self.stop_words = set(stopwords.words('english')) if self.stop_words_enabled else set()
        
        # Add custom stop words
        self.stop_words.update({
            'show', 'me', 'the', 'get', 'give', 'tell', 'want', 'need', 'like', 'would'
        })
    
    def _initialize_nltk(self):
        """Initialize required NLTK data."""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading NLTK stopwords...")
            nltk.download('stopwords', quiet=True)
    
    def extract_keywords(self, query: str) -> ExtractedKeywords:
        """
        Extract keywords from user query.
        
        Args:
            query: User input query
            
        Returns:
            ExtractedKeywords object with extracted information
        """
        # Clean and normalize query
        cleaned_query = self._clean_query(query)
        
        # Tokenize
        tokens = word_tokenize(cleaned_query.lower())
        
        # Remove stop words and short words
        filtered_tokens = [
            token for token in tokens 
            if (token not in self.stop_words and 
                len(token) >= self.min_keyword_length and
                token.isalpha())
        ]
        
        # Apply stemming if enabled
        if self.stemming_enabled and self.stemmer:
            stemmed_tokens = [self.stemmer.stem(token) for token in filtered_tokens]
        else:
            stemmed_tokens = filtered_tokens
        
        # Extract primary keywords (most relevant)
        primary_keywords = self._extract_primary_keywords(stemmed_tokens, query)
        
        # Extract secondary keywords
        secondary_keywords = self._extract_secondary_keywords(stemmed_tokens, primary_keywords)
        
        # Extract named entities
        entities = self._extract_entities(query)
        
        # Determine intent
        intent = self._determine_intent(query, primary_keywords)
        
        # Calculate confidence
        confidence = self._calculate_confidence(query, primary_keywords, intent)
        
        return ExtractedKeywords(
            primary_keywords=primary_keywords[:self.max_keywords],
            secondary_keywords=secondary_keywords[:self.max_keywords],
            entities=entities,
            intent=intent,
            confidence=confidence,
            original_query=query
        )
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize the input query."""
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query.strip())
        
        # Handle common abbreviations
        query = re.sub(r'\bfy\b', 'fiscal year', query, flags=re.IGNORECASE)
        query = re.sub(r'\bq(\d)\b', r'quarter \1', query, flags=re.IGNORECASE)
        
        return query
    
    def _extract_primary_keywords(self, tokens: List[str], original_query: str) -> List[str]:
        """Extract primary keywords based on frequency and domain relevance."""
        # Count token frequency
        token_freq = {}
        for token in tokens:
            token_freq[token] = token_freq.get(token, 0) + 1
        
        # Score tokens based on frequency and domain relevance
        scored_tokens = []
        for token, freq in token_freq.items():
            score = freq
            
            # Boost domain-specific keywords
            if token in self.TABLE_DISCOVERY_KEYWORDS:
                score += 5
            elif token in self.TREND_ANALYSIS_KEYWORDS:
                score += 5
            
            # Boost if token appears in original query (case-sensitive match)
            if token in original_query.lower():
                score += 2
            
            scored_tokens.append((token, score))
        
        # Sort by score and return top keywords
        scored_tokens.sort(key=lambda x: x[1], reverse=True)
        return [token for token, _ in scored_tokens]
    
    def _extract_secondary_keywords(self, tokens: List[str], primary_keywords: List[str]) -> List[str]:
        """Extract secondary keywords that complement primary keywords."""
        secondary = []
        for token in tokens:
            if token not in primary_keywords and len(token) >= self.min_keyword_length:
                secondary.append(token)
        
        return secondary
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities from the query."""
        entities = []
        
        # Extract time periods
        for pattern, entity_type in self.TIME_PERIOD_PATTERNS.items():
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                entities.append(match.group().strip())
        
        # Extract potential table/column names (words with underscores or mixed case)
        entity_patterns = [
            r'\b[a-z]+_[a-z_]+\b',  # snake_case
            r'\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b',  # CamelCase
        ]
        
        for pattern in entity_patterns:
            matches = re.finditer(pattern, query)
            for match in matches:
                entities.append(match.group())
        
        return list(set(entities))  # Remove duplicates
    
    def _determine_intent(self, query: str, keywords: List[str]) -> str:
        """Determine the user's intent based on query and keywords."""
        query_lower = query.lower()
        
        # Table discovery intent
        table_indicators = ['show', 'list', 'find', 'search', 'tables', 'table', 'related']
        if any(indicator in query_lower for indicator in table_indicators):
            return 'table_discovery'
        
        # Trend analysis intent
        trend_indicators = ['trend', 'analysis', 'production', 'over time', 'last', 'fy']
        if any(indicator in query_lower for indicator in trend_indicators):
            return 'trend_analysis'
        
        # Data query intent
        query_indicators = ['select', 'count', 'sum', 'average', 'max', 'min']
        if any(indicator in query_lower for indicator in query_indicators):
            return 'data_query'
        
        # Default to general query
        return 'general_query'
    
    def _calculate_confidence(self, query: str, keywords: List[str], intent: str) -> float:
        """Calculate confidence score for the extraction."""
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on keyword quality
        if keywords:
            confidence += min(len(keywords) * 0.1, 0.3)
        
        # Boost confidence based on intent clarity
        intent_indicators = {
            'table_discovery': self.TABLE_DISCOVERY_KEYWORDS,
            'trend_analysis': self.TREND_ANALYSIS_KEYWORDS
        }
        
        if intent in intent_indicators:
            query_lower = query.lower()
            matches = sum(1 for indicator in intent_indicators[intent] 
                         if indicator in query_lower)
            confidence += min(matches * 0.1, 0.2)
        
        # Boost confidence for longer, more specific queries
        if len(query.split()) > 5:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def extract_time_period(self, query: str) -> Optional[Dict[str, str]]:
        """
        Extract time period information from query.
        
        Args:
            query: User query
            
        Returns:
            Dictionary with time period information or None
        """
        for pattern, period_type in self.TIME_PERIOD_PATTERNS.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return {
                    'type': period_type,
                    'value': match.group().strip(),
                    'raw_match': match.group()
                }
        
        return None
    
    def extract_table_references(self, query: str) -> List[str]:
        """
        Extract potential table references from query.
        
        Args:
            query: User query
            
        Returns:
            List of potential table names
        """
        table_refs = []
        
        # Look for words that might be table names
        # Common patterns: snake_case, CamelCase, or words after "from", "table", etc.
        
        # Pattern 1: Words after table-related keywords
        table_keywords = r'\b(?:table|from|in|on)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b'
        matches = re.finditer(table_keywords, query, re.IGNORECASE)
        for match in matches:
            table_refs.append(match.group(1))
        
        # Pattern 2: Snake case words (likely table names)
        snake_case = r'\b[a-z]+(?:_[a-z0-9]+)+\b'
        matches = re.finditer(snake_case, query)
        for match in matches:
            table_refs.append(match.group())
        
        return list(set(table_refs))  # Remove duplicates
    
    def get_search_terms(self, keywords: ExtractedKeywords) -> List[str]:
        """
        Get optimized search terms for database queries.
        
        Args:
            keywords: Extracted keywords object
            
        Returns:
            List of search terms optimized for database searching
        """
        search_terms = []
        
        # Add primary keywords
        search_terms.extend(keywords.primary_keywords)
        
        # Add entities (they're often specific and valuable)
        search_terms.extend(keywords.entities)
        
        # Add selected secondary keywords
        search_terms.extend(keywords.secondary_keywords[:3])  # Limit secondary keywords
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in search_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms[:self.max_keywords]

