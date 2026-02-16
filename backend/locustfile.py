import time
from locust import HttpUser, task, between

class QuickstartUser(HttpUser):

    host="http://127.0.0.1:5000"

    wait_time = between(1, 5)

    def on_start(self):
        # Login once per simulated user
        self.token = "eyJhbGciOiJIUzI1NiIsImtpZCI6InRyVVErU3NaelorVnNnKzAiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FwZnNib2xkeHlzcXprcmVyYmd0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3NDZmNjgyNS0yZDFjLTQ5MWQtYjE3NS1kZjAwNmJmMmJlNzciLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU4NDg1OTU4LCJpYXQiOjE3NTg0ODIzNTgsImVtYWlsIjoic2ViYXN0aWVuYnJvd24xQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJzZWJhc3RpZW5icm93bjFAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiNzQ2ZjY4MjUtMmQxYy00OTFkLWIxNzUtZGYwMDZiZjJiZTc3In0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3NTg0ODIzNTh9XSwic2Vzc2lvbl9pZCI6IjJiYmM2NTk2LWZjMjEtNDNjMS1hYjViLTlhYTUzMDE0OGQzNCIsImlzX2Fub255bW91cyI6ZmFsc2V9.ipQiWKbiFw73UcmIcwrG4AV-POt2SqjVWAJvvS5tu9o"

    @task
    def retrieve_courses(self):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        with self.client.post("/accept-terms", headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                # Optionally log number of courses returned
                try:
                    courses = response.json()
                    #print(f"Retrieved {len(courses)} courses for user")
                    print(courses)
                    response.success()
                except Exception as e:
                    response.failure(f"Failed parsing JSON: {str(e)}")
            else:
                response.failure(f"Failed with status {response.status_code}: {response.text}")