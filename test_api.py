import requests

sample_jd = """
We are seeking a versatile Full Stack Developer with a strong background in IT infrastructure to design, build, and maintain our web applications and internal tools.
In this role, you will be responsible for the entire software lifecycle, creating responsive frontend user interfaces, developing scalable backend APIs,
managing relational and NoSQL databases, and ensuring seamless integration with our cloud networks and servers (AWS/Azure/Docker).
The ideal candidate possesses deep proficiency in modern JavaScript frameworks (like React or Angular) and server-side languages (such as Node.js or Python),
combined with a solid understanding of network security, systems administration, and DevOps pipelines to keep our production environments stable and secure.
"""

response = requests.post(
    "http://127.0.0.1:8000/jobs",
    json={
        "title": "Full Stack Developer",
        "raw_description": sample_jd
    }
)

print(f"Status code: {response.status_code}")
print(response.json())

# --- test updating the rubric ---
updated_rubric = response.json()["rubric"]
updated_rubric[0]["weight"] = 50

update_response = requests.put(
    f"http://127.0.0.1:8000/jobs/{response.json()['id']}/rubric",
    json={"rubric": updated_rubric}
)

print(f"\nUpdate status: {update_response.status_code}")
print(update_response.json())

job_id_to_check = response.json()["id"]  # or hardcode a job_id you know has scored resumes

rankings_response = requests.get(f"http://127.0.0.1:8000/jobs/{job_id_to_check}/rankings")
print(f"\nRankings status: {rankings_response.status_code}")
print(rankings_response.json())