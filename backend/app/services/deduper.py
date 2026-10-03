"""
Visual deduplication using CLIP embeddings
"""
import numpy as np
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
import torch
import open_clip
from PIL import Image

from models.scan import PhotoRecord, DuplicateGroup, ScanSession
from config import Config

class VisualDeduper:
    """Finds visually similar photos using CLIP embeddings"""
    
    def __init__(self, config: Config):
        self.config = config
        self.device = config.CLIP_DEVICE
        
        # Load CLIP model
        print(f"Loading CLIP model: {config.CLIP_MODEL} on {self.device}...")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            config.CLIP_MODEL,
            pretrained='openai',
            device=self.device
        )
        self.model.eval()
        print("✓ CLIP model loaded")
    
    def find_visual_duplicates(self, session: ScanSession, 
                              progress_callback: Optional[Callable] = None) -> ScanSession:
        """
        Find visually similar photos using CLIP embeddings
        
        Args:
            session: ScanSession with photos already indexed
            progress_callback: Optional callback for progress
            
        Returns:
            Updated ScanSession with visual duplicate groups
        """
        if not session.photos:
            return session
        
        print(f"Computing CLIP embeddings for {len(session.photos)} photos...")
        
        # Compute embeddings for all photos
        embeddings = []
        valid_photos = []
        
        for i, photo in enumerate(session.photos):
            try:
                embedding = self._compute_embedding(photo.file_path)
                if embedding is not None:
                    embeddings.append(embedding)
                    valid_photos.append(photo)
                    
                    if progress_callback:
                        progress_callback({
                            "stage": "embedding",
                            "current": i + 1,
                            "total": len(session.photos)
                        })
            except Exception as e:
                print(f"Warning: Could not compute embedding for {photo.file_path}: {e}")
        
        if not embeddings:
            return session
        
        embeddings = np.array(embeddings)
        
        # Find visual duplicates using cosine distance
        print("Finding visual duplicates...")
        processed = set()
        
        for i in range(len(embeddings)):
            if i in processed:
                continue
            
            # Compute cosine distance to all other images
            distances = self._cosine_distances(embeddings[i:i+1], embeddings)[0]
            
            # Find matches (distance < threshold)
            matches = np.where(distances < self.config.VISUAL_MATCH_THRESHOLD)[0]
            
            # Skip if no duplicates found
            if len(matches) <= 1:
                continue
            
            # Create duplicate group
            group = DuplicateGroup()
            group.group_type = "visual"
            group.photo_ids = [valid_photos[j].id for j in matches]
            group.kept_photo_id = valid_photos[matches[0]].id  # Keep first one
            
            # Calculate average confidence (inverse of distance)
            avg_distance = np.mean(distances[matches])
            group.confidence_score = max(0, 1.0 - avg_distance)
            
            session.duplicate_groups.append(group)
            session.visual_duplicates += len(matches) - 1  # Don't count the original
            
            # Mark as processed
            for j in matches:
                processed.add(j)
        
        return session
    
    def find_exact_duplicates(self, session: ScanSession) -> ScanSession:
        """
        Find exact duplicates by MD5 hash
        
        Args:
            session: ScanSession with photos
            
        Returns:
            Updated ScanSession with exact duplicate groups
        """
        print("Finding exact duplicates by MD5...")
        
        # Group by MD5 hash
        hash_groups = {}
        for photo in session.photos:
            if photo.file_hash_md5:
                if photo.file_hash_md5 not in hash_groups:
                    hash_groups[photo.file_hash_md5] = []
                hash_groups[photo.file_hash_md5].append(photo)
        
        # Create groups for duplicates (groups with 2+ photos)
        for file_hash, photos in hash_groups.items():
            if len(photos) <= 1:
                continue
            
            group = DuplicateGroup()
            group.group_type = "exact"
            group.photo_ids = [p.id for p in photos]
            group.kept_photo_id = photos[0].id  # Keep first one
            group.confidence_score = 1.0  # 100% confidence for exact match
            
            session.duplicate_groups.append(group)
            session.exact_duplicates += len(photos) - 1  # Don't count the original
        
        return session
    
    def _compute_embedding(self, file_path: str) -> Optional[np.ndarray]:
        """Compute CLIP embedding for a single image"""
        try:
            image = Image.open(file_path).convert('RGB')
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                embedding = self.model.encode_image(image_input)
            
            # Normalize and convert to numpy
            embedding = embedding.cpu().numpy()[0]
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            print(f"Error computing embedding for {file_path}: {e}")
            return None
    
    def _cosine_distances(self, query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
        """
        Compute cosine distances between query and corpus embeddings
        
        Lower distance = more similar
        """
        # Normalize
        query_norm = query / np.linalg.norm(query, axis=1, keepdims=True)
        corpus_norm = corpus / np.linalg.norm(corpus, axis=1, keepdims=True)
        
        # Cosine similarity = dot product of normalized vectors
        # Cosine distance = 1 - similarity
        similarities = np.dot(query_norm, corpus_norm.T)
        distances = 1 - similarities
        
        return distances.flatten()
