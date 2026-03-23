import os

def get_llm(temperature: float = 0.0, max_tokens: int = None, advanced_model: bool = False):
    """
    Centralized LLM provider factory. 
    Swaps models dynamically based on the LLM_PROVIDER environment variable.
    
    If advanced_model is True, uses a smarter reasoning model (Sonnet/Pro).
    Otherwise, uses a fast, cheap model (Haiku/Flash) for validation sweeps.
    """
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        # Fast model for validation, Pro model for complex agent reasoning
        model_name = "gemini-3.1-flash-lite-preview"
        return ChatGoogleGenerativeAI(
            model=model_name, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
    
    # Default: Anthropic
    from langchain_anthropic import ChatAnthropic
    model_name = "claude-3-5-sonnet-20241022" if advanced_model else "claude-3-haiku-20240307"
    return ChatAnthropic(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens
    )
