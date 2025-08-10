from __future__ import annotations
import os, time
from typing import Any, Dict, List, Tuple, Optional
from openai import OpenAI
from .base import Provider

class OpenAIReasoningProvider(Provider):
    name = "openai-reasoning"
    def __init__(self, model: str, base_url: Optional[str] = None, api_key: Optional[str] = None, effort: str = "medium"):
        super().__init__(model)
        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), **kwargs)
        self.effort = effort

    def supports_images(self) -> bool:
        return True

    def _convert_messages_to_input(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert standard chat messages to the reasoning API input format"""
        input_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                # System messages are handled differently in reasoning API
                continue
            elif msg["role"] == "user":
                content = msg["content"]
                if isinstance(content, str):
                    input_messages.append({
                        "role": "user",
                        "content": [{"type": "input_text", "text": content}]
                    })
                elif isinstance(content, list):
                    # Handle mixed content (text + images)
                    converted_content = []
                    for item in content:
                        if item.get("type") == "text":
                            converted_content.append({"type": "input_text", "text": item["text"]})
                        elif item.get("type") == "image_url":
                            # Convert image format for reasoning API
                            converted_content.append({
                                "type": "input_image", 
                                "input_image": {
                                    "format": "url",
                                    "data": item["image_url"]["url"]
                                }
                            })
                    input_messages.append({
                        "role": "user", 
                        "content": converted_content
                    })
        
        return input_messages

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        
        # Convert messages to reasoning API format
        input_messages = self._convert_messages_to_input(messages)
        
        # Add system message content to the first user message if present
        system_content = ""
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
                break
        
        if system_content and input_messages:
            # Prepend system content to first user message
            if input_messages[0]["content"] and len(input_messages[0]["content"]) > 0:
                first_text_item = next((item for item in input_messages[0]["content"] if item.get("type") == "input_text"), None)
                if first_text_item:
                    first_text_item["text"] = system_content + "\n\n" + first_text_item["text"]
        
        try:
            resp = self.client.responses.create(
                model=self.model,
                input=input_messages,
                text={
                    "format": {"type": "text"},
                    "verbosity": "medium"
                },
                reasoning={
                    "effort": self.effort,
                    "summary": "auto"
                },
                tools=[],
                store=True
            )
            
            # Extract the text response
            text = ""
            if hasattr(resp, 'choices') and resp.choices:
                # Standard format
                text = resp.choices[0].message.content or ""
            elif hasattr(resp, 'content') and resp.content:
                # Extract from reasoning API response
                for item in resp.content:
                    if hasattr(item, 'text'):
                        text += item.text
                    elif isinstance(item, dict) and 'text' in item:
                        text += item['text']
            elif hasattr(resp, 'text'):
                text = resp.text
            else:
                # Fallback: try to extract text from response
                text = str(resp)
                
        except Exception as e:
            # Fallback to standard chat completions if reasoning API fails
            print(f"Reasoning API failed, falling back to standard API: {e}")
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.2),
                max_tokens=kwargs.get("max_tokens", 500)
            )
            text = resp.choices[0].message.content or ""
        
        return text, int((time.time()-start)*1000)
