"""
Response parser for AI-generated content.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ParsedResponse:
    """Container for parsed AI response."""
    main_content: str
    sql_queries: List[str]
    suggestions: List[str]
    insights: List[str]
    follow_up_questions: List[str]
    metadata: Dict[str, Any]

class ResponseParser:
    """
    Parser for AI-generated responses to extract structured information.
    """
    
    def __init__(self):
        """Initialize the response parser."""
        # Patterns for extracting different types of content
        self.sql_pattern = re.compile(
            r'```sql\s*(.*?)\s*```|```\s*(SELECT.*?)\s*```',
            re.DOTALL | re.IGNORECASE
        )
        
        self.code_pattern = re.compile(
            r'```(?:sql|python|json)?\s*(.*?)\s*```',
            re.DOTALL
        )
        
        self.list_pattern = re.compile(
            r'^\s*(?:\d+\.|\-|\•)\s*(.+)$',
            re.MULTILINE
        )
        
        self.insight_keywords = [
            'insight', 'finding', 'observation', 'trend', 'pattern',
            'notable', 'significant', 'important', 'key point'
        ]
        
        self.suggestion_keywords = [
            'suggest', 'recommend', 'consider', 'try', 'might want',
            'could', 'should', 'next step'
        ]
    
    def parse_response(self, response_text: str, intent: str = 'general') -> ParsedResponse:
        """
        Parse AI response into structured components.
        
        Args:
            response_text: Raw AI response text
            intent: The intent of the original query
            
        Returns:
            ParsedResponse object with structured content
        """
        if not response_text:
            return ParsedResponse(
                main_content="",
                sql_queries=[],
                suggestions=[],
                insights=[],
                follow_up_questions=[],
                metadata={}
            )
        
        # Extract SQL queries
        sql_queries = self._extract_sql_queries(response_text)
        
        # Extract suggestions
        suggestions = self._extract_suggestions(response_text)
        
        # Extract insights
        insights = self._extract_insights(response_text)
        
        # Extract follow-up questions
        follow_up_questions = self._extract_follow_up_questions(response_text)
        
        # Clean main content (remove extracted elements)
        main_content = self._clean_main_content(
            response_text, sql_queries, suggestions, insights, follow_up_questions
        )
        
        # Generate metadata
        metadata = self._generate_metadata(response_text, intent)
        
        return ParsedResponse(
            main_content=main_content.strip(),
            sql_queries=sql_queries,
            suggestions=suggestions,
            insights=insights,
            follow_up_questions=follow_up_questions,
            metadata=metadata
        )
    
    def _extract_sql_queries(self, text: str) -> List[str]:
        """Extract SQL queries from the response."""
        queries = []
        
        # Find code blocks that contain SQL
        matches = self.sql_pattern.findall(text)
        for match in matches:
            # match is a tuple, get the non-empty group
            query = match[0] if match[0] else match[1]
            if query.strip():
                queries.append(query.strip())
        
        # Also look for SQL-like statements outside code blocks
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE']
        lines = text.split('\n')
        
        current_query = []
        in_query = False
        
        for line in lines:
            line_upper = line.strip().upper()
            
            # Start of a potential SQL query
            if any(line_upper.startswith(keyword) for keyword in sql_keywords):
                if current_query:
                    queries.append('\n'.join(current_query).strip())
                current_query = [line.strip()]
                in_query = True
            elif in_query:
                # Continue building the query
                if line.strip():
                    current_query.append(line.strip())
                    # End query on semicolon or empty line after content
                    if line.strip().endswith(';'):
                        queries.append('\n'.join(current_query).strip())
                        current_query = []
                        in_query = False
                else:
                    # Empty line might end the query
                    if current_query:
                        queries.append('\n'.join(current_query).strip())
                        current_query = []
                        in_query = False
        
        # Add any remaining query
        if current_query:
            queries.append('\n'.join(current_query).strip())
        
        # Remove duplicates while preserving order
        unique_queries = []
        seen = set()
        for query in queries:
            if query not in seen and len(query) > 10:  # Filter out very short "queries"
                seen.add(query)
                unique_queries.append(query)
        
        return unique_queries
    
    def _extract_suggestions(self, text: str) -> List[str]:
        """Extract suggestions from the response."""
        suggestions = []
        
        # Look for sections that contain suggestions
        suggestion_sections = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in self.suggestion_keywords):
                # Found a suggestion line
                suggestion_text = line.strip()
                
                # Clean up the suggestion
                suggestion_text = re.sub(r'^\d+\.\s*', '', suggestion_text)
                suggestion_text = re.sub(r'^[-•]\s*', '', suggestion_text)
                
                if len(suggestion_text) > 10:  # Filter out very short suggestions
                    suggestions.append(suggestion_text)
        
        # Also look for numbered or bulleted lists that might be suggestions
        list_matches = self.list_pattern.findall(text)
        for match in list_matches:
            if any(keyword in match.lower() for keyword in self.suggestion_keywords):
                if match not in suggestions and len(match) > 10:
                    suggestions.append(match.strip())
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _extract_insights(self, text: str) -> List[str]:
        """Extract insights from the response."""
        insights = []
        
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in self.insight_keywords):
                # Found an insight line
                insight_text = line.strip()
                
                # Clean up the insight
                insight_text = re.sub(r'^\d+\.\s*', '', insight_text)
                insight_text = re.sub(r'^[-•]\s*', '', insight_text)
                
                if len(insight_text) > 15:  # Filter out very short insights
                    insights.append(insight_text)
        
        return insights[:5]  # Limit to 5 insights
    
    def _extract_follow_up_questions(self, text: str) -> List[str]:
        """Extract follow-up questions from the response."""
        questions = []
        
        # Look for question patterns
        question_patterns = [
            r'(?:Would you like to|Do you want to|Should we|Can we|How about)\s+([^?]+\?)',
            r'([^.!]*\?)',  # Any sentence ending with ?
        ]
        
        for pattern in question_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                question = match.strip()
                if len(question) > 10 and question not in questions:
                    questions.append(question)
        
        # Also look for sections labeled as questions or follow-ups
        lines = text.split('\n')
        in_question_section = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Check if we're entering a question section
            if any(phrase in line_lower for phrase in ['follow-up', 'next questions', 'you might ask']):
                in_question_section = True
                continue
            
            if in_question_section:
                # Extract questions from this section
                if line.strip() and ('?' in line or line.strip().startswith(('-', '•', '1.', '2.'))):
                    question = line.strip()
                    question = re.sub(r'^\d+\.\s*', '', question)
                    question = re.sub(r'^[-•]\s*', '', question)
                    
                    if len(question) > 10 and question not in questions:
                        questions.append(question)
                elif not line.strip():
                    in_question_section = False
        
        return questions[:5]  # Limit to 5 questions
    
    def _clean_main_content(self, text: str, sql_queries: List[str], 
                           suggestions: List[str], insights: List[str],
                           follow_up_questions: List[str]) -> str:
        """Clean the main content by removing extracted elements."""
        cleaned_text = text
        
        # Remove SQL code blocks
        cleaned_text = self.code_pattern.sub('', cleaned_text)
        
        # Remove extracted suggestions, insights, and questions
        all_extracted = suggestions + insights + follow_up_questions
        
        for item in all_extracted:
            # Remove the item and common prefixes
            patterns_to_remove = [
                re.escape(item),
                r'^\d+\.\s*' + re.escape(item),
                r'^[-•]\s*' + re.escape(item),
            ]
            
            for pattern in patterns_to_remove:
                cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.MULTILINE)
        
        # Clean up extra whitespace and empty lines
        cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
        cleaned_text = re.sub(r'^\s*\n', '', cleaned_text)
        
        return cleaned_text.strip()
    
    def _generate_metadata(self, text: str, intent: str) -> Dict[str, Any]:
        """Generate metadata about the response."""
        return {
            'word_count': len(text.split()),
            'character_count': len(text),
            'has_code': bool(self.code_pattern.search(text)),
            'has_questions': '?' in text,
            'intent': intent,
            'confidence_indicators': self._extract_confidence_indicators(text)
        }
    
    def _extract_confidence_indicators(self, text: str) -> List[str]:
        """Extract phrases that indicate confidence level."""
        confidence_phrases = [
            'definitely', 'certainly', 'clearly', 'obviously',
            'might', 'could', 'possibly', 'perhaps', 'maybe',
            'likely', 'probably', 'appears to', 'seems to'
        ]
        
        found_indicators = []
        text_lower = text.lower()
        
        for phrase in confidence_phrases:
            if phrase in text_lower:
                found_indicators.append(phrase)
        
        return found_indicators
    
    def extract_table_recommendations(self, response: ParsedResponse) -> List[Dict[str, Any]]:
        """
        Extract table recommendations from a parsed response.
        
        Args:
            response: ParsedResponse object
            
        Returns:
            List of table recommendation dictionaries
        """
        recommendations = []
        
        # Look for table names in the main content and suggestions
        all_text = response.main_content + ' ' + ' '.join(response.suggestions)
        
        # Pattern to match table references
        table_patterns = [
            r'\b([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\b',  # schema.table.column
            r'\b([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\b',  # schema.table
            r'\b([a-zA-Z_][a-zA-Z0-9_]*_(?:table|data|info|records))\b',  # table-like names
        ]
        
        for pattern in table_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                if match not in [r['name'] for r in recommendations]:
                    recommendations.append({
                        'name': match,
                        'confidence': 0.7,  # Default confidence
                        'reason': 'Mentioned in AI response'
                    })
        
        return recommendations[:10]  # Limit to 10 recommendations
    
    def format_for_display(self, response: ParsedResponse) -> Dict[str, Any]:
        """
        Format parsed response for display in UI.
        
        Args:
            response: ParsedResponse object
            
        Returns:
            Dictionary formatted for UI display
        """
        return {
            'main_content': response.main_content,
            'sql_queries': [
                {'query': query, 'formatted': self._format_sql(query)}
                for query in response.sql_queries
            ],
            'suggestions': response.suggestions,
            'insights': response.insights,
            'follow_up_questions': response.follow_up_questions,
            'has_code': bool(response.sql_queries),
            'metadata': response.metadata
        }
    
    def _format_sql(self, sql: str) -> str:
        """
        Basic SQL formatting for display.
        
        Args:
            sql: SQL query string
            
        Returns:
            Formatted SQL string
        """
        # Basic formatting - could be enhanced with a proper SQL formatter
        formatted = sql.strip()
        
        # Add line breaks after major keywords
        keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING']
        for keyword in keywords:
            formatted = re.sub(
                f'\\b{keyword}\\b',
                f'\n{keyword}',
                formatted,
                flags=re.IGNORECASE
            )
        
        # Clean up extra whitespace
        formatted = re.sub(r'\n\s*\n', '\n', formatted)
        formatted = formatted.strip()
        
        return formatted

