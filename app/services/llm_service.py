"""Service d'intégration avec OpenAI pour les embeddings et DeepSeek pour la génération de réponses."""
import os
import logging
import json
from typing import Dict, Any, List, Optional
import asyncio

from openai import OpenAI, AsyncOpenAI
from app.config import settings
from app.utils.circuit_breaker import circuit

logger = logging.getLogger(__name__)

class LLMService:
    """Service pour l'intégration avec OpenAI (embedding) et DeepSeek (génération)."""
    
    def __init__(self):
        # Initialisation du client OpenAI pour les embeddings
        self.openai_client = self._initialize_openai()
        
        # Initialisation du client DeepSeek pour la génération
        self.deepseek_client = self._initialize_deepseek()
        
        # Configuration des modèles
        self.embedding_model = settings.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.chat_model = "deepseek-chat"
        self.reasoner_model = "deepseek-reasoner"
        
        # Prompt par défaut
        self.default_system_prompt = (
            "Tu es un expert du football qui répond à des questions en te basant "
            "uniquement sur le contexte fourni. Si l'information n'est pas dans le "
            "contexte, indique-le clairement. Sois concis et précis dans tes réponses."
        )
        
        logger.info("Service LLM initialisé avec OpenAI pour embedding et DeepSeek pour génération")
    
    def _initialize_openai(self):
        """Initialise le client OpenAI pour les embeddings."""
        try:
            if not settings.OPENAI_API_KEY:
                logger.error("Clé API OpenAI non définie. Définissez OPENAI_API_KEY dans .env")
                raise ValueError("Clé API OpenAI non définie")
            
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("Client OpenAI initialisé avec succès")
            return client
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client OpenAI: {str(e)}")
            raise
    
    def _initialize_deepseek(self):
        """Initialise le client DeepSeek pour la génération."""
        try:
            if not settings.DEEPSEEK_API_KEY:
                logger.error("Clé API DeepSeek non définie. Définissez DEEPSEEK_API_KEY dans .env")
                raise ValueError("Clé API DeepSeek non définie")
            
            # DeepSeek utilise la même interface que OpenAI mais avec une base_url différente
            client = AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1"  # URL de l'API DeepSeek
            )
            
            logger.info("Client DeepSeek initialisé avec succès")
            return client
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client DeepSeek: {str(e)}")
            raise
    
    @circuit(name="embedding_generate", failure_threshold=3, recovery_timeout=60)
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Génère un embedding pour le texte donné en utilisant OpenAI.
        
        Args:
            text: Texte à encoder
            
        Returns:
            Vecteur d'embedding
            
        Raises:
            Exception: Si la génération échoue
        """
        if not text:
            return []
        
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erreur lors de la génération d'embedding: {str(e)}")
            raise
    
    @circuit(name="llm_generate", failure_threshold=3, recovery_timeout=60)
    async def generate_response(
        self,
        question: str,
        context: str,
        use_reasoner: bool = False,
        system_prompt: str = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        """
        Génère une réponse à partir du contexte et de la question en utilisant DeepSeek.
        
        Args:
            question: Question posée
            context: Contexte pour la génération
            use_reasoner: Si True, utilise le modèle deepseek-reasoner, sinon deepseek-chat
            system_prompt: Prompt système (None = prompt par défaut)
            max_tokens: Nombre maximum de tokens pour la réponse
            temperature: Température pour la génération (0-1)
            
        Returns:
            Réponse générée par le LLM
            
        Raises:
            Exception: Si la génération échoue
        """
        # Utiliser les valeurs par défaut si non spécifiées
        system_prompt = system_prompt or self.default_system_prompt
        
        # Choisir le modèle en fonction du paramètre use_reasoner
        model = self.reasoner_model if use_reasoner else self.chat_model
        
        # Construire le message utilisateur
        user_message = f"Question: {question}\n\nContexte: {context}"
        
        try:
            # Générer la réponse avec DeepSeek
            response = await self.deepseek_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erreur lors de la génération de réponse avec DeepSeek ({model}): {str(e)}")
            # Tenter une réponse de secours en cas d'échec
            return self._generate_fallback_response(question, context)
    
    def _generate_fallback_response(self, question: str, context: str) -> str:
        """
        Génère une réponse de secours en cas d'échec du LLM.
        
        Args:
            question: Question posée
            context: Contexte disponible
            
        Returns:
            Réponse de secours
        """
        return (
            "Je suis désolé, je ne peux pas générer une réponse complète pour le moment. "
            "Voici les informations disponibles dans le contexte :\n\n"
            f"{context[:500]}..." if len(context) > 500 else context
        )

    @circuit(name="reasoning_analyze", failure_threshold=3, recovery_timeout=60)
    async def analyze_question_complexity(self, question: str) -> Dict[str, Any]:
        """
        Analyse la complexité d'une question pour déterminer s'il faut utiliser le modèle reasoner.
        
        Args:
            question: Question à analyser
            
        Returns:
            Informations sur la complexité de la question
        """
        try:
            # Utiliser le modèle de chat pour analyser rapidement la question
            response = await self.deepseek_client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "Analyse la complexité de cette question sur le football. Réponds avec un JSON contenant uniquement les champs 'complexity' (1-5), 'reasoning_required' (true/false), et 'reasoning_type' (comparative/temporal/statistical/causal/none)."},
                    {"role": "user", "content": question}
                ],
                response_format={"type": "json_object"},
                max_tokens=256,
                temperature=0.1
            )
            
            # Extraire le JSON de la réponse
            analysis_text = response.choices[0].message.content
            analysis = json.loads(analysis_text)
            
            # Déterminer si le modèle reasoner est nécessaire
            use_reasoner = analysis.get("reasoning_required", False) or analysis.get("complexity", 0) >= 4
            
            return {
                "complexity": analysis.get("complexity", 0),
                "reasoning_required": analysis.get("reasoning_required", False),
                "reasoning_type": analysis.get("reasoning_type", "none"),
                "use_reasoner": use_reasoner
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de la complexité: {str(e)}")
            # Par défaut, ne pas utiliser le modèle reasoner
            return {
                "complexity": 0,
                "reasoning_required": False,
                "reasoning_type": "none",
                "use_reasoner": False,
                "error": str(e)
            }

# Instance singleton pour utilisation dans toute l'application
llm_service = LLMService()