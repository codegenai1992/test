"""
Prompt templates for AI interactions.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class PromptContext:
    """Context information for prompt generation."""
    user_query: str
    intent: str
    keywords: List[str]
    table_info: Optional[List[Dict[str, Any]]] = None
    data_sample: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, str]]] = None

class PromptTemplates:
    """
    Collection of prompt templates for different AI interactions.
    """
    
    @staticmethod
    def get_table_discovery_prompt(context: PromptContext) -> str:
        """
        Generate prompt for table discovery queries.
        
        Args:
            context: PromptContext with query information
            
        Returns:
            Formatted prompt string
        """
        base_prompt = f"""
You are a helpful database assistant specializing in Snowflake data analysis. 
The user is looking for tables related to their query.

User Query: "{context.user_query}"
Detected Keywords: {', '.join(context.keywords)}
Intent: {context.intent}

"""
        
        if context.table_info:
            base_prompt += "Available Tables:\n"
            for table in context.table_info:
                table_name = table.get('table_name', 'Unknown')
                schema_name = table.get('schema_name', 'Unknown')
                comment = table.get('comment', 'No description available')
                row_count = table.get('row_count', 'Unknown')
                
                base_prompt += f"- {schema_name}.{table_name} ({row_count} rows): {comment}\n"
            
            base_prompt += "\n"
        
        base_prompt += """
Based on the user's query and the available tables, please:

1. Identify the most relevant tables for the user's needs
2. Explain why these tables are relevant
3. Suggest specific columns or data points that might be useful
4. Provide example queries if appropriate
5. Offer follow-up questions to help refine the search

Please provide a helpful, conversational response that guides the user to the information they need.
"""
        
        return base_prompt
    
    @staticmethod
    def get_trend_analysis_prompt(context: PromptContext) -> str:
        """
        Generate prompt for trend analysis queries.
        
        Args:
            context: PromptContext with query information
            
        Returns:
            Formatted prompt string
        """
        base_prompt = f"""
You are an expert data analyst specializing in trend analysis and business intelligence.
The user wants to analyze trends in their data.

User Query: "{context.user_query}"
Detected Keywords: {', '.join(context.keywords)}
Intent: {context.intent}

"""
        
        if context.data_sample:
            base_prompt += "Sample Data:\n"
            for key, value in context.data_sample.items():
                base_prompt += f"- {key}: {value}\n"
            base_prompt += "\n"
        
        if context.table_info:
            base_prompt += "Relevant Tables:\n"
            for table in context.table_info:
                table_name = table.get('table_name', 'Unknown')
                schema_name = table.get('schema_name', 'Unknown')
                base_prompt += f"- {schema_name}.{table_name}\n"
            base_prompt += "\n"
        
        base_prompt += """
Please analyze the data and provide:

1. Key trends and patterns in the data
2. Insights about performance over time
3. Notable changes or anomalies
4. Recommendations based on the trends
5. Suggestions for deeper analysis

Focus on actionable insights that can help with business decision-making.
Explain your analysis in clear, business-friendly language.
"""
        
        return base_prompt
    
    @staticmethod
    def get_data_explanation_prompt(context: PromptContext) -> str:
        """
        Generate prompt for explaining data results.
        
        Args:
            context: PromptContext with query information
            
        Returns:
            Formatted prompt string
        """
        base_prompt = f"""
You are a data analyst helping users understand their query results.

Original Query: "{context.user_query}"
Keywords: {', '.join(context.keywords)}

"""
        
        if context.data_sample:
            base_prompt += "Query Results:\n"
            for key, value in context.data_sample.items():
                base_prompt += f"- {key}: {value}\n"
            base_prompt += "\n"
        
        base_prompt += """
Please provide:

1. A clear explanation of what the results show
2. Key insights from the data
3. Context about what these numbers mean
4. Suggestions for follow-up analysis
5. Any limitations or caveats about the data

Make your explanation accessible to both technical and non-technical users.
"""
        
        return base_prompt
    
    @staticmethod
    def get_query_suggestion_prompt(context: PromptContext) -> str:
        """
        Generate prompt for query suggestions.
        
        Args:
            context: PromptContext with query information
            
        Returns:
            Formatted prompt string
        """
        base_prompt = f"""
You are a SQL expert helping users formulate better database queries.

User's Request: "{context.user_query}"
Detected Intent: {context.intent}
Keywords: {', '.join(context.keywords)}

"""
        
        if context.table_info:
            base_prompt += "Available Tables and Columns:\n"
            for table in context.table_info:
                table_name = table.get('table_name', 'Unknown')
                schema_name = table.get('schema_name', 'Unknown')
                columns = table.get('columns', [])
                
                base_prompt += f"\n{schema_name}.{table_name}:\n"
                for col in columns[:10]:  # Limit to first 10 columns
                    col_name = col.get('name', 'Unknown')
                    col_type = col.get('data_type', 'Unknown')
                    base_prompt += f"  - {col_name} ({col_type})\n"
            
            base_prompt += "\n"
        
        base_prompt += """
Please provide:

1. Suggested SQL queries that address the user's request
2. Explanation of what each query does
3. Alternative approaches to get the same information
4. Tips for optimizing the queries
5. Follow-up questions that might provide additional insights

Format your SQL suggestions clearly and include comments explaining key parts.
"""
        
        return base_prompt
    
    @staticmethod
    def get_conversational_prompt(context: PromptContext) -> str:
        """
        Generate prompt for conversational interactions.
        
        Args:
            context: PromptContext with query information
            
        Returns:
            Formatted prompt string
        """
        base_prompt = """
You are a friendly and knowledgeable database assistant. You help users explore and understand their data through natural conversation.

"""
        
        if context.conversation_history:
            base_prompt += "Conversation History:\n"
            for exchange in context.conversation_history[-5:]:  # Last 5 exchanges
                base_prompt += f"User: {exchange.get('user', '')}\n"
                base_prompt += f"Assistant: {exchange.get('assistant', '')}\n\n"
        
        base_prompt += f"Current User Query: \"{context.user_query}\"\n"
        base_prompt += f"Detected Keywords: {', '.join(context.keywords)}\n"
        base_prompt += f"Intent: {context.intent}\n\n"
        
        base_prompt += """
Please respond in a helpful, conversational manner. Consider the conversation history and provide:

1. A direct answer to the user's question
2. Additional context or insights that might be helpful
3. Suggestions for related questions or analysis
4. Clear next steps if the user wants to dive deeper

Keep your response engaging and easy to understand.
"""
        
        return base_prompt
    
    @staticmethod
    def get_error_handling_prompt(context: PromptContext, error_message: str) -> str:
        """
        Generate prompt for handling errors gracefully.
        
        Args:
            context: PromptContext with query information
            error_message: The error that occurred
            
        Returns:
            Formatted prompt string
        """
        return f"""
You are a helpful database assistant. The user encountered an error while trying to execute their query.

User Query: "{context.user_query}"
Error Message: "{error_message}"
Keywords: {', '.join(context.keywords)}

Please provide:

1. A friendly explanation of what went wrong
2. Suggestions for how to fix the issue
3. Alternative approaches to get the information they need
4. Tips to avoid similar errors in the future

Be empathetic and focus on helping the user succeed with their data exploration.
"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """
        Get the system prompt that defines the AI assistant's role.
        
        Returns:
            System prompt string
        """
        return """
You are an expert Snowflake database assistant with deep knowledge of:
- SQL query optimization and best practices
- Data analysis and business intelligence
- Snowflake-specific features and functions
- Data visualization and reporting
- Database schema design and relationships

Your role is to help users:
- Discover and understand their data
- Write effective SQL queries
- Analyze trends and patterns
- Generate actionable insights
- Optimize database performance

Always provide:
- Clear, accurate information
- Practical, actionable advice
- Multiple approaches when possible
- Context about limitations or assumptions
- Follow-up suggestions for deeper analysis

Communicate in a friendly, professional manner that's accessible to users with varying levels of technical expertise.
"""
    
    @staticmethod
    def format_prompt_with_context(template: str, **kwargs) -> str:
        """
        Format a prompt template with additional context variables.
        
        Args:
            template: Base prompt template
            **kwargs: Additional context variables
            
        Returns:
            Formatted prompt string
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # Handle missing variables gracefully
            return template + f"\n\n[Note: Missing context variable: {e}]"

