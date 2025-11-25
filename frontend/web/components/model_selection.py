"""
Model Selection UI Component (refactored - pure UI logic)
Responsible for rendering model selection interface only
"""

import streamlit as st
import time
from typing import Dict, Any, List, Optional, Tuple, Callable
from frontend.web.utils.constants import PROVIDERS


class ModelSelectionComponent:
    """Model Selection UI Component"""
    
    def __init__(self):
        """Initialize component"""
        pass
    
    def get_provider_info(self, provider: str) -> Dict[str, str]:
        """Get provider information
        
        Args:
            provider: Provider name
            
        Returns:
            Dict: Provider information
        """
        provider_info = {
            "Anthropic": {"name": "Anthropic"},
            "OpenAI": {"name": "OpenAI"},
            "DeepSeek": {"name": "DeepSeek"},
            "Gemini": {"name": "Gemini"},
            "Groq": {"name": "Groq"},
            "Ollama": {"name": "Ollama"}
        }
        return provider_info.get(provider, {"name": provider})
    
    def display_loading_state(self, message: str = "Loading available models..."):
        """Display loading state
        
        Args:
            message: Loading message
        """
        with st.spinner(message):
            time.sleep(0.1)  # Minimum display time
    
    def display_error_state(self, error_msg: str, info_msg: str = None):
        """Display error state
        
        Args:
            error_msg: Error message
            info_msg: Additional info message
        """
        st.error(error_msg)
        if info_msg:
            st.info(info_msg)
    
    def display_success_message(self, message: str):
        """Display success message
        
        Args:
            message: Success message
        """
        st.success(message)
    
    def render_page_header(self):
        """Render page header"""
        st.markdown("### Select AI Model")
        st.markdown("Choose the AI model for your red team operations")
    
    def render_current_model_info(self, current_model: Optional[Dict[str, Any]] = None):
        """Display currently selected model information
        
        Args:
            current_model: Current model information
            
        Returns:
            bool: Whether the change model button was clicked
        """
        if current_model:
            model_name = current_model.get('display_name', 'Unknown')
            st.success(f"✅ Current Model: {model_name}")
            
            # Confirm model change
            if st.button("🔄 Change Model", use_container_width=True):
                return True
            
            st.divider()
        
        return False
    
    def render_provider_selection(
        self, 
        providers: List[str], 
        default_index: int = 0
    ) -> str:
        """Render provider selection UI
        
        Args:
            providers: List of available providers
            default_index: Default selection index
            
        Returns:
            str: Selected provider
        """
        provider_options = []
        provider_mapping = {}
        
        for provider_key in providers:
            provider_info = self.get_provider_info(provider_key)
            display_text = provider_info['name']
            provider_options.append(display_text)
            provider_mapping[display_text] = provider_key
        
        selected_provider_display = st.selectbox(
            "Provider",
            options=provider_options,
            index=default_index,
            help="Choose your service provider",
            key="provider_selection"
        )
        
        return provider_mapping[selected_provider_display]
    
    def render_model_selection(
        self,
        models: List[Dict[str, Any]],
        selected_provider: str,
        default_index: int = 0
    ) -> Optional[str]:
        """Render model selection UI
        
        Args:
            models: List of available models
            selected_provider: Selected provider
            default_index: Default selection index
            
        Returns:
            Optional[str]: Selected model display name
        """
        if not models:
            st.warning(f"No models available for {selected_provider}")
            return None
        
        model_options = []
        model_mapping = {}
        
        for model in models:
            # Clean model name - remove provider prefix and simplify
            display_name = model.get('display_name', 'Unknown Model')
            
            # Clean up display name
            for prefix in [f"[{selected_provider}]", f"[{selected_provider.lower()}]", 
                         f"{selected_provider}", f"{selected_provider.lower()}"]:
                if prefix in display_name:
                    display_name = display_name.replace(f"{prefix} ", "").replace(prefix, "")
            
            model_options.append(display_name)
            model_mapping[display_name] = model
        
        selected_model_display = st.selectbox(
            "Model",
            options=model_options,
            index=default_index,
            help="Choose the specific model variant",
            key="model_selection"
        )
        
        return selected_model_display
    
    def render_initialize_button(self) -> bool:
        """Render initialize button
        
        Returns:
            bool: Whether the button was clicked
        """
        return st.button("Initialize AI Agents", type="primary", use_container_width=True)
    
    def render_complete_selection_ui(
        self,
        providers_data: Dict[str, List[Dict[str, Any]]],
        current_model: Optional[Dict[str, Any]] = None,
        default_provider: Optional[str] = None,
        default_model: Optional[Dict[str, Any]] = None,
        callbacks: Optional[Dict[str, Callable]] = None
    ) -> Optional[Dict[str, Any]]:
        """Render complete model selection UI
        
        Args:
            providers_data: Model data by provider
            current_model: Currently selected model
            default_provider: Default provider
            default_model: Default model
            callbacks: Callback functions
            
        Returns:
            Optional[Dict]: Selected model information
        """
        if callbacks is None:
            callbacks = {}
        
        # Page header
        self.render_page_header()
        
        # Current model info
        if self.render_current_model_info(current_model):
            if "on_model_change" in callbacks:
                callbacks["on_model_change"]()
            return None
        
        # Prepare provider list
        providers = list(providers_data.keys())
        
        # Find default provider index
        default_provider_index = 0
        if default_provider and default_provider in providers:
            default_provider_index = providers.index(default_provider)
        
        # Provider selection
        selected_provider = self.render_provider_selection(providers, default_provider_index)
        
        # Model selection
        if selected_provider in providers_data:
            models = providers_data[selected_provider]
            
            # Find default model index
            default_model_index = 0
            if default_model and models:
                for idx, model in enumerate(models):
                    if model.get('model_name') == default_model.get('model_name'):
                        default_model_index = idx
                        break
            
            # Model selection UI
            selected_model_display = self.render_model_selection(
                models, selected_provider, default_model_index
            )
            
            if selected_model_display:
                # Find selected model
                selected_model = None
                for model in models:
                    display_name = model.get('display_name', 'Unknown Model')
                    # Apply same cleanup logic
                    for prefix in [f"[{selected_provider}]", f"[{selected_provider.lower()}]", 
                                 f"{selected_provider}", f"{selected_provider.lower()}"]:
                        if prefix in display_name:
                            display_name = display_name.replace(f"{prefix} ", "").replace(prefix, "")
                    
                    if display_name == selected_model_display:
                        selected_model = model
                        break
                
                # Initialize button
                if self.render_initialize_button():
                    return selected_model
        
        return None
    
    def show_loading_screen(self, model_info: Dict[str, Any]):
        """Display loading screen
        
        Args:
            model_info: Model information
        """
        provider_info = self.get_provider_info(model_info.get('provider', 'Unknown'))
        
        # Center-aligned loading content
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown(f"""
            <div style="text-align: center; padding: 60px 0;">
                <h2>Setting up {model_info.get('display_name', 'Model')}</h2>
                <p style="opacity: 0.7;">Initializing AI agents for red team operations...</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display progress
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)
        
        return st.empty()
    
    def render_initialization_ui(
        self, 
        model_info: Dict[str, Any],
        status: str = "initializing",
        error_message: str = None
    ):
        """Render initialization UI
        
        Args:
            model_info: Model information
            status: Initialization status ("initializing", "success", "error")
            error_message: Error message (if error status)
            
        Returns:
            str: User action ("retry", "back", None)
        """
        model_name = model_info.get('display_name', 'Model')
        
        if status == "initializing":
            with st.spinner(f"Initializing {model_name}..."):
                time.sleep(0.1)
        
        elif status == "success":
            st.success(f"✅ {model_name} initialized successfully!")
            time.sleep(1.0)
            return "success"
        
        elif status == "error":
            st.error(f"❌ Initialization failed: {error_message or 'Unknown error'}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Retry", use_container_width=True):
                    return "retry"
            with col2:
                if st.button("⬅️ Back", use_container_width=True):
                    return "back"
        
        return None
    
    def display_provider_status(self, status_info: Dict[str, Any]):
        """Display provider status information
        
        Args:
            status_info: Status information
        """
        if status_info.get("type") == "success" and "ollama_message" in status_info:
            st.success(status_info["ollama_message"])
