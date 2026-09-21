from locust import HttpUser, between, task


class WelcomeUser(HttpUser):
    """Requests the welcome page."""

    wait_time = between(1, 5)

    @task
    def welcome(self):
        self.client.get('/')
