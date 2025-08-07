# monitoring.py - Monitoring ve metrics
import time
import psutil
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from fastapi.routing import APIRoute
from loguru import logger
import asyncio

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP requests', 
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections_total',
    'Number of active connections'
)

AI_REQUESTS = Counter(
    'ai_requests_total',
    'Total AI service requests',
    ['service_type', 'status']
)

AI_RESPONSE_TIME = Histogram(
    'ai_response_duration_seconds',
    'AI service response time in seconds',
    ['service_type']
)

DATABASE_OPERATIONS = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'status']
)

RATE_LIMIT_HITS = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit exceeded events',
    ['endpoint']
)

# System Metrics
MEMORY_USAGE = Gauge(
    'process_memory_usage_bytes',
    'Process memory usage in bytes'
)

CPU_USAGE = Gauge(
    'process_cpu_usage_percent',
    'Process CPU usage percentage'
)

class MetricsMiddleware:
    """Prometheus metrics middleware"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        start_time = time.time()
        
        # Increment active connections
        ACTIVE_CONNECTIONS.inc()
        
        try:
            response = await self.app(scope, receive, send)
            return response
        finally:
            # Record metrics
            duration = time.time() - start_time
            method = request.method
            path = request.url.path
            
            # Get status code from response (this is tricky in ASGI)
            status_code = getattr(request.state, 'status_code', 200)
            
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status_code=status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            
            ACTIVE_CONNECTIONS.dec()

class MonitoringService:
    """Monitoring service for collecting system metrics"""
    
    def __init__(self):
        self.start_time = time.time()
        self._monitoring_task = None
    
    def start_monitoring(self):
        """Start background monitoring task"""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._collect_system_metrics())
    
    def stop_monitoring(self):
        """Stop background monitoring task"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
    
    async def _collect_system_metrics(self):
        """Collect system metrics periodically"""
        while True:
            try:
                # Memory usage
                memory_info = psutil.Process().memory_info()
                MEMORY_USAGE.set(memory_info.rss)
                
                # CPU usage
                cpu_percent = psutil.Process().cpu_percent()
                CPU_USAGE.set(cpu_percent)
                
                # Wait 30 seconds before next collection
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def record_ai_request(self, service_type: str, duration: float, success: bool):
        """Record AI service request metrics"""
        status = "success" if success else "error"
        AI_REQUESTS.labels(service_type=service_type, status=status).inc()
        AI_RESPONSE_TIME.labels(service_type=service_type).observe(duration)
    
    def record_database_operation(self, operation: str, success: bool):
        """Record database operation metrics"""
        status = "success" if success else "error"
        DATABASE_OPERATIONS.labels(operation=operation, status=status).inc()
    
    def record_rate_limit_hit(self, endpoint: str):
        """Record rate limit exceeded event"""
        RATE_LIMIT_HITS.labels(endpoint=endpoint).inc()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        uptime = time.time() - self.start_time
        memory_info = psutil.Process().memory_info()
        
        return {
            "status": "healthy",
            "uptime_seconds": uptime,
            "memory_usage_mb": memory_info.rss / 1024 / 1024,
            "cpu_usage_percent": psutil.Process().cpu_percent(),
            "timestamp": time.time()
        }

# Global monitoring service instance
monitoring_service = MonitoringService()

async def get_metrics():
    """Get Prometheus metrics"""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

def log_performance(operation: str):
    """Decorator to log operation performance"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                logger.error(f"Error in {operation}: {e}")
                raise
            finally:
                duration = time.time() - start_time
                
                # Record metrics based on operation type
                if operation.startswith("ai_"):
                    monitoring_service.record_ai_request(
                        service_type=operation.replace("ai_", ""),
                        duration=duration,
                        success=success
                    )
                elif operation.startswith("db_"):
                    monitoring_service.record_database_operation(
                        operation=operation.replace("db_", ""),
                        success=success
                    )
                
                logger.info(f"{operation} completed in {duration:.2f}s (success: {success})")
        
        return wrapper
    return decorator

class HealthChecker:
    """Health check service"""
    
    @staticmethod
    async def check_database_health() -> Dict[str, Any]:
        """Check Firestore connectivity"""
        try:
            from .firestore_db import firestore_manager
            return await firestore_manager.health_check()
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False
            }
    
    @staticmethod
    async def check_ai_service_health() -> Dict[str, Any]:
        """Check AI service connectivity"""
        try:
            # Mock AI service health check
            return {
                "status": "healthy",
                "response_time_ms": 50,
                "available": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "available": False
            }
    
    @staticmethod
    async def check_external_services_health() -> Dict[str, Any]:
        """Check external services (scraper, etc.)"""
        try:
            # Mock external service health check
            return {
                "scraper_api": {"status": "healthy", "response_time_ms": 30},
                "selenium_hub": {"status": "healthy", "response_time_ms": 20}
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    @classmethod
    async def get_comprehensive_health(cls) -> Dict[str, Any]:
        """Get comprehensive health status"""
        health_checks = await asyncio.gather(
            cls.check_database_health(),
            cls.check_ai_service_health(),
            cls.check_external_services_health(),
            return_exceptions=True
        )
        
        database_health, ai_health, external_health = health_checks
        
        overall_status = "healthy"
        if any(check.get("status") == "unhealthy" for check in health_checks if isinstance(check, dict)):
            overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "timestamp": time.time(),
            "services": {
                "database": database_health,
                "ai_service": ai_health,
                "external_services": external_health
            },
            "system": monitoring_service.get_health_status()
        }