"""
Tools module for the Nova Educational Bot.
Provides Wikipedia search, DuckDuckGo search, quiz generation, 
flashcards, YouTube search, and calculator functionality.
"""

import wikipedia
from duckduckgo_search import DDGS
from typing import Optional, List, Dict
import re
import json


def search_wikipedia(query: str, sentences: int = 3) -> str:
    """
    Search Wikipedia for information about a topic.
    
    Args:
        query: The search query
        sentences: Number of sentences to return (default: 3)
    
    Returns:
        Summary of the Wikipedia article or error message
    """
    try:
        # Search for the query
        search_results = wikipedia.search(query, results=3)
        
        if not search_results:
            return f"No Wikipedia articles found for '{query}'."
        
        # Try to get the page summary
        for title in search_results:
            try:
                page = wikipedia.page(title, auto_suggest=False)
                summary = wikipedia.summary(title, sentences=sentences, auto_suggest=False)
                return f"📚 **{page.title}**\n\n{summary}\n\n🔗 Source: {page.url}"
            except wikipedia.DisambiguationError as e:
                # Try the first option from disambiguation
                if e.options:
                    try:
                        summary = wikipedia.summary(e.options[0], sentences=sentences, auto_suggest=False)
                        page = wikipedia.page(e.options[0], auto_suggest=False)
                        return f"📚 **{page.title}**\n\n{summary}\n\n🔗 Source: {page.url}"
                    except:
                        continue
            except wikipedia.PageError:
                continue
        
        return f"Could not find detailed information for '{query}'."
        
    except Exception as e:
        return f"Error searching Wikipedia: {str(e)}"


def search_web(query: str, max_results: int = 3) -> str:
    """
    Search the web using DuckDuckGo.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return
    
    Returns:
        Formatted search results
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        if not results:
            return f"No web results found for '{query}'."
        
        formatted_results = ["🌐 **Web Search Results:**\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            body = result.get("body", "No description")
            url = result.get("href", "")
            
            formatted_results.append(f"**{i}. {title}**")
            formatted_results.append(f"{body}")
            if url:
                formatted_results.append(f"🔗 {url}")
            formatted_results.append("")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error searching the web: {str(e)}"


def search_youtube_videos(query: str, max_results: int = 3) -> str:
    """
    Search for educational YouTube videos on a topic.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return
    
    Returns:
        Formatted video results with links
    """
    try:
        search_query = f"{query} educational tutorial"
        with DDGS() as ddgs:
            results = list(ddgs.videos(search_query, max_results=max_results))
        
        if not results:
            return f"No educational videos found for '{query}'."
        
        formatted_results = ["🎬 **Educational Videos:**\n"]
        
        for i, video in enumerate(results, 1):
            title = video.get("title", "No title")
            publisher = video.get("publisher", "Unknown")
            duration = video.get("duration", "")
            url = video.get("content", "")
            
            formatted_results.append(f"**{i}. {title}**")
            formatted_results.append(f"   📺 {publisher} | ⏱️ {duration}")
            if url:
                formatted_results.append(f"   ▶️ Watch: {url}")
            formatted_results.append("")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error searching videos: {str(e)}"


def calculate(expression: str) -> str:
    """
    Perform mathematical calculations safely.
    
    Args:
        expression: Mathematical expression to evaluate
    
    Returns:
        The result of the calculation
    """
    try:
        # Clean the expression
        expression = expression.strip()
        
        # Remove any potentially dangerous characters
        allowed_chars = set("0123456789+-*/().^ %")
        if not all(c in allowed_chars or c.isspace() for c in expression):
            return "Error: Invalid characters in expression. Only numbers and basic operators (+, -, *, /, ^, %) are allowed."
        
        # Replace common math notations
        expression = expression.replace("^", "**")
        expression = expression.replace("%", "/100")
        
        # Safely evaluate
        import ast
        import operator
        
        # Define safe operations
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        
        def eval_expr(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                return operators[type(node.op)](eval_expr(node.left), eval_expr(node.right))
            elif isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](eval_expr(node.operand))
            else:
                raise ValueError(f"Unsupported operation")
        
        tree = ast.parse(expression, mode='eval')
        result = eval_expr(tree.body)
        
        # Format result nicely
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        
        return f"🧮 **Calculation Result:**\n\n`{expression.replace('**', '^')}` = **{result}**"
        
    except ZeroDivisionError:
        return "Error: Division by zero is not allowed."
    except Exception as e:
        return f"Error calculating: {str(e)}"


def generate_quiz_questions(topic: str, num_questions: int = 3) -> str:
    """
    Generate quiz questions on a topic (template for LLM to fill).
    This returns a prompt structure that the LLM will complete.
    
    Args:
        topic: The topic to generate questions about
        num_questions: Number of questions to generate
    
    Returns:
        Template structure for quiz generation
    """
    return f"""GENERATE_QUIZ:{topic}:{num_questions}"""


def generate_flashcards(topic: str, num_cards: int = 5) -> str:
    """
    Generate flashcards for studying a topic.
    
    Args:
        topic: The topic to create flashcards for
        num_cards: Number of flashcards to generate
    
    Returns:
        Template structure for flashcard generation
    """
    return f"""GENERATE_FLASHCARDS:{topic}:{num_cards}"""


def generate_mermaid_diagram(topic: str, diagram_type: str = "flowchart") -> Optional[str]:
    """
    Generate a Mermaid diagram code for educational topics.
    
    Args:
        topic: The topic to create a diagram for
        diagram_type: Type of diagram (flowchart, mindmap, sequence)
    
    Returns:
        Mermaid diagram code or None
    """
    templates = {
        "flowchart": f"""```mermaid
flowchart TD
    A[Start: {topic}] --> B[Step 1]
    B --> C[Step 2]
    C --> D[Step 3]
    D --> E[End Result]
```""",
        "mindmap": f"""```mermaid
mindmap
    root(({topic}))
        Concept 1
            Detail A
            Detail B
        Concept 2
            Detail C
            Detail D
        Concept 3
            Detail E
```""",
        "sequence": f"""```mermaid
sequenceDiagram
    participant User
    participant System
    User->>System: Request about {topic}
    System->>System: Process
    System->>User: Response
```"""
    }
    
    return templates.get(diagram_type, templates["flowchart"])


def extract_keywords(text: str) -> list:
    """
    Extract important keywords from text for follow-up context.
    
    Args:
        text: Input text to extract keywords from
    
    Returns:
        List of keywords
    """
    # Remove common words and extract nouns/proper nouns
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
        'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'under', 'again', 'further', 'then', 'once', 'here',
        'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
        'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
        'because', 'until', 'while', 'although', 'though', 'what', 'which',
        'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'i', 'you',
        'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'its', 'our', 'their', 'mine', 'yours', 'hers',
        'ours', 'theirs', 'about', 'tell', 'know', 'get', 'got', 'like'
    }
    
    # Clean text and split into words
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    
    # Filter out stop words and short words
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Return unique keywords (preserving order)
    seen = set()
    unique_keywords = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique_keywords.append(k)
    
    return unique_keywords[:10]  # Return top 10 keywords


# Subject areas for educational focus
SUBJECT_AREAS = {
    "general": {"name": "General Knowledge", "icon": "🌐", "color": "#667eea"},
    "math": {"name": "Mathematics", "icon": "🧮", "color": "#f59e0b"},
    "science": {"name": "Science", "icon": "🔬", "color": "#10b981"},
    "history": {"name": "History", "icon": "📜", "color": "#8b5cf6"},
    "literature": {"name": "Literature", "icon": "📖", "color": "#ec4899"},
    "programming": {"name": "Programming", "icon": "💻", "color": "#06b6d4"},
    "geography": {"name": "Geography", "icon": "🌍", "color": "#84cc16"},
    "art": {"name": "Art & Music", "icon": "🎨", "color": "#f97316"},
}


# Tool descriptions for the LangChain agent
TOOL_DESCRIPTIONS = {
    "wikipedia": (
        "Search Wikipedia for factual information about people, places, events, "
        "concepts, or any topic. Use this for educational and research queries. "
        "Input should be a clear search term or question."
    ),
    "web_search": (
        "Search the web for current information, news, or topics not covered by Wikipedia. "
        "Use this for recent events, current affairs, or when Wikipedia doesn't have information. "
        "Input should be a search query."
    ),
    "youtube_search": (
        "Search for educational YouTube videos about a topic. Use this when the user "
        "wants video tutorials, lectures, or visual explanations. "
        "Input should be the topic to find videos about."
    ),
    "calculator": (
        "Perform mathematical calculations. Use this for any math problems, "
        "arithmetic, percentages, or numerical computations. "
        "Input should be a mathematical expression like '2 + 2' or '15 * 7'."
    ),
    "quiz": (
        "Generate quiz questions to test knowledge on a topic. Use when the user "
        "wants to practice or test their understanding. "
        "Input should be the topic to create questions about."
    ),
    "flashcards": (
        "Generate study flashcards for learning a topic. Use when the user "
        "wants to memorize facts or study key concepts. "
        "Input should be the topic to create flashcards for."
    ),
    "diagram": (
        "Generate a visual diagram to explain concepts, processes, or relationships. "
        "Use this for educational content that benefits from visualization. "
        "Input should be the topic to visualize."
    )
}
