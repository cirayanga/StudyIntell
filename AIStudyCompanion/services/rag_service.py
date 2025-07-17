import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import CohereEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document
from app import db
from models import KnowledgeBase

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        self.embeddings = None
        self.vector_store = None
        
        if self.cohere_api_key:
            try:
                self.embeddings = CohereEmbeddings(
                    cohere_api_key=self.cohere_api_key,
                    user_agent="ai-study-buddy/1.0"
                )
                self.initialize_vector_store()
            except Exception as e:
                logger.error(f"Error initializing embeddings: {e}")
                self.embeddings = None
        else:
            logger.warning("Cohere API key not found for RAG service")
    
    def initialize_vector_store(self):
        """Initialize or load the vector store with existing knowledge base"""
        try:
            from app import app
            with app.app_context():
                # Load existing knowledge base from database
                knowledge_items = KnowledgeBase.query.all()
                
                if knowledge_items:
                    documents = []
                    for item in knowledge_items:
                        doc = Document(
                            page_content=item.content,
                            metadata={
                                "title": item.title,
                                "category": item.category,
                                "source_url": item.source_url,
                                "id": item.id
                            }
                        )
                        documents.append(doc)
                    
                    # Create vector store from documents
                    if documents and self.embeddings:
                        self.vector_store = FAISS.from_documents(documents, self.embeddings)
                        logger.info(f"Initialized vector store with {len(documents)} documents")
                else:
                    # Initialize with default educational content
                    self.add_default_knowledge()
                
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
    
    def add_default_knowledge(self):
        """Add some default educational content to the knowledge base"""
        from app import app
        
        default_content = [
            {
                "title": "Study Techniques: Spaced Repetition",
                "content": """Spaced repetition is a learning technique that involves reviewing information at increasing intervals. This method is based on the psychological spacing effect, where information is more easily recalled if learning sessions are spaced out over time rather than concentrated in a short period. The key principles include: 1) Initial learning session, 2) First review after 1 day, 3) Second review after 3 days, 4) Third review after 1 week, 5) Subsequent reviews at increasing intervals. This technique is particularly effective for memorizing facts, vocabulary, and concepts that require long-term retention.""",
                "category": "Study Methods"
            },
            {
                "title": "Active Learning Strategies",
                "content": """Active learning involves engaging with material through activities that require students to analyze, synthesize, and evaluate information. Unlike passive learning (like reading or listening to lectures), active learning strategies include: summarizing information in your own words, asking questions about the material, discussing concepts with peers, teaching others, creating mind maps or concept diagrams, solving problems and applying knowledge, and self-testing through quizzes or flashcards. Research shows that active learning significantly improves retention and understanding compared to passive methods.""",
                "category": "Study Methods"
            },
            {
                "title": "Time Management: Pomodoro Technique",
                "content": """The Pomodoro Technique is a time management method that uses short, focused work intervals followed by brief breaks. The standard approach involves: 1) Choose a task to work on, 2) Set a timer for 25 minutes (one 'Pomodoro'), 3) Work on the task until the timer rings, 4) Take a 5-minute break, 5) Repeat the cycle, 6) After 4 Pomodoros, take a longer 15-30 minute break. This technique helps maintain focus, prevents burnout, and makes large tasks feel more manageable by breaking them into smaller, timed segments.""",
                "category": "Time Management"
            },
            {
                "title": "Note-Taking: Cornell Method",
                "content": """The Cornell Note-Taking System is an effective method for organizing and reviewing notes. It involves dividing your note page into three sections: 1) Note-taking area (right side, largest section) for writing main notes during class or reading, 2) Cue column (left side, narrow) for keywords, questions, and main ideas added during review, 3) Summary section (bottom) for a brief summary of the page's content. This system encourages active engagement with material and makes reviewing more efficient by providing clear organization and built-in study cues.""",
                "category": "Note-Taking"
            }
        ]
        
        try:
            with app.app_context():
                for content in default_content:
                    # Check if content already exists
                    existing = KnowledgeBase.query.filter_by(title=content["title"]).first()
                    if not existing:
                        knowledge_item = KnowledgeBase(
                            title=content["title"],
                            content=content["content"],
                            category=content["category"]
                        )
                        db.session.add(knowledge_item)
                
                db.session.commit()
                logger.info("Added default knowledge base content")
                
                # Reinitialize vector store with new content
                self.initialize_vector_store()
            
        except Exception as e:
            logger.error(f"Error adding default knowledge: {e}")
            with app.app_context():
                db.session.rollback()
    
    def add_knowledge(self, title: str, content: str, category: str, source_url: str = None) -> bool:
        """Add new knowledge to the database and update vector store"""
        try:
            # Add to database
            knowledge_item = KnowledgeBase(
                title=title,
                content=content,
                category=category,
                source_url=source_url
            )
            db.session.add(knowledge_item)
            db.session.commit()
            
            # Add to vector store if initialized
            if self.vector_store and self.embeddings:
                doc = Document(
                    page_content=content,
                    metadata={
                        "title": title,
                        "category": category,
                        "source_url": source_url,
                        "id": knowledge_item.id
                    }
                )
                self.vector_store.add_documents([doc])
            
            logger.info(f"Added knowledge item: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding knowledge: {e}")
            db.session.rollback()
            return False
    
    def search_knowledge(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant information"""
        if not self.vector_store:
            return []
        
        try:
            # Perform similarity search
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "title": doc.metadata.get("title", "Unknown"),
                    "category": doc.metadata.get("category", "General"),
                    "source_url": doc.metadata.get("source_url"),
                    "relevance_score": float(score),
                    "id": doc.metadata.get("id")
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    def get_context_for_query(self, query: str, max_context_length: int = 1000) -> str:
        """Get relevant context from knowledge base for a query"""
        relevant_docs = self.search_knowledge(query, k=3)
        
        if not relevant_docs:
            return ""
        
        context_parts = []
        current_length = 0
        
        for doc in relevant_docs:
            content = doc["content"]
            title = doc["title"]
            
            # Add title and content, but respect max length
            addition = f"[{title}]: {content}\n\n"
            if current_length + len(addition) <= max_context_length:
                context_parts.append(addition)
                current_length += len(addition)
            else:
                # Add partial content if it fits
                remaining_space = max_context_length - current_length
                if remaining_space > 50:  # Only add if we have reasonable space
                    partial_content = content[:remaining_space-len(f"[{title}]: ")]
                    context_parts.append(f"[{title}]: {partial_content}...")
                break
        
        return "".join(context_parts)
    
    def get_study_recommendations(self, query: str) -> List[str]:
        """Get study recommendations based on query"""
        relevant_docs = self.search_knowledge(query, k=5)
        
        recommendations = []
        categories_found = set()
        
        for doc in relevant_docs:
            category = doc["category"]
            if category not in categories_found:
                categories_found.add(category)
                recommendations.append(f"Review {category} materials")
        
        # Add general study recommendations
        if "study" in query.lower() or "learn" in query.lower():
            recommendations.extend([
                "Try active recall techniques",
                "Use spaced repetition for memorization",
                "Take regular breaks using the Pomodoro technique"
            ])
        
        return recommendations[:5]  # Limit to 5 recommendations
