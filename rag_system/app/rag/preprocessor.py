import re
from typing import List
from bs4 import BeautifulSoup


class TextPreprocessor:
    """Text preprocessing for RAG pipeline"""
    
    def __init__(self):
        self.boilerplate_patterns = [
            r'cookie policy',
            r'privacy policy',
            r'terms of service',
            r'copyright ©',
            r'all rights reserved',
            r'navigation',
            r'menu',
            r'footer',
            r'header',
        ]
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove special characters but keep basic punctuation
        # text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)\[\]\{\}]', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def remove_boilerplate(self, text: str) -> str:
        """Remove boilerplate content"""
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            line_lower = line.lower().strip()
            # Skip lines containing boilerplate patterns
            if any(pattern in line_lower for pattern in self.boilerplate_patterns):
                continue
            # Skip very short lines (likely navigation)
            if len(line.strip()) < 10 and len(line.strip()) > 0:
                continue
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def normalize_structure(self, text: str) -> str:
        """Preserve and normalize document structure"""
        # Ensure proper spacing around headers
        text = re.sub(r'(#{1,6})\s*(.+)', r'\1 \2\n', text)
        
        # Ensure proper list formatting
        text = re.sub(r'\n\s*[-*]\s+', r'\n• ', text)
        text = re.sub(r'\n\s*\d+\.\s+', r'\n1. ', text)
        
        # Ensure paragraphs are separated
        text = re.sub(r'\n\s*\n', r'\n\n', text)
        
        return text
    
    def preprocess(self, text: str, content_type: str = "text/plain") -> str:
        """Full preprocessing pipeline"""
        # Handle different content types
        if content_type == "text/html":
            text = self.extract_text_from_html(text)
        
        # Clean text
        text = self.clean_text(text)
        
        # Remove boilerplate
        text = self.remove_boilerplate(text)
        
        # Normalize structure
        text = self.normalize_structure(text)
        
        # Final cleanup
        text = self.clean_text(text)
        
        return text
    
    def preprocess_file_content(self, content: bytes, filename: str) -> str:
        """Preprocess file content based on filename"""
        # Determine content type from filename
        if filename.lower().endswith('.html'):
            content_type = "text/html"
        elif filename.lower().endswith('.md'):
            content_type = "text/markdown"
        else:
            content_type = "text/plain"
        
        # Decode content
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            # Try with error handling
            text = content.decode('utf-8', errors='ignore')
        
        return self.preprocess(text, content_type)