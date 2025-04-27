"""
Google Gemini API integration for Scholar Scraper.
This module handles all interactions with the Gemini API.
"""
import os
import re
import requests
from typing import Dict, List, Optional, Tuple, Any

from config.settings import config
from utils.error_handling import handle_api_error, log_exceptions
from utils.caching import cache_result


class GeminiAPI:
    """Class for interacting with the Google Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize the Gemini API client.
        
        Args:
            api_key: Optional API key (defaults to config value)
        """
        self.api_key = api_key or config.GOOGLE_GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Google Gemini API key not found. Set GOOGLE_GEMINI_API_KEY in .env file.")
        
        self.endpoint = f"{config.GEMINI_API_ENDPOINT}?key={self.api_key}"
    
    @cache_result(expiry_hours=24.0)
    def generate_content(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generate content from the Gemini API.
        
        Args:
            prompt: Text prompt to send to the API
            max_retries: Maximum number of retry attempts on failure
            
        Returns:
            Generated text response
            
        Raises:
            ValueError: If API request fails after retries
        """
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
        
        headers = {"Content-Type": "application/json"}
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.endpoint, 
                    headers=headers, 
                    json=payload, 
                    timeout=60
                )
                response.raise_for_status()
                
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                
            except Exception as e:
                if attempt == max_retries - 1:
                    handle_api_error("Gemini", e)
                    raise ValueError(f"Failed to generate content after {max_retries} attempts: {str(e)}")
        
        # This should never be reached due to the exception above
        return ""
    
    @cache_result(expiry_hours=168.0)  # Cache translation for a week
    def translate_to_english(self, text: str, source_lang: str = 'German') -> str:
        """
        Translate text to English using Gemini.
        
        Args:
            text: Text to translate
            source_lang: Source language of the text
            
        Returns:
            Translated text in English
        """
        if not text:
            return text
        
        # Create a translation prompt
        prompt = f"""
        Translate the following text from {source_lang} to English:
        
        "{text}"
        
        Return ONLY the translated text without any additional commentary.
        """
        
        try:
            result = self.generate_content(prompt)
            
            # Extract the translated text using a series of regex patterns
            # Try different patterns in order of preference
            
            # 1. Match: entire response if it's just the translation
            if '\n' not in result and len(result.split()) <= 20:
                return result
            
            # 2. Match: text within triple quotes
            match = re.search(r'```(.+?)```', result, re.DOTALL)
            if match:
                translation = match.group(1).strip()
                return translation
            
            # 3. Match: text within double quotes
            match = re.search(r'"([^"]+)"', result)
            if match:
                translation = match.group(1).strip()
                return translation
            
            # 4. Match: quoted translation
            match = re.search(r'"([A-Za-z\s\-]+)"', result)
            if match:
                translation = match.group(1).strip()
                return translation
            
            # 5. Match: single word only
            match = re.match(r'^([A-Za-z\s\-]+)$', result)
            if match:
                translation = match.group(1).strip()
                return translation
            
            # 6. Fallback: comma-separated list (batch translation)
            if ',' in result:
                first = result.split(',')[0].strip()
                return first
            
            # 7. Return whatever we got
            return result
            
        except Exception as e:
            handle_api_error("Gemini Translation", e)
            return text  # Return original text if translation fails
    
    @cache_result(expiry_hours=168.0)  # Cache for a week
    def extract_keywords_from_question(self, question: str) -> List[Tuple[str, int]]:
        """
        Extract relevant search keywords from a research question.
        
        Args:
            question: Research question text
            
        Returns:
            List of (keyword, weight) tuples
        """
        prompt = f"""
        Extract the most essential research keywords from this question: 
        
        "{question}"
        
        Return ONLY a list of the top 5-7 most specific and meaningful single-word keywords that would be useful for searching academic databases. 
        
        For each keyword, assign a relevance weight from 1-10, with 10 being most relevant.
        Format your response as a simple list with one keyword:weight per line, like this:
        keyword1:10
        keyword2:8
        etc.
        
        Focus on scientific, technical, or domain-specific terms that would yield relevant research papers.
        """
        
        try:
            text = self.generate_content(prompt)
        except Exception:
            # In case of API failure, extract simple keywords from the question
            words = question.split()
            return [(w, 1) for w in words if len(w) > 3][:5]
        
        # Parse the response into (keyword, weight) pairs
        pairs = []
        for line in text.strip().splitlines():
            if ':' in line:
                kw, wt = line.split(':', 1)
                kw = kw.strip()
                
                # Skip multi-word keywords as they don't work well with our search
                if ' ' in kw or '-' in kw:
                    continue
                
                try:
                    # Parse weight as integer, default to 1 if parsing fails
                    weight = int(wt.strip())
                    pairs.append((kw, weight))
                except ValueError:
                    pairs.append((kw, 1))
            elif line.strip():
                # Handle case where no weight is provided
                kw = line.strip()
                if ' ' not in kw and '-' not in kw:
                    pairs.append((kw, 1))
        
        return pairs
    
    @cache_result(expiry_hours=24.0)
    def summarize_papers(self, abstracts: List[str], keywords: List[str], 
                         nutrition_only: bool = False) -> str:
        """
        Generate a summary of research papers based on their abstracts.
        
        Args:
            abstracts: List of paper abstracts
            keywords: Keywords used for the search
            nutrition_only: Whether to focus on nutritional aspects
            
        Returns:
            Generated summary text
        """
        # Format the abstracts and keywords for the prompt
        keyword_lines = '\n'.join([f'- {kw}' for kw in keywords])
        abstract_text = ''
        
        for idx, abs_text in enumerate(abstracts, 1):
            abs_text = abs_text.strip().replace('\n', ' ')
            abstract_text += f"Abstract {idx}: {abs_text}\n\n"
        
        # Create an appropriate prompt based on the mode
        if nutrition_only:
            prompt = f"""
            As a scientific nutrition researcher, I need you to analyze these ingredient(s) based on the provided scientific abstracts. 
            
            Keywords/Ingredients:
            {keyword_lines}
            
            Abstracts:
            {abstract_text}
            
            Create a concise but comprehensive summary that:
            
            1. Clearly states which ingredient(s) you're analyzing
            2. Summarizes the established beneficial effects from scientific literature (with evidence strength indicated)
            3. Summarizes potential harmful effects or risks from scientific literature (with evidence strength indicated)
            4. Identifies key synergistic or antagonistic interactions with other substances
            5. Provides practical advice on consumption based on scientific findings
            
            Format your response with clear headings and bullet points for readability.
            
            Provide Context & Disclaimers:
            
            Emphasize that effects are often dose-dependent and individual responses can vary.
            Note that the concentration of compounds can vary in natural foods.
            Crucially, include a clear disclaimer: State that the information provided is for educational and informational purposes only, based on general scientific findings, and does not constitute personalized medical or nutritional advice. Strongly emphasize the importance of consulting with qualified healthcare professionals (like doctors or registered dietitians) before making significant dietary changes.
            """
        else:
            prompt = f"""
            As a scientific researcher, I need you to analyze these papers based on the provided scientific abstracts. 
            
            Topic/Keywords:
            {keyword_lines}
            
            Abstracts:
            {abstract_text}
            
            Create a concise but comprehensive summary that:
            
            1. Clearly states the topic being examined
            2. Synthesizes the key findings from the abstracts
            3. Evaluates the quality and consistency of the evidence
            4. Highlights practical takeaways, applications, or implications of these findings
            
            Format your response with clear headings for readability. Use bullet points where appropriate.
            
            Also include an "Important Considerations" section that addresses limitations in the research, conflicting findings, or areas where more research is needed.
            
            End with a clear disclaimer: State that the information provided is for educational and informational purposes only, based on general scientific findings, and does not constitute personalized medical, nutritional, or fitness advice. Emphasize the importance of consulting with qualified healthcare professionals before making significant changes based on this information.
            """
        
        try:
            return self.generate_content(prompt)
        except Exception as e:
            handle_api_error("Gemini Summarization", e)
            return f"Error generating summary: {str(e)}"
