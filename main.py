import os
import asyncio
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
import automation_logic

app = FastAPI()

@app.post("/")
async def start_automation_endpoint(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    if not data:
        return JSONResponse(content={"error": "No JSON data provided"}, status_code=400)

    row_number = data.get('row_number')
    email = data.get('email')
    reason = data.get('reason')
    callback_url = data.get('callback_url') 

    if not row_number or not email or not callback_url:
        return JSONResponse(content={"error": "Missing row_number, email, or callback_url"}, status_code=400)

    # FastAPI Native Background Task - much more stable on Cloud Run than threading.Thread
    print(f"Adding Background Task for Row {row_number}")
    background_tasks.add_task(automation_logic.run_automation, row_number, email, reason, callback_url)

    return JSONResponse(content={"message": "Automation Started"}, status_code=202)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)