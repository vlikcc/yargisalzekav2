"""
Google Cloud Firestore Database Configuration for Scraper API
"""
import os
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class FirestoreManager:
    """Google Cloud Firestore Manager for Scraper API"""
    
    def __init__(self):
        self.client: Optional[firestore.Client] = None
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.database_id = os.getenv("FIRESTORE_DATABASE_ID", "(default)")
        
    def connect(self) -> bool:
        """Firestore'a bağlan"""
        try:
            if self.project_id:
                self.client = firestore.Client(
                    project=self.project_id,
                    database=self.database_id
                )
            else:
                # Default credentials kullan
                self.client = firestore.Client(database=self.database_id)
            
            # Test connection
            test_doc = self.client.collection('_health_check').document('test')
            test_doc.set({'timestamp': firestore.SERVER_TIMESTAMP})
            test_doc.delete()
            
            logger.info(f"Firestore'a başarıyla bağlanıldı - Project: {self.project_id}, DB: {self.database_id}")
            return True
            
        except Exception as e:
            logger.error(f"Firestore bağlantı hatası: {e}")
            return False
    
    def disconnect(self):
        """Firestore bağlantısını kapat"""
        if self.client:
            self.client.close()
            logger.info("Firestore bağlantısı kapatıldı")
    
    def health_check(self) -> bool:
        """Database sağlık kontrolü"""
        try:
            if not self.client:
                return False
            
            # Test query
            test_collection = self.client.collection('_health_check')
            docs = test_collection.limit(1).get()
            return True
            
        except Exception as e:
            logger.error(f"Firestore sağlık kontrolü başarısız: {e}")
            return False
    
    # Yargıtay Decisions Management
    async def save_yargitay_decision(self, decision_data: Dict[str, Any]) -> str:
        """Yargıtay kararını Firestore'a kaydet"""
        try:
            decisions_ref = self.client.collection('yargitay_decisions')
            
            # Decision ID oluştur
            decision_id = decision_data.get('decision_id')
            if not decision_id:
                # Court, date ve number'dan unique ID oluştur
                court = decision_data.get('court', '')
                date = decision_data.get('date', '')
                number = decision_data.get('number', '')
                decision_id = hashlib.md5(f"{court}_{date}_{number}".encode()).hexdigest()
            
            # Timestamp'leri ekle
            decision_data.update({
                'decision_id': decision_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Kaydet
            doc_ref = decisions_ref.document(decision_id)
            doc_ref.set(decision_data, merge=True)
            
            logger.info(f"Yargıtay kararı kaydedildi: {decision_id}")
            return decision_id
            
        except Exception as e:
            logger.error(f"Yargıtay kararı kaydetme hatası: {e}")
            raise
    
    async def get_yargitay_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Yargıtay kararını ID ile getir"""
        try:
            doc_ref = self.client.collection('yargitay_decisions').document(decision_id)
            doc = doc_ref.get()
            
            if doc.exists:
                decision_data = doc.to_dict()
                decision_data['id'] = doc.id
                return decision_data
            
            return None
            
        except Exception as e:
            logger.error(f"Yargıtay kararı getirme hatası: {e}")
            return None
    
    async def search_yargitay_decisions(
        self, 
        keywords: List[str], 
        limit: int = 50,
        court: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Yargıtay kararlarında arama yap"""
        try:
            decisions_ref = self.client.collection('yargitay_decisions')
            query = decisions_ref
            
            # Court filter
            if court:
                query = query.where('court', '==', court)
            
            # Date filters
            if date_from:
                query = query.where('date', '>=', date_from)
            if date_to:
                query = query.where('date', '<=', date_to)
            
            # Keywords filter (array-contains-any)
            if keywords:
                # Firestore array-contains-any max 10 items
                search_keywords = keywords[:10]
                query = query.where('keywords', 'array_contains_any', search_keywords)
            
            # Order and limit
            query = query.order_by('date', direction=firestore.Query.DESCENDING).limit(limit)
            
            # Execute query
            docs = query.get()
            
            results = []
            for doc in docs:
                decision_data = doc.to_dict()
                decision_data['id'] = doc.id
                results.append(decision_data)
            
            logger.info(f"Yargıtay arama tamamlandı: {len(results)} sonuç")
            return results
            
        except Exception as e:
            logger.error(f"Yargıtay arama hatası: {e}")
            return []
    
    async def get_decisions_by_keywords(self, keywords: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Anahtar kelimelere göre kararları getir"""
        return await self.search_yargitay_decisions(keywords=keywords, limit=limit)
    
    # Search Cache Management
    async def save_search_cache(
        self, 
        keywords: List[str], 
        results: List[Dict[str, Any]], 
        search_duration: float
    ) -> str:
        """Arama sonuçlarını cache'e kaydet"""
        try:
            cache_ref = self.client.collection('search_cache')
            
            # Keywords hash oluştur
            keywords_str = '_'.join(sorted(keywords))
            keywords_hash = hashlib.md5(keywords_str.encode()).hexdigest()
            
            cache_data = {
                'keywords_hash': keywords_hash,
                'keywords': keywords,
                'search_results': results,
                'total_results': len(results),
                'search_duration': search_duration,
                'hit_count': 1,
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_used': firestore.SERVER_TIMESTAMP,
                'expires_at': datetime.utcnow() + timedelta(days=7)
            }
            
            # Cache'e kaydet
            doc_ref = cache_ref.document(keywords_hash)
            doc_ref.set(cache_data)
            
            logger.info(f"Arama cache'e kaydedildi: {keywords_hash}")
            return keywords_hash
            
        except Exception as e:
            logger.error(f"Arama cache kaydetme hatası: {e}")
            raise
    
    async def get_search_cache(self, keywords: List[str]) -> Optional[Dict[str, Any]]:
        """Cache'den arama sonuçlarını getir"""
        try:
            keywords_str = '_'.join(sorted(keywords))
            keywords_hash = hashlib.md5(keywords_str.encode()).hexdigest()
            
            doc_ref = self.client.collection('search_cache').document(keywords_hash)
            doc = doc_ref.get()
            
            if doc.exists:
                cache_data = doc.to_dict()
                
                # Expiry kontrolü
                if cache_data.get('expires_at') and cache_data['expires_at'] > datetime.utcnow():
                    # Hit count'u artır
                    doc_ref.update({
                        'hit_count': firestore.Increment(1),
                        'last_used': firestore.SERVER_TIMESTAMP
                    })
                    
                    return cache_data
                else:
                    # Expired cache'i sil
                    doc_ref.delete()
            
            return None
            
        except Exception as e:
            logger.error(f"Arama cache getirme hatası: {e}")
            return None
    
    # Search Query Logging
    async def log_search_query(
        self, 
        query_text: str, 
        keywords: List[str], 
        results_count: int,
        execution_time: float,
        user_id: Optional[str] = None
    ) -> str:
        """Arama sorgusunu logla"""
        try:
            queries_ref = self.client.collection('search_queries')
            
            query_data = {
                'user_id': user_id,
                'query_text': query_text,
                'keywords': keywords,
                'results_count': results_count,
                'execution_time': execution_time,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            # Kaydet
            doc_ref = queries_ref.add(query_data)
            query_id = doc_ref[1].id
            
            logger.info(f"Arama sorgusu loglandı: {query_id}")
            return query_id
            
        except Exception as e:
            logger.error(f"Arama sorgusu loglama hatası: {e}")
            raise
    
    # Statistics
    async def get_scraper_stats(self) -> Dict[str, Any]:
        """Scraper istatistikleri"""
        try:
            stats = {}
            
            # Decision counts
            decisions_ref = self.client.collection('yargitay_decisions')
            decisions_count = len(list(decisions_ref.select([]).get()))
            stats['total_decisions'] = decisions_count
            
            # Recent decisions (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_decisions = decisions_ref.where('created_at', '>=', thirty_days_ago).get()
            stats['recent_decisions'] = len(list(recent_decisions))
            
            # Search queries count
            queries_ref = self.client.collection('search_queries')
            queries_count = len(list(queries_ref.select([]).get()))
            stats['total_queries'] = queries_count
            
            # Cache stats
            cache_ref = self.client.collection('search_cache')
            cache_count = len(list(cache_ref.select([]).get()))
            stats['cache_entries'] = cache_count
            
            # Active cache (not expired)
            now = datetime.utcnow()
            active_cache = cache_ref.where('expires_at', '>', now).get()
            stats['active_cache'] = len(list(active_cache))
            
            return stats
            
        except Exception as e:
            logger.error(f"Scraper istatistikleri alınamadı: {e}")
            return {}
    
    # Cleanup Operations
    async def cleanup_expired_cache(self) -> int:
        """Süresi dolmuş cache'leri temizle"""
        try:
            cache_ref = self.client.collection('search_cache')
            now = datetime.utcnow()
            
            # Expired cache'leri bul
            expired_docs = cache_ref.where('expires_at', '<=', now).get()
            
            deleted_count = 0
            batch = self.client.batch()
            
            for doc in expired_docs:
                batch.delete(doc.reference)
                deleted_count += 1
                
                # Batch size limit (500)
                if deleted_count % 500 == 0:
                    batch.commit()
                    batch = self.client.batch()
            
            # Remaining deletes
            if deleted_count % 500 != 0:
                batch.commit()
            
            logger.info(f"Temizlenen expired cache sayısı: {deleted_count}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache temizleme hatası: {e}")
            return 0


# Global Firestore manager instance
firestore_manager = FirestoreManager()


def get_firestore_client():
    """Firestore client'ını al"""
    return firestore_manager.client


def init_firestore() -> bool:
    """Firestore'u başlat"""
    try:
        success = firestore_manager.connect()
        if success:
            logger.info("Scraper API Firestore'a başarıyla bağlandı")
        return success
    except Exception as e:
        logger.error(f"Firestore initialization hatası: {e}")
        return False


def close_firestore():
    """Firestore bağlantısını kapat"""
    firestore_manager.disconnect()


# Legacy function for backward compatibility
async def init_db():
    """
    Uygulama başladığında Firestore bağlantısını başlatır.
    Firestore bağlantısı başarısız olursa fallback mode'da çalışır.
    """
    try:
        success = init_firestore()
        if not success:
            logger.warning("Firestore bağlantısı kurulamadı, in-memory cache mode'da çalışılıyor")
        return success
    except Exception as e:
        logger.error(f"Database initialization hatası: {e}, fallback mode aktif")
        return False

