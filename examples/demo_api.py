import requests


def stream_ata_api():
    url = "http://127.0.0.1:8000/api/agent/ata"
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjeCJ9.Gb_y2viQzURkq9cTmP9bdE6I_c1RZZcKLrnZgluLZP0",
        "Content-Type": "application/json",
    }
    payload = {"active_role": "ac", "passive_role": "pa", "topic": ""}
    with requests.post(url, headers=headers, json=payload, stream=True) as resp:
        if resp.status_code == 200:
            for line in resp.iter_lines():
                if line:
                    print(line.decode("utf-8"), flush=True)
        else:
            print(f"Error: {resp.status_code} - {resp.text}")


if __name__ == "__main__":
    stream_ata_api()
