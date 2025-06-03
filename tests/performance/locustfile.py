"""
Comprehensive performance testing suite for OpenPypi API using Locust.
"""

import json
import random
import time
from typing import Any, Dict

from locust import HttpUser, between, events, task
from locust.env import Environment


class OpenPypiAPIUser(HttpUser):
    """Simulated user for OpenPypi API performance testing."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a user starts."""
        self.client.headers.update(
            {"Content-Type": "application/json", "User-Agent": "Locust-Performance-Test/1.0"}
        )

        # Simulate user authentication if needed
        self.api_key = self.get_api_key()
        if self.api_key:
            self.client.headers["X-API-Key"] = self.api_key

    def get_api_key(self) -> str:
        """Get API key for authenticated requests."""
        # In a real scenario, you'd authenticate and get a real API key
        return "test-api-key-for-performance-testing"

    @task(10)
    def health_check(self):
        """Test health check endpoint - most frequent task."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(8)
    def get_root_info(self):
        """Test root endpoint."""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "name" in data and "version" in data:
                    response.success()
                else:
                    response.failure("Root endpoint missing required fields")
            else:
                response.failure(f"Root endpoint failed: {response.status_code}")

    @task(6)
    def get_monitoring_info(self):
        """Test monitoring endpoint."""
        with self.client.get("/monitoring/info", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Monitoring info failed: {response.status_code}")

    @task(5)
    def health_detailed(self):
        """Test detailed health check."""
        with self.client.get("/health/detailed", catch_response=True) as response:
            if response.status_code in [200, 503]:  # 503 is acceptable for degraded health
                response.success()
            else:
                response.failure(f"Detailed health check failed: {response.status_code}")

    @task(4)
    def readiness_probe(self):
        """Test Kubernetes readiness probe."""
        with self.client.get("/ready", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Readiness probe failed: {response.status_code}")

    @task(3)
    def liveness_probe(self):
        """Test Kubernetes liveness probe."""
        with self.client.get("/live", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Liveness probe failed: {response.status_code}")

    @task(2)
    def generate_project_sync(self):
        """Test synchronous project generation - computationally intensive."""
        project_data = self.generate_random_project_data()

        with self.client.post("/generate/sync", json=project_data, catch_response=True) as response:
            if response.status_code in [200, 201]:
                # Check if generation was successful
                try:
                    data = response.json()
                    if data.get("success"):
                        response.success()
                    else:
                        response.failure("Generation marked as unsuccessful")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 422:
                # Validation error is acceptable for random data
                response.success()
            elif response.status_code == 429:
                # Rate limit is expected under load
                response.success()
            else:
                response.failure(f"Sync generation failed: {response.status_code}")

    @task(1)
    def generate_project_async(self):
        """Test asynchronous project generation."""
        project_data = self.generate_random_project_data()

        with self.client.post(
            "/generate/async", json=project_data, catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                try:
                    data = response.json()
                    # Check for task ID if async
                    if response.status_code == 202:
                        if "data" in data and "task_id" in data["data"]:
                            # Optionally check task status
                            task_id = data["data"]["task_id"]
                            self.check_task_status(task_id)
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 422:
                response.success()  # Validation error acceptable
            elif response.status_code == 429:
                response.success()  # Rate limit expected
            else:
                response.failure(f"Async generation failed: {response.status_code}")

    def check_task_status(self, task_id: str):
        """Check the status of an async task."""
        with self.client.get(
            f"/generate/status/{task_id}", catch_response=True, name="/generate/status/[task_id]"
        ) as response:
            if response.status_code in [200, 404]:  # 404 acceptable if task not found
                response.success()
            else:
                response.failure(f"Task status check failed: {response.status_code}")

    def generate_random_project_data(self) -> Dict[str, Any]:
        """Generate random project data for testing."""
        project_names = [
            "test-project",
            "demo-app",
            "sample-service",
            "api-client",
            "data-processor",
            "web-scraper",
            "ml-pipeline",
            "task-runner",
        ]

        authors = ["John Doe", "Jane Smith", "Alex Johnson", "Sam Wilson"]

        return {
            "name": f"{random.choice(project_names)}-{random.randint(1000, 9999)}",
            "description": f"Performance test project for load testing - {time.time()}",
            "author": random.choice(authors),
            "email": f"test{random.randint(1, 1000)}@example.com",
            "version": f"{random.randint(0, 2)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "options": {
                "use_fastapi": random.choice([True, False]),
                "use_docker": random.choice([True, False]),
                "test_framework": random.choice(["pytest", "unittest"]),
            },
        }


class AdminUser(HttpUser):
    """Admin user with access to monitoring and admin endpoints."""

    wait_time = between(2, 5)
    weight = 1  # Lower weight, fewer admin users

    def on_start(self):
        """Setup admin user."""
        self.client.headers.update(
            {"Content-Type": "application/json", "X-API-Key": "admin-api-key-for-testing"}
        )

    @task(5)
    def get_system_metrics(self):
        """Test system metrics endpoint."""
        with self.client.get("/monitoring/metrics/system", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"System metrics failed: {response.status_code}")

    @task(4)
    def get_application_metrics(self):
        """Test application metrics endpoint."""
        with self.client.get("/monitoring/metrics/application", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"App metrics failed: {response.status_code}")

    @task(3)
    def get_comprehensive_metrics(self):
        """Test comprehensive monitoring endpoint."""
        with self.client.get("/monitoring/metrics", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Comprehensive metrics failed: {response.status_code}")


class StressTestUser(HttpUser):
    """Stress test user for high-load scenarios."""

    wait_time = between(0.1, 0.5)  # Very short wait times
    weight = 3  # Higher weight for stress testing

    @task
    def rapid_health_checks(self):
        """Rapid fire health checks to test rate limiting."""
        endpoints = ["/health", "/ready", "/live", "/"]
        endpoint = random.choice(endpoints)

        with self.client.get(endpoint, catch_response=True) as response:
            if response.status_code in [200, 429]:  # Accept rate limiting
                response.success()
            else:
                response.failure(f"Rapid request failed: {response.status_code}")


# Performance test events and statistics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print("🚀 Starting OpenPypi API performance tests...")
    print(f"Target host: {environment.host}")
    print(f"Number of users: {environment.runner.target_user_count}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print("🏁 Performance test completed!")

    # Print summary statistics
    stats = environment.stats
    print(f"\nTest Summary:")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Requests/sec: {stats.total.current_rps:.2f}")

    # Check for performance thresholds
    if stats.total.avg_response_time > 1000:  # 1 second
        print("⚠️  WARNING: Average response time exceeds 1 second!")

    if stats.total.num_failures / stats.total.num_requests > 0.05:  # 5% error rate
        print("⚠️  WARNING: Error rate exceeds 5%!")

    print("\nDetailed statistics saved to locust report files.")


# Custom performance scenarios
class LightLoadTest(HttpUser):
    """Light load test scenario."""

    tasks = [OpenPypiAPIUser]
    min_wait = 1000
    max_wait = 3000


class MediumLoadTest(HttpUser):
    """Medium load test scenario."""

    tasks = [OpenPypiAPIUser, AdminUser]
    min_wait = 500
    max_wait = 2000


class HeavyLoadTest(HttpUser):
    """Heavy load test scenario."""

    tasks = [OpenPypiAPIUser, AdminUser, StressTestUser]
    min_wait = 100
    max_wait = 1000


# Configuration for different test scenarios
def get_test_config(scenario: str) -> Dict[str, Any]:
    """Get configuration for different test scenarios."""
    configs = {
        "smoke": {
            "users": 1,
            "spawn_rate": 1,
            "run_time": "30s",
            "user_classes": [OpenPypiAPIUser],
        },
        "load": {
            "users": 10,
            "spawn_rate": 2,
            "run_time": "5m",
            "user_classes": [OpenPypiAPIUser, AdminUser],
        },
        "stress": {
            "users": 50,
            "spawn_rate": 5,
            "run_time": "10m",
            "user_classes": [OpenPypiAPIUser, AdminUser, StressTestUser],
        },
        "spike": {
            "users": 100,
            "spawn_rate": 10,
            "run_time": "2m",
            "user_classes": [StressTestUser],
        },
    }
    return configs.get(scenario, configs["load"])


if __name__ == "__main__":
    print("Use locust command line to run performance tests:")
    print("Examples:")
    print("  locust -f locustfile.py --host=http://localhost:8000")
    print(
        "  locust -f locustfile.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=60s"
    )
    print(
        "  locust -f locustfile.py --host=http://localhost:8000 --headless --users=50 --spawn-rate=5 --run-time=300s"
    )
